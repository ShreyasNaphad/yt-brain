import logging
import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Any

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
        pass
    
    # Note: metadata and transcript extraction methods were moved directly
    # to routes/video.py to avoid yt-dlp dependencies on Render servers.
