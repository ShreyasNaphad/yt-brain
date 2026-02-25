import re
import httpx
import json
import logging
from urllib.parse import urlparse, parse_qs
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Video ID extraction
# ---------------------------------------------------------------------------

def extract_video_id(url: str) -> str:
    url = url.strip()
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "v" in params:
        return params["v"][0]
    raise ValueError(f"Could not extract video ID from URL: {url}")

# ---------------------------------------------------------------------------
# Metadata via oEmbed (always works, even on cloud)
# ---------------------------------------------------------------------------

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
        logger.warning(f"oEmbed failed: {e}")
    return {
        "video_id": video_id,
        "title": "YouTube Video",
        "channel": "Unknown",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "duration_seconds": 0,
        "url": url
    }

# ---------------------------------------------------------------------------
# LAYER 1: Innertube API — Android client (best for cloud servers)
# ---------------------------------------------------------------------------

_INNERTUBE_CLIENTS = {
    "android": {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US",
                "userAgent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            }
        },
        "headers": {
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "X-YouTube-Client-Name": "3",
            "X-YouTube-Client-Version": "19.09.37",
        },
    },
    "web": {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240313.05.00",
                "hl": "en",
                "gl": "US",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            }
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": "2.20240313.05.00",
        },
    },
    "ios": {
        "context": {
            "client": {
                "clientName": "IOS",
                "clientVersion": "19.09.3",
                "deviceModel": "iPhone14,3",
                "hl": "en",
                "gl": "US",
                "userAgent": "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)",
            }
        },
        "headers": {
            "User-Agent": "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)",
            "X-YouTube-Client-Name": "5",
            "X-YouTube-Client-Version": "19.09.3",
        },
    },
}

def _innertube_get_player(video_id: str, client_name: str = "android") -> dict | None:
    """Fetch video player info via Innertube player endpoint."""
    cfg = _INNERTUBE_CLIENTS[client_name]
    payload = {
        "context": cfg["context"],
        "videoId": video_id,
    }
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
                json=payload,
                headers={
                    **cfg["headers"],
                    "Content-Type": "application/json",
                },
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.warning(f"Innertube player ({client_name}) failed: {e}")
    return None


def _innertube_transcript(video_id: str, client_name: str = "android") -> list | None:
    """
    Attempt to get transcript via Innertube.
    Step 1: Get captions URL from player endpoint.
    Step 2: Fetch the timedtext XML/JSON.
    Step 3: Parse into transcript entries.
    """
    cfg = _INNERTUBE_CLIENTS[client_name]

    # Step 1: get player info for caption track URLs
    player_data = _innertube_get_player(video_id, client_name)
    if not player_data:
        return None

    captions = player_data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])

    if not tracks:
        logger.info(f"Innertube ({client_name}): no caption tracks found")
        return None

    # Prefer English tracks
    caption_url = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang.startswith("en"):
            caption_url = track.get("baseUrl")
            break
    # Fallback to first track (auto-translate to English)
    if not caption_url and tracks:
        caption_url = tracks[0].get("baseUrl")
        if caption_url:
            caption_url += "&tlang=en"

    if not caption_url:
        return None

    # Request JSON3 format
    if "fmt=" not in caption_url:
        caption_url += "&fmt=json3"
    else:
        caption_url = caption_url.replace("fmt=srv3", "fmt=json3").replace("fmt=srv1", "fmt=json3")

    # Step 2: fetch the captions (long timeout for 3hr+ videos)
    try:
        with httpx.Client(timeout=60) as client:
            r = client.get(caption_url, headers=cfg["headers"])
            if r.status_code != 200:
                logger.warning(f"Innertube ({client_name}): caption fetch HTTP {r.status_code}")
                return None
            data = r.json()
    except Exception as e:
        # Maybe XML format — try parsing as XML
        try:
            return _parse_xml_captions(r.text)
        except Exception:
            logger.warning(f"Innertube ({client_name}): caption parse failed: {e}")
            return None

    # Step 3: parse JSON3 format
    transcript = []
    for event in data.get("events", []):
        if "segs" in event:
            text = " ".join(
                s.get("utf8", "") for s in event["segs"]
            ).strip()
            if text and text != "\n":
                transcript.append({
                    "text": text,
                    "start": event.get("tStartMs", 0) / 1000,
                    "duration": event.get("dDurationMs", 0) / 1000,
                })

    if transcript:
        logger.info(f"Innertube ({client_name}) success: {len(transcript)} entries")
        return transcript

    return None


def _parse_xml_captions(xml_text: str) -> list | None:
    """Parse XML timedtext (srv1/srv3) format as fallback."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)
    transcript = []
    for elem in root.iter("text"):
        text = (elem.text or "").strip()
        if text:
            start = float(elem.get("start", 0))
            dur = float(elem.get("dur", 0))
            transcript.append({"text": text, "start": start, "duration": dur})
    return transcript if transcript else None

# ---------------------------------------------------------------------------
# LAYER 2: youtube-transcript-api library
# ---------------------------------------------------------------------------

def _youtube_transcript_api(video_id: str) -> list | None:
    """Try the youtube-transcript-api library."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Try fetching transcript — supports both old and new API versions
        try:
            # New API (v1.0+)
            ytt_api = YouTubeTranscriptApi()
            transcript_data = ytt_api.fetch(video_id, languages=["en", "en-US", "en-GB"])
            transcript = []
            for snippet in transcript_data:
                text = snippet.text.strip() if hasattr(snippet, 'text') else str(snippet.get('text', '')).strip()
                start = snippet.start if hasattr(snippet, 'start') else snippet.get('start', 0)
                duration = snippet.duration if hasattr(snippet, 'duration') else snippet.get('duration', 0)
                if text:
                    transcript.append({
                        "text": text,
                        "start": float(start),
                        "duration": float(duration),
                    })
            if transcript:
                logger.info(f"youtube-transcript-api (new) success: {len(transcript)} entries")
                return transcript
        except Exception as e1:
            logger.info(f"youtube-transcript-api new API failed: {e1}, trying old API...")
            # Old API (pre-1.0)
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=["en", "en-US", "en-GB"]
                )
                transcript = []
                for entry in transcript_list:
                    text = entry.get("text", "").strip()
                    if text:
                        transcript.append({
                            "text": text,
                            "start": entry.get("start", 0),
                            "duration": entry.get("duration", 0),
                        })
                if transcript:
                    logger.info(f"youtube-transcript-api (old) success: {len(transcript)} entries")
                    return transcript
            except Exception as e2:
                logger.warning(f"youtube-transcript-api old API also failed: {e2}")
    except ImportError:
        logger.warning("youtube-transcript-api not installed, skipping")
    except Exception as e:
        logger.warning(f"youtube-transcript-api failed: {e}")
    return None

