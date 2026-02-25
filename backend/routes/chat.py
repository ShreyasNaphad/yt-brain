from fastapi import APIRouter, HTTPException
from services.cache_service import cache
from services.vector_store import vector_store
from services.embedding_service import EmbeddingService
from services.llm_service import llm_service
import traceback
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()

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
            # Remove common stop words for better matching
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

        # Build context from retrieved chunks
        context = ""
        for chunk in top_chunks:
            mins = int(chunk.get('start_time', 0) // 60)
            secs = int(chunk.get('start_time', 0) % 60)
            context += f"[{mins:02d}:{secs:02d}] {chunk['text']}\n\n"

        # Allow generous context: up to ~12000 chars (~3000 tokens)
        # Groq's llama-3.3-70b supports 128k context, so this is safe
        if len(context) > 12000:
            context = context[:12000] + "\n...(additional content available)"

        # Build messages for LLM — include overview for global understanding
        messages = [
            {
                "role": "user",
                "content": f"""You are a helpful, friendly assistant who has thoroughly studied this entire video. Answer the user's question conversationally, like a knowledgeable friend.

CRITICAL RULES:
- DO NOT say "in the transcript", "the video says", "in the excerpts", or anything similar. Just state the facts directly as if you know them.
- Be warm and natural in your tone. Talk like a friend who watched the whole video.
- Include timestamps like [MM:SS] when specific parts are relevant.
- You have access to the FULL VIDEO OVERVIEW below. Use it to answer broad questions about the video's topics and structure.
- For specific questions, use the RELEVANT SECTIONS which contain detailed content.
- If the answer cannot be determined from the information provided, respond helpfully with what you DO know about the video.

FULL VIDEO OVERVIEW:
{overview}

RELEVANT SECTIONS:
{context}

QUESTION: {message}

Give a comprehensive, helpful answer. For broad questions (like "explain important topics"), draw from the overview and provide detailed explanations. For specific questions, cite timestamps."""
            }
        ]

        answer = llm_service.chat_completion(messages, max_tokens=600)

        sources = [{"text": c['text'][:100], "start_time": c.get('start_time', 0)} for c in top_chunks[:4]]
        return {"answer": answer, "sources": sources}

    except HTTPException:
        raise
    except Exception as e:
        print(f"CHAT ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
