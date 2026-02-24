import re
import httpx
import yt_dlp
from urllib.parse import urlparse, parse_qs
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
    return {
        "video_id": video_id,
        "title": "YouTube Video",
        "channel": "Unknown",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "duration_seconds": 0,
        "url": url
    }

def get_ydl_opts(tmpdir=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        # Rotate through these to avoid IP blocks
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
        # Pretend to be a real browser
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        'socket_timeout': 30,
    }
    if tmpdir:
        opts['outtmpl'] = f'{tmpdir}/%(id)s.%(ext)s'
    return opts

def extract_transcript(video_id: str) -> list:
    import tempfile, os, json

    # METHOD 1: yt-dlp with android client (bypasses most IP blocks)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = get_ydl_opts(tmpdir)
            ydl_opts.update({
                'writeautomaticsub': True,
                'writesubtitles': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB', 'en.*'],
                'subtitlesformat': 'json3',
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f'https://www.youtube.com/watch?v={video_id}',
                    download=True
                )
            
            # Find the subtitle file
            for fname in os.listdir(tmpdir):
                if fname.endswith('.json3'):
                    with open(os.path.join(tmpdir, fname), 'r') as f:
                        data = json.load(f)
                    transcript = []
                    for event in data.get('events', []):
                        if 'segs' in event:
                            text = ' '.join(
                                s.get('utf8', '') for s in event['segs']
                            ).strip()
                            if text and text != '\n':
                                transcript.append({
                                    'text': text,
                                    'start': event.get('tStartMs', 0) / 1000,
                                    'duration': event.get('dDurationMs', 0) / 1000
                                })
                    if transcript:
                        print(f"Method 1 success: {len(transcript)} entries")
                        return transcript
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # METHOD 2: yt-dlp fetch info dict subtitles directly without downloading
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
        
        # Try automatic captions first then manual
        captions = info.get('automatic_captions', {})
        manual = info.get('subtitles', {})
        
        # Merge, prefer manual
        all_captions = {**captions, **manual}
        
        for lang in ['en', 'en-US', 'en-GB']:
            if lang in all_captions:
                for fmt in all_captions[lang]:
                    if fmt.get('ext') == 'json3':
                        try:
                            with httpx.Client(timeout=15) as client:
                                r = client.get(fmt['url'])
                                data = r.json()
                            transcript = []
                            for event in data.get('events', []):
                                if 'segs' in event:
                                    text = ' '.join(
                                        s.get('utf8', '') for s in event['segs']
                                    ).strip()
                                    if text and text != '\n':
                                        transcript.append({
                                            'text': text,
                                            'start': event.get('tStartMs', 0) / 1000,
                                            'duration': event.get('dDurationMs', 0) / 1000
                                        })
                            if transcript:
                                print(f"Method 2 success: {len(transcript)} entries")
                                return transcript
                        except Exception as e:
                            print(f"Method 2 fmt fetch failed: {e}")
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # METHOD 3: Use description + chapters as fallback content
    # so app never completely fails
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
        title = info.get('title', '')
        description = info.get('description', '')
        chapters = info.get('chapters', [])
        
        content = f"Video Title: {title}\n\n"
        if chapters:
            content += "Video Chapters:\n"
            for ch in chapters:
                content += f"[{int(ch['start_time'])}s] {ch['title']}\n"
            content += "\n"
        if description:
            content += f"Description:\n{description[:3000]}"
        
        if len(content) > 100:
            words = content.split()
            entries = []
            start_time = 0
            for i in range(0, len(words), 50):
                chunk = ' '.join(words[i:i+50])
                entries.append({
                    'text': chunk,
                    'start': start_time,
                    'duration': 10
                })
                start_time += 10
            print(f"Method 3 fallback: {len(entries)} entries from description")
            return entries
    except Exception as e:
        print(f"Method 3 failed: {e}")

    raise HTTPException(
        status_code=400,
        detail="Could not extract transcript or content from this video. The video may be private, age-restricted, or have no captions."
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
    
    if current_words:
        chunks.append({
            'text': ' '.join(current_words),
            'start_time': current_start,
            'chunk_index': len(chunks)
        })
    
    print(f"Created {len(chunks)} chunks")
    return chunks