# ---------------------------------------------------------------------------
# LAYER 3: yt-dlp (works well locally, often blocked on cloud)
# ---------------------------------------------------------------------------

def _yt_dlp_transcript(video_id: str) -> list | None:
    """Try yt-dlp subtitle extraction — works best locally."""
    try:
        import yt_dlp
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writeautomaticsub": True,
                "writesubtitles": True,
                "subtitleslangs": ["en", "en-US", "en-GB", "en.*"],
                "subtitlesformat": "json3",
                "outtmpl": f"{tmpdir}/%(id)s.%(ext)s",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                    }
                },
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "socket_timeout": 30,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=True,
                )

            # Find the subtitle file
            for fname in os.listdir(tmpdir):
                if fname.endswith(".json3"):
                    with open(os.path.join(tmpdir, fname), "r") as f:
                        data = json.load(f)
                    transcript = []
                    for event in data.get("events", []):
                        if "segs" in event:
                            text = " ".join(
                                s.get("utf8", "") for s in event["segs"]
                            ).strip()
                            if text and text != "\n":
                                transcript.append({
                                    "text": text,
                                    "start": event.get("tStartMs", 0) / 1000,
                                    "duration": event.get("dDurationMs", 0) / 1000,
                                })
                    if transcript:
                        logger.info(f"yt-dlp success: {len(transcript)} entries")
                        return transcript
    except ImportError:
        logger.info("yt-dlp not installed, skipping")
    except Exception as e:
        logger.warning(f"yt-dlp failed: {e}")
    return None

# ---------------------------------------------------------------------------
# LAYER 4: Metadata-only fallback (always works)
# ---------------------------------------------------------------------------

def _metadata_fallback(video_id: str) -> list | None:
    """Last resort: build minimal transcript from oEmbed metadata."""
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with httpx.Client(timeout=10) as client:
            r = client.get(oembed_url)
            if r.status_code == 200:
                data = r.json()
                title = data.get("title", "")
                author = data.get("author_name", "")
                content = f"Video Title: {title}\nChannel: {author}\n\nNote: Full transcript was not available for this video. Analysis is based on video metadata only."
                if len(content) > 30:
                    logger.info(f"Metadata fallback: using title/channel info")
                    return [{
                        "text": content,
                        "start": 0,
                        "duration": 0,
                    }]
    except Exception as e:
        logger.warning(f"Metadata fallback failed: {e}")
    return None

# ---------------------------------------------------------------------------
# Main transcript extraction — tries all layers in order
# ---------------------------------------------------------------------------

def extract_transcript(video_id: str) -> list:
    """
    Extract transcript using a multi-layered approach.
    Tries methods from most-likely-to-work-on-cloud to least:
      1. Innertube API (Android client)
      2. Innertube API (iOS client)  
      3. Innertube API (Web client)
      4. youtube-transcript-api library
      5. yt-dlp (mostly works locally)
      6. Metadata fallback (always works)
    """
    methods = [
        ("Innertube Android", lambda: _innertube_transcript(video_id, "android")),
        ("Innertube iOS",     lambda: _innertube_transcript(video_id, "ios")),
        ("Innertube Web",     lambda: _innertube_transcript(video_id, "web")),
        ("youtube-transcript-api", lambda: _youtube_transcript_api(video_id)),
        ("yt-dlp",            lambda: _yt_dlp_transcript(video_id)),
        ("Metadata fallback", lambda: _metadata_fallback(video_id)),
    ]

    for name, method in methods:
        logger.info(f"Trying method: {name}...")
        try:
            result = method()
            if result:
                logger.info(f"SUCCESS with {name}: {len(result)} transcript entries")
                return result
        except Exception as e:
            logger.warning(f"{name} raised exception: {e}")

    raise HTTPException(
        status_code=400,
        detail="Could not extract transcript or content from this video. The video may be private, age-restricted, or have no captions."
    )

# ---------------------------------------------------------------------------
# Chunking (unchanged)
# ---------------------------------------------------------------------------

def chunk_transcript(transcript: list) -> list:
    chunks = []
    current_words = []
    current_start = 0
    word_count = 0

    for entry in transcript:
        text = entry.get("text", "").strip()
        if not text:
            continue
        words = text.split()
        if word_count == 0:
            current_start = entry.get("start", 0)
        current_words.extend(words)
        word_count += len(words)

        if word_count >= 200:
            chunks.append({
                "text": " ".join(current_words),
                "start_time": current_start,
                "chunk_index": len(chunks),
            })
            current_words = []
            word_count = 0
            current_start = 0

    if current_words:
        chunks.append({
            "text": " ".join(current_words),
            "start_time": current_start,
            "chunk_index": len(chunks),
        })

    logger.info(f"Created {len(chunks)} chunks")
    return chunks
