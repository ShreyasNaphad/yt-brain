import re
import httpx
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from fastapi import HTTPException

def extract_video_id(url: str) -> str:
    url = url.strip()
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "v" in params:
        return params["v"][0]
    raise ValueError(f"Could not extract video ID from URL: {url}")

def extract_metadata(url: str) -> dict:
    video_id = extract_video_id(url)
    
    # Use YouTube oEmbed API - free, no key, works on all IPs
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with httpx.Client(timeout=10) as client:
            response = client.get(oembed_url)
            if response.status_code == 200:
                data = response.json()
                return {
                    "video_id": video_id,
                    "title": data.get("title", "YouTube Video"),
                    "channel": data.get("author_name", "Unknown"),
                    "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    "duration_seconds": 0,
                    "url": url
                }
    except Exception as e:
        print(f"oEmbed failed: {e}")
    
    # Fallback - construct manually, always works
    return {
        "video_id": video_id,
        "title": "YouTube Video",
        "channel": "Unknown",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "duration_seconds": 0,
        "url": url
    }

def extract_transcript(video_id: str) -> list:
    errors = []
    
    # Detect API version: v1.0+ removed static methods
    use_new_api = not hasattr(YouTubeTranscriptApi, 'get_transcript')
    
    if use_new_api:
        # NEW API (v1.0+): instance-based
        print("Using youtube-transcript-api v1.0+ (new API)")
        ytt = YouTubeTranscriptApi()
        
        # Method 1: Direct fetch
        try:
            result = ytt.fetch(video_id)
            transcript = [
                {'text': s.text, 'start': s.start, 'duration': s.duration}
                for s in result
            ]
            print(f"Transcript method 1 (new API) success: {len(transcript)} entries")
            return transcript
        except Exception as e:
            errors.append(f"Method 1 (new): {str(e)}")
        
        # Method 2: List and try each
        try:
            transcript_list = ytt.list(video_id)
            for t in transcript_list:
                try:
                    result = t.fetch()
                    transcript = [
                        {'text': s.text, 'start': s.start, 'duration': s.duration}
                        for s in result
                    ]
                    print(f"Transcript method 2 (new API) success: lang={t.language}")
                    return transcript
                except Exception as e:
                    errors.append(f"Method 2 lang {t.language}: {str(e)}")
                    continue
        except Exception as e:
            errors.append(f"Method 2 list: {str(e)}")
    else:
        # OLD API (pre-1.0): static methods
        print("Using youtube-transcript-api (legacy API)")
        
        # Method 1: Direct English transcript
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            print(f"Transcript method 1 success: {len(transcript)} entries")
            return transcript
        except Exception as e:
            errors.append(f"Method 1: {str(e)}")

        # Method 2: Any available language
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            print(f"Transcript method 2 success: {len(transcript)} entries")
            return transcript
        except Exception as e:
            errors.append(f"Method 2: {str(e)}")

        # Method 3: List all and try each one
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for t in transcript_list:
                try:
                    fetched = t.fetch()
                    print(f"Transcript method 3 success: language={t.language}")
                    return [{'text': e['text'], 'start': e['start'], 
                             'duration': e.get('duration', 0)} for e in fetched]
                except Exception as e:
                    errors.append(f"Method 3 lang {t.language}: {str(e)}")
                    continue
        except Exception as e:
            errors.append(f"Method 3 list: {str(e)}")

        # Method 4: Try auto-generated captions specifically
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for t in transcript_list:
                if t.is_generated:
                    try:
                        fetched = t.fetch()
                        print(f"Transcript method 4 success: auto-generated {t.language}")
                        return [{'text': e['text'], 'start': e['start'],
                                 'duration': e.get('duration', 0)} for e in fetched]
                    except Exception as e:
                        errors.append(f"Method 4: {str(e)}")
        except Exception as e:
            errors.append(f"Method 4 list: {str(e)}")

        # Method 5: Try translating to English from whatever exists
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for t in transcript_list:
                try:
                    translated = t.translate('en').fetch()
                    print(f"Transcript method 5 success: translated from {t.language}")
                    return [{'text': e['text'], 'start': e['start'],
                             'duration': e.get('duration', 0)} for e in translated]
                except:
                    continue
        except Exception as e:
            errors.append(f"Method 5: {str(e)}")

    print(f"ALL transcript methods failed: {errors}")
    raise HTTPException(
        status_code=400,
        detail=f"This video has no accessible captions. This can happen if the video owner disabled transcripts. Try a different video. Errors: {'; '.join(errors[-2:])}"
    )

def chunk_transcript(transcript: list) -> list:
    chunks = []
    current_words = []
    current_start = 0
    word_count = 0
    
    for entry in transcript:
        text = entry.get('text', '').strip()
        if not text:
            continue
        words = text.split()
        if word_count == 0:
            current_start = entry.get('start', 0)
        current_words.extend(words)
        word_count += len(words)
        
        if word_count >= 200:
            chunks.append({
                'text': ' '.join(current_words),
                'start_time': current_start,
                'chunk_index': len(chunks)
            })
            current_words = []
            word_count = 0
            current_start = 0
    
    # Don't forget the last chunk
    if current_words:
        chunks.append({
            'text': ' '.join(current_words),
            'start_time': current_start,
            'chunk_index': len(chunks)
        })
    
    print(f"Created {len(chunks)} chunks")
    return chunks
