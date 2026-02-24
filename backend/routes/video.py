from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import traceback
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from services.cache_service import cache
from services.youtube_service import YouTubeService, extract_video_id
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
youtube_service = YouTubeService()
embedding_service = EmbeddingService()

# Use global singletons for stateful services
# cache and vector_store are imported

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
    
    # Step 1: Get metadata (fast, ~1 second)
    try:
        metadata = {
            "video_id": video_id,
            "title": "YouTube Video",
            "channel": "Unknown",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "duration_seconds": 0,
            "url": url
        }
        # Try to get real metadata but dont fail if it errors
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'no_warnings': True, 'socket_timeout': 10}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
                metadata["title"] = info.get("title", "YouTube Video")
                metadata["channel"] = info.get("uploader", "Unknown")
                metadata["duration_seconds"] = info.get("duration", 0)
        except Exception as meta_err:
            print(f"Metadata fetch failed (using fallback): {meta_err}")
        
        cache.set(f"video:{video_id}", metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata error: {str(e)}")
    
    # Step 2: Get transcript (can take a few seconds)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_entries = None
        
        try:
            transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        except:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for t in transcript_list:
                    try:
                        transcript_entries = t.fetch()
                        break
                    except:
                        continue
            except:
                pass
        
        if not transcript_entries:
            # Fallback: use description as content
            try:
                import yt_dlp
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(
                        f'https://www.youtube.com/watch?v={video_id}', 
                        download=False
                    )
                    desc = info.get('description', 'No content available')
                    title = info.get('title', '')
                    content = f"{title}\n\n{desc}"
                    words = content.split()
                    transcript_entries = []
                    for i in range(0, len(words), 50):
                        transcript_entries.append({
                            'text': ' '.join(words[i:i+50]),
                            'start': i * 2,
                            'duration': 10
                        })
            except Exception as desc_err:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Could not get any content from video: {str(desc_err)}"
                )
        
        # Step 3: Simple chunking - max 15 chunks
        chunks = []
        total = len(transcript_entries)
        chunk_size = max(1, total // 15)
        
        for i in range(0, total, chunk_size):
            group = transcript_entries[i:i+chunk_size]
            text = ' '.join([e.get('text', '') for e in group])
            chunks.append({
                'text': text,
                'start_time': group[0].get('start', 0),
                'chunk_index': len(chunks)
            })
            if len(chunks) >= 15:
                break
        
        # Step 4: Store full transcript text for BM25/summary
        full_text = ' '.join([e.get('text', '') for e in transcript_entries])
        cache.set(f"transcript:{video_id}", full_text)
        
        # Step 5: Embed and store chunks (TF-IDF, instant)
        texts = [c['text'] for c in chunks]
        embedding_service.fit(texts) # Try fitting to ensure we can embed
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
        
        # Trim transcript to 6000 chars max to save tokens
        trimmed = transcript[:6000] if len(transcript) > 6000 else transcript
        
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
