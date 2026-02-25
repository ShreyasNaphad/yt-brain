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

router = APIRouter(tags=["video"])  # Prefix handled in main.py
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


def _generate_overview(chunks: list, metadata: dict) -> str:
    """
    Generate a condensed topic overview from the full video by sampling
    chunks evenly across the entire video. This gives the LLM a global
    understanding of the video content for answering broad questions.
    """
    total_chunks = len(chunks)
    if total_chunks == 0:
        return ""

    # Sample up to 20 chunks evenly distributed across the video
    max_samples = min(20, total_chunks)
    step = max(1, total_chunks // max_samples)
    sampled = [chunks[i] for i in range(0, total_chunks, step)][:max_samples]

    # Build a sampled transcript with timestamps
    sampled_text = ""
    for chunk in sampled:
        mins = int(chunk['start_time'] // 60)
        secs = int(chunk['start_time'] % 60)
        # Take first 300 chars of each sampled chunk to stay within token limits
        text_snippet = chunk['text'][:300]
        sampled_text += f"[{mins:02d}:{secs:02d}] {text_snippet}\n\n"

    # Cap the sampled text to ~8000 chars for the overview generation prompt
    if len(sampled_text) > 8000:
        sampled_text = sampled_text[:8000]

    title = metadata.get("title", "Unknown")
    channel = metadata.get("channel", "Unknown")

    try:
        messages = [
            {
                "role": "user",
                "content": f"""Analyze these excerpts from the video "{title}" by {channel} and create a comprehensive topic overview.

The video has {total_chunks} content sections. These are evenly sampled excerpts:

{sampled_text}

Return ONLY valid JSON:
{{
  "main_topic": "one sentence describing what the entire video is about",
  "topics": [
    {{"title": "topic name", "description": "1-2 sentence description", "approximate_timestamp": "MM:SS"}}
  ],
  "key_terms": ["term1", "term2", "term3"]
}}

Include 8-15 topics that cover the FULL video. Include 10-20 key terms."""
            }
        ]
        overview_data = llm_service.chat_completion_json(messages, max_tokens=1200)

        # Format as readable text for context injection
        overview_text = f"VIDEO: {title} by {channel}\n"
        overview_text += f"MAIN TOPIC: {overview_data.get('main_topic', '')}\n\n"
        overview_text += "TOPICS COVERED:\n"
        for i, topic in enumerate(overview_data.get("topics", []), 1):
            ts = topic.get("approximate_timestamp", "")
            overview_text += f"{i}. [{ts}] {topic['title']}: {topic['description']}\n"

        key_terms = overview_data.get("key_terms", [])
        if key_terms:
            overview_text += f"\nKEY TERMS: {', '.join(key_terms)}\n"

        logger.info(f"Generated overview: {len(overview_text)} chars, {len(overview_data.get('topics', []))} topics")
        return overview_text

    except Exception as e:
        logger.warning(f"Overview generation failed: {e}")
        # Fallback: just list chunk timestamps as basic overview
        return f"VIDEO: {title} by {channel}\nTotal sections: {total_chunks}\n"


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
        total_words = sum(len(e.get('text', '').split()) for e in transcript_entries)
        logger.info(f"Transcript: {len(transcript_entries)} entries, ~{total_words} words")
        
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
        
        cache.set(f"chunks:{video_id}", chunks)
        
        # Step 6: Generate overview for global context in chat
        overview = _generate_overview(chunks, metadata)
        cache.set(f"overview:{video_id}", overview)
        
        cache.set(f"status:{video_id}", "ready")
        
        logger.info(f"SUCCESS: processed {len(chunks)} chunks, ~{total_words} words for {video_id}")
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
        
        # Use the overview as additional context for summary
        overview = cache.get(f"overview:{video_id}") or ""
        
        # Sample more aggressively for long videos: 5 sections evenly spaced
        total_len = len(transcript)
        if total_len > 15000:
            # For long videos, take 5 evenly spaced sections of 2000 chars
            section_size = 2000
            num_sections = 5
            step = total_len // num_sections
            sections = []
            for i in range(num_sections):
                start = i * step
                sections.append(transcript[start:start + section_size])
            trimmed = "\n\n---\n\n".join(
                f"[SECTION {i+1}/{num_sections}]\n{s}" for i, s in enumerate(sections)
            )
        elif total_len > 6000:
            # Medium videos: beginning, middle, end
            trimmed = (
                f"[BEGINNING]\n{transcript[:2500]}\n\n"
                f"[MIDDLE]\n{transcript[total_len//2 - 1250:total_len//2 + 1250]}\n\n"
                f"[END]\n{transcript[-2500:]}"
            )
        else:
            trimmed = transcript
        
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this video transcript and return ONLY valid JSON. 
No markdown, no explanation, just the JSON object.

VIDEO OVERVIEW:
{overview}

TRANSCRIPT EXCERPTS:
{trimmed}

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
Use actual start_time seconds from the transcript context."""
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
