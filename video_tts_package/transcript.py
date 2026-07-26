import re
from typing import List, Dict, Optional
import yt_dlp
import requests

def extract_video_id(url_or_id: str) -> str:
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    m = re.search(r'(?:v=|\/)([A-Za-z0-9_-]{11})', url_or_id)
    if m:
        return m.group(1)
    return url_or_id

def fetch_transcript_segments(video_url_or_id: str, languages: Optional[List[str]] = None) -> List[Dict]:
    vid = extract_video_id(video_url_or_id)
    if languages is None:
        languages = ['en', 'ja', 'zh', 'ko']

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': languages,
        'subtitlesformat': 'json3',
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(vid, download=False)
        except Exception as e:
            raise Exception(f"yt-dlp extraction failed: {e}")

        subs = info.get('requested_subtitles')
        if not subs:
            raise Exception(f"No transcript found for {vid}")

        # Prioritize languages in the order requested, or grab the first available
        chosen_lang = None
        for lang in languages:
            if lang in subs:
                chosen_lang = lang
                break

        if not chosen_lang and subs:
            chosen_lang = list(subs.keys())[0]

        if not chosen_lang:
            raise Exception(f"No transcript found for {vid}")

        url = subs[chosen_lang]['url']
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise Exception(f"Failed to download or parse json3 transcript: {e}")

        normalized = []
        for event in data.get('events', []):
            start = event.get('tStartMs', 0) / 1000.0
            duration = event.get('dDurationMs', 0) / 1000.0
            segs = event.get('segs', [])
            text = "".join([seg.get('utf8', '') for seg in segs]).strip()
            # Ignore empty segments
            if not text and not normalized:
                continue
            normalized.append({
                'start': float(start),
                'duration': float(duration),
                'text': text
            })

        if not normalized:
            raise Exception(f"No valid transcript segments found for {vid}")

        return normalized
