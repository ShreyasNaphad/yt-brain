import logging
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp
import os
import tempfile
import json
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    url = url.strip()
    
    # 1. Handle youtu.be short links
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    
    parsed = urlparse(url)
    
    # 2. Handle standard watch?v= parameter
    params = parse_qs(parsed.query)
    if "v" in params:
        return params["v"][0]
        
    # 3. Handle path-based IDs (shorts, embed, live, v)
    path_segments = [p for p in parsed.path.split('/') if p]
    
    # Common path prefixes for video IDs
    target_segments = {'shorts', 'embed', 'live', 'v'}
    
    for i, segment in enumerate(path_segments):
        if segment in target_segments and i < len(path_segments) - 1:
            return path_segments[i+1]
            
    # 4. Fallback Regex (Capture 11 char ID)
    # This matches commonly found patterns if structure is slightly off
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)

    raise ValueError(f"Could not extract video ID from URL: {url}")

class YouTubeService:
    def __init__(self):
        # Configure yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a YouTube video URL using yt-dlp.
        Parses video_id from URL first.
        """
        # Parse video_id from URL
        try:
            video_id = extract_video_id(url)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "video_id": video_id,
                    "title": info.get("title"),
                    "channel": info.get("uploader"),
                    "thumbnail_url": info.get("thumbnail"),
                    "duration_seconds": info.get("duration"),
                    "url": url
                }
        except Exception as e:
            logger.error(f"Error fetching video info for {url}: {e}")
            # Fallback metadata so app doesn't crash
            return {
                "video_id": video_id,
                "title": "YouTube Video",
                "channel": "Unknown",
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "duration_seconds": 0,
                "url": url
            }

    def extract_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """
        Fetch transcript for a video using a robust multi-method strategy.
        """
        
        # METHOD 1: Try standard transcript fetch
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            print(f"Method 1 success: got {len(transcript)} entries")
            return transcript
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
        
        # METHOD 2: Try listing all available transcripts and use any one
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in transcript_list:
                try:
                    fetched = transcript.fetch()
                    print(f"Method 2 success: used transcript '{transcript.language}'")
                    return [{'text': e['text'], 'start': e['start'], 'duration': e.get('duration', 0)} for e in fetched]
                except:
                    continue
        except Exception as e2:
            print(f"Method 2 failed: {e2}")
        
        # METHOD 3: Try with translated/auto-generated captions
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in transcript_list:
                try:
                    translated = transcript.translate('en').fetch()
                    print(f"Method 3 success: translated from {transcript.language}")
                    return [{'text': e['text'], 'start': e['start'], 'duration': e.get('duration', 0)} for e in translated]
                except:
                    continue
        except Exception as e3:
            print(f"Method 3 failed: {e3}")

        # METHOD 4: Use yt-dlp to download auto-generated subtitles as text
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    'skip_download': True,
                    'writeautomaticsub': True,
                    'writesubtitles': True,
                    'subtitleslangs': ['en', 'en-US', 'en-GB'],
                    'subtitlesformat': 'json3',
                    'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                    'quiet': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
                
                # Find subtitle file
                found_transcript = []
                for fname in os.listdir(tmpdir):
                    if fname.endswith('.json3'):
                        with open(os.path.join(tmpdir, fname), encoding='utf-8') as f:
                            data = json.load(f)
                        
                        for event in data.get('events', []):
                            if 'segs' in event:
                                text = ' '.join(s.get('utf8', '') for s in event['segs']).strip()
                                if text and text != '\n':
                                    found_transcript.append({
                                        'text': text,
                                        'start': event.get('tStartMs', 0) / 1000,
                                        'duration': event.get('dDurationMs', 0) / 1000
                                    })
                        break # Successfully parsed one file
                
                if found_transcript:
                    print(f"Method 4 success: yt-dlp got {len(found_transcript)} entries")
                    return found_transcript
        except Exception as e4:
            print(f"Method 4 failed: {e4}")

        # METHOD 5: Use yt-dlp to get video description + title as fallback content
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
                description = info.get('description', '')
                title = info.get('title', '')
                chapters = info.get('chapters', [])
                
                # Build synthetic transcript from description + chapters
                content = f"Video Title: {title}\n\n"
                if chapters:
                    content += "Video Chapters:\n"
                    if isinstance(chapters, list):
                        for ch in chapters:
                            content += f"[{int(ch.get('start_time', 0))}s] {ch.get('title', '')}\n"
                    content += "\n"
                content += f"Video Description:\n{description}"
                
                # Split into fake transcript entries every 40 words
                entries = []
                words = content.split()
                chunk_size = 40
                start_time = 0
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    entries.append({'text': chunk, 'start': start_time, 'duration': 5})
                    start_time += 5
                
                if entries:
                    print(f"Method 5 success: using description/metadata as content")
                    return entries
        except Exception as e5:
            print(f"Method 5 failed: {e5}")

        raise HTTPException(
            status_code=400,
            detail="Could not extract any content from this video. Try a different video."
        )

    def chunk_transcript(self, transcript: List[Dict[str, Any]], chunk_size: int = 350, overlap: int = 40) -> List[Dict[str, Any]]:
        """
        Group transcript entries into chunks of ~350 words with 40-word overlap.
        Each chunk: {text, start_time, chunk_index}
        """
        if not transcript:
            return []

        chunks = []
        current_chunk_words = []
        current_chunk_start_time = transcript[0]['start']
        word_count = 0
        chunk_index = 0
        
        # Flatten transcript into a list of words with timestamps? 
        # Actually, transcript entries are phrases. We should probably chunk by phrases to maintain coherence,
        # but the requirement says "words". Let's stick to accumulating phrases until word count is reached.
        # A simpler approach for "words" is to join text and split, but we lose timestamps.
        # Better approach: Accumulate transcript entries until word count > chunk_size.
        
        # Sliding window over transcript entries might be too coarse if entries are long.
        # Let's iterate through transcript entries and maintain a buffer.
        
        # Pre-process: split all entries into word-level objects could be expensive but precise.
        # Let's try a hybrid: accumulate entries.
        
        # However, for overlap, we need to be able to backtrack.
        # Let's convert the transcript into a list of words with (word, start_time) tuples first?
        # That effectively reconstructs the timeline.
        
        flattened_words = []
        for entry in transcript:
            words = entry['text'].split()
            start = entry['start']
            duration = entry['duration']
            # Interpolate time? Or just assign start time to all words?
            # Assigning coarse start time is fine for retrieval.
            for w in words:
                flattened_words.append({"word": w, "start": start})
                
        # Sliding window with overlap
        i = 0
        while i < len(flattened_words):
            chunk_end = min(i + chunk_size, len(flattened_words))
            chunk_slice = flattened_words[i:chunk_end]
            
            chunk_text = " ".join([w['word'] for w in chunk_slice])
            start_time = chunk_slice[0]['start']
            
            chunks.append({
                "text": chunk_text,
                "start_time": start_time,
                "chunk_index": chunk_index
            })
            
            chunk_index += 1
            i += (chunk_size - overlap)

        # Performance Optimization: Cap at 20 chunks
        # If we have too many chunks, it slows down embedding and context window.
        # We sample evenly to cover the whole video.
        MAX_CHUNKS = 20
        if len(chunks) > MAX_CHUNKS:
            logger.info(f"Downsampling chunks from {len(chunks)} to {MAX_CHUNKS}")
            step = len(chunks) // MAX_CHUNKS
            # Sample every 'step' items, take first 20
            chunks = chunks[::step][:MAX_CHUNKS]
            # Re-index
            for idx, chunk in enumerate(chunks):
                chunk["chunk_index"] = idx
            
        return chunks
