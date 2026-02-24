from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import traceback
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from services.cache_service import cache
from services.youtube_service import extract_video_id, extract_metadata, extract_transcript, chunk_transcript
from services.embedding_service import EmbeddingService
from services.vector_store import vector_store
from services.llm_service import llm_service

router = APIRouter(tags=["video"]) # Prefix handled in main.py
logger = logging.getLogger(__name__)

@router.get("/test-llm")
def test_llm():
    try:
        ans = llm_service.chat_completion([{"role":"user", "content":"say exactly 'hello'"}], max_tokens=10)
        return {"status": "success", "answer": ans}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Initialize local services (stateless ones)
embedding_service = EmbeddingService()

class VideoRequest(BaseModel):
    url: str

class VideoMetadataResponse(BaseModel):
    video_id: str
    title: str
    channel: str
    thumbnail_url: str
    duration_seconds: int
    url: str
    processed: bool = False
    chunk_count: int = 0

@router.post("/process")
async def process_video(body: dict):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        video_id = extract_video_id(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    # Return cached result instantly
    cached = cache.get(f"video:{video_id}")
    if cached and cache.get(f"status:{video_id}") == "ready":
        return {**cached, "processed": True, "status": "ready"}
    
    try:
        # Step 1: Get metadata via oEmbed API
        metadata = extract_metadata(url)
        cache.set(f"video:{video_id}", metadata)
        
        # Step 2: Get transcript
        transcript_entries = extract_transcript(video_id)
        
        # Step 3: Chunk it
        chunks = chunk_transcript(transcript_entries)
        
        # Step 4: Store full transcript text
        full_text = ' '.join([e.get('text', '') for e in transcript_entries])
        cache.set(f"transcript:{video_id}", full_text)
        
        # Step 5: Embed and store chunks (TF-IDF, instant)
        texts = [c['text'] for c in chunks]
        embedding_service.fit(texts)
        vectors = embedding_service.embed_batch(texts)
        for i, chunk in enumerate(chunks):
            chunk['vector'] = vectors[i]
        vector_store.upsert_chunks(video_id, chunks)
        
        cache.set(f"status:{video_id}", "ready")
        cache.set(f"chunks:{video_id}", chunks)
        
        print(f"SUCCESS: processed {len(chunks)} chunks for {video_id}")
        return {**metadata, "processed": True, "status": "ready", "chunk_count": len(chunks)}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PROCESSING ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/status")
async def get_video_status(video_id: str):
    status = cache.get(f"status:{video_id}")
    if not status:
        return {"status": "unknown"}
    return {"status": status}


@router.get("/{video_id}/metadata")
async def get_video_metadata(video_id: str):
    ctx_key = f"video:{video_id}"
    cached_data = cache.get(ctx_key)
    return cached_data

@router.get("/{video_id}/summary")
async def get_summary(video_id: str):
    try:
        cached = cache.get(f"summary:{video_id}")
        if cached:
            return cached
        
        transcript = cache.get(f"transcript:{video_id}")
        if not transcript:
            raise HTTPException(status_code=400, detail="Video not processed yet")
        
        # Sample from beginning, middle, and end of transcript for full coverage
        max_section = 2000
        if len(transcript) > max_section * 3:
            beginning = transcript[:max_section]
            mid_start = len(transcript) // 2 - max_section // 2
            middle = transcript[mid_start:mid_start + max_section]
            ending = transcript[-max_section:]
            trimmed = f"[BEGINNING]\n{beginning}\n\n[MIDDLE]\n{middle}\n\n[END]\n{ending}"
        else:
            trimmed = transcript
        
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this video transcript and return ONLY valid JSON. 
No markdown, no explanation, just the JSON object.

{{
  "overview": "3-4 sentence summary of the video",
  "deep_concepts": [
    {{"name": "concept name", "explanation": "2 sentence explanation", "start_time": 0}}
  ],
  "actionable_takeaways": [
    "takeaway 1",
    "takeaway 2", 
    "takeaway 3",
    "takeaway 4",
    "takeaway 5"
  ]
}}

Include 4-5 deep_concepts and exactly 5 actionable_takeaways.
Use actual start_time seconds from the transcript context.

TRANSCRIPT:
{trimmed}"""
            }
        ]
        
        result = llm_service.chat_completion_json(messages, max_tokens=800)
        cache.set(f"summary:{video_id}", result, ttl=86400*30)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"SUMMARY ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
