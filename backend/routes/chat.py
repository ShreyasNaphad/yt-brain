from fastapi import APIRouter, HTTPException
from services.cache_service import cache
from services.vector_store import vector_store
from services.embedding_service import EmbeddingService
from services.llm_service import llm_service
import httpx
import traceback
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()


def _web_search_fallback(query: str, video_title: str) -> str:
    """
    Last resort: search the web for information about the video topic.
    Uses DuckDuckGo instant answer API (no API key needed).
    """
    try:
        search_query = f"{video_title} {query}"
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://api.duckduckgo.com/",
                params={"q": search_query, "format": "json", "no_html": 1},
                headers={"User-Agent": "YTBrain/1.0"},
            )
            if r.status_code == 200:
                data = r.json()
                results = []
                # Abstract (main answer)
                if data.get("AbstractText"):
                    results.append(data["AbstractText"])
                # Related topics
                for topic in data.get("RelatedTopics", [])[:3]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(topic["Text"])
                if results:
                    return "\n".join(results[:3])
    except Exception as e:
        logger.warning(f"Web search fallback failed: {e}")
    return ""


@router.post("")
async def chat(body: dict):
    try:
        video_id = body.get("video_id", "").strip()
        message = body.get("message", "").strip()
        history = body.get("history", [])

        if not video_id or not message:
            raise HTTPException(status_code=400, detail="video_id and message required")

        # Get transcript from cache
        transcript = cache.get(f"transcript:{video_id}")
        if not transcript:
            raise HTTPException(status_code=400, detail="Video not processed yet")

        # Get the pre-computed overview (global video context)
        overview = cache.get(f"overview:{video_id}") or ""

        # Get chunks for retrieval
        chunks = cache.get(f"chunks:{video_id}") or []

        if not chunks:
            raise HTTPException(status_code=400, detail="Video not processed yet")

        # ----- Improved chunk retrieval: TF-IDF similarity -----
        # Try TF-IDF vector similarity first, fall back to keyword matching
        top_chunks = []
        try:
            query_vector = embedding_service.embed_text(message)
            if query_vector:
                results = vector_store.search(video_id, query_vector, top_k=8)
                if results:
                    top_chunks = results
        except Exception as e:
            logger.warning(f"Vector search failed: {e}, falling back to keyword matching")

        # Fallback: keyword matching if vector search didn't work
        if not top_chunks:
            message_words = set(message.lower().split())
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at',
                         'to', 'for', 'of', 'with', 'and', 'or', 'not', 'this', 'that',
                         'it', 'i', 'me', 'my', 'we', 'you', 'what', 'how', 'why', 'when',
                         'can', 'do', 'does', 'about', 'from', 'some', 'explain', 'tell'}
            query_words = message_words - stop_words

            scored_chunks = []
            for chunk in chunks:
                chunk_words = set(chunk['text'].lower().split())
                overlap = len(query_words & chunk_words)
                scored_chunks.append((overlap, chunk))
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            top_chunks = [c for _, c in scored_chunks[:8]]

        # If still no good matches, sample evenly across the video
        if not top_chunks or len(top_chunks) < 4:
            total = len(chunks)
            step = max(1, total // 8)
            top_chunks = [chunks[i] for i in range(0, total, step)][:8]

        # Build context from retrieved chunks (no timestamps)
        context = ""
        for chunk in top_chunks:
            context += f"{chunk['text']}\n\n"

        # Allow generous context: up to ~12000 chars (~3000 tokens)
        if len(context) > 12000:
            context = context[:12000] + "\n...(additional content available)"

        # Detect if user wants short or detailed answer
        msg_lower = message.lower()
        wants_short = any(w in msg_lower for w in ['short', 'brief', 'briefly', 'quick', 'one line', 'one sentence', 'tldr', 'tl;dr'])
        wants_detail = any(w in msg_lower for w in ['detail', 'detailed', 'long', 'elaborate', 'in depth', 'in-depth', 'explain in', 'thorough', 'comprehensive', 'everything about'])

        if wants_short:
            length_instruction = "Give a short, concise answer in 2-3 sentences."
            max_tokens = 200
        elif wants_detail:
            length_instruction = "Give a detailed, thorough answer with full explanations. Be as comprehensive as possible."
            max_tokens = 1000
        else:
            length_instruction = "Give a medium-length, informative answer in about 7-10 sentences. Cover the key points well."
            max_tokens = 500

        # Check if the transcript content seems too minimal (metadata-only fallback)
        is_minimal_transcript = len(transcript.strip()) < 200 or "transcript was not available" in transcript.lower()

        # If transcript is minimal, try web search for additional context
        web_context = ""
        if is_minimal_transcript:
            video_meta = cache.get(f"video:{video_id}") or {}
            video_title = video_meta.get("title", "")
            web_context = _web_search_fallback(message, video_title)

        # Build messages for LLM — include overview for global understanding
        extra_context = ""
        if web_context:
            extra_context = f"\n\nADDITIONAL WEB CONTEXT (use only to supplement, not replace video info):\n{web_context}"

        messages = [
            {
                "role": "user",
                "content": f"""You are a helpful, friendly assistant who has thoroughly studied this entire video. Answer the user's question conversationally, like a knowledgeable friend.

CRITICAL RULES:
- DO NOT say "in the transcript", "the video says", "in the excerpts", or anything similar. Just state the facts directly as if you know them.
- Be warm and natural in your tone. Talk like a friend who watched the whole video.
- Do NOT include any timestamps in your answer.
- You have access to the FULL VIDEO OVERVIEW below. Use it to answer broad questions about the video's topics and structure.
- For specific questions, use the RELEVANT SECTIONS which contain detailed content.
- NEVER say you don't have transcript or can't answer. Always try your best to provide a helpful, relevant answer using ALL available information.
- If the video content sections are limited, use the overview and any additional context to give the best possible answer.

FULL VIDEO OVERVIEW:
{overview}

RELEVANT SECTIONS:
{context}{extra_context}

QUESTION: {message}

{length_instruction}"""
            }
        ]

        answer = llm_service.chat_completion(messages, max_tokens=max_tokens)

        sources = [{"text": c['text'][:100], "start_time": c.get('start_time', 0)} for c in top_chunks[:4]]
        return {"answer": answer, "sources": sources}

    except HTTPException:
        raise
    except Exception as e:
        print(f"CHAT ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
