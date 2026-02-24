from fastapi import APIRouter, HTTPException
from services.cache_service import cache
from services.vector_store import vector_store
from services.embedding_service import EmbeddingService
from services.llm_service import llm_service
import traceback

router = APIRouter()
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

        # Simple keyword search on transcript chunks
        chunks = cache.get(f"chunks:{video_id}") or []

        # Find relevant chunks using simple keyword matching
        message_words = set(message.lower().split())
        scored_chunks = []
        for chunk in chunks:
            chunk_words = set(chunk['text'].lower().split())
            overlap = len(message_words & chunk_words)
            scored_chunks.append((overlap, chunk))
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [c for _, c in scored_chunks[:4]]

        # If no good matches, just use first 4 chunks
        if not top_chunks or all(score == 0 for score, _ in scored_chunks[:4]):
            top_chunks = chunks[:4]

        # Build context (capped to avoid overwhelming the LLM)
        context = ""
        for chunk in top_chunks:
            mins = int(chunk['start_time'] // 60)
            secs = int(chunk['start_time'] % 60)
            context += f"[{mins:02d}:{secs:02d}] {chunk['text']}\n\n"
        
        # Safety trim: cap context to ~4000 chars to stay within token limits
        if len(context) > 4000:
            context = context[:4000] + "\n...(trimmed)"

        # Build messages for LLM
        messages = [
            {
                "role": "user",
                "content": f"""You are a helpful, friendly assistant. Answer the user's question conversationally, like a knowledgeable friend, using the information provided below.
CRITICAL RULES:
- DO NOT say "in the transcript", "the video says", "in the excerpts", or anything similar. Just state the facts directly as if you know them.
- Be warm and natural in your tone. Talk like a friend.
- Include timestamps like [MM:SS] when specific parts are relevant.
- If the answer cannot be determined from the information provided, respond in a friendly way that you don't have that specific information.

INFORMATION:
{context}

QUESTION: {message}

Give a conversational, helpful answer in 2-4 sentences."""
            }
        ]

        answer = llm_service.chat_completion(messages, max_tokens=300)

        sources = [{"text": c['text'][:100], "start_time": c['start_time']} for c in top_chunks]
        return {"answer": answer, "sources": sources}

    except HTTPException:
        raise
    except Exception as e:
        print(f"CHAT ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
