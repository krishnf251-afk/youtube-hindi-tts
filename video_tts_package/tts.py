import os
import asyncio
from typing import List, Dict, Optional
import requests
from edge_tts import Communicate
from pydub import AudioSegment

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # required
GEMINI_API_URL = os.getenv("GEMINI_API_URL")  # required; user-provided translate endpoint
VOICE = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural")
BITRATE = os.getenv("MP3_BITRATE", "128k")

def translate_text_with_gemini(text: str) -> str:
    if not GEMINI_API_URL or not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_URL and GEMINI_API_KEY must be set in environment.")
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"input": text, "target_language": "hi"}
    try:
        resp = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            if "translated_text" in data:
                return data["translated_text"]
            if "translation" in data:
                return data["translation"]
            if "output" in data and isinstance(data["output"], str):
                return data["output"]
        if isinstance(data, str):
            return data
        raise RuntimeError(f"Unexpected Gemini response shape: {data}")
    except Exception as e:
        raise RuntimeError(f"Gemini translation failed: {str(e)}")

async def synthesize_text_to_file_async(text: str, out_path: str, voice: str = VOICE):
    comm = Communicate(text, voice)
    await comm.save(out_path)

def synthesize_and_align(chunks: List[Dict], tmpdir: str, job_id: str, JOBS: Optional[dict] = None) -> str:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    parts = []
    try:
        for i, c in enumerate(chunks):
            original_text = c.get('text', '').strip()
            start = float(c.get('start', 0.0))
            duration = float(c.get('duration', 0.0))
            if original_text:
                translated = translate_text_with_gemini(original_text)
            else:
                translated = ""

            if translated:
                part_path = os.path.join(tmpdir, f"tts_part_{i}.mp3")
                loop.run_until_complete(synthesize_text_to_file_async(translated, part_path))
                parts.append({'path': part_path, 'start': start, 'duration': duration})
            else:
                parts.append({'path': None, 'start': start, 'duration': duration})
            if JOBS is not None:
                JOBS[job_id]['message'] = f"synthesized_segment_{i}"
    except Exception as e:
        raise

    final = None
    for p in parts:
        start_ms = int(round(p['start'] * 1000))
        if final is None:
            final = AudioSegment.silent(duration=max(0, start_ms))
        else:
            if len(final) < start_ms:
                gap = start_ms - len(final)
                final += AudioSegment.silent(duration=gap)
        if p['path']:
            seg = AudioSegment.from_file(p['path'], format="mp3")
            final += seg
            try:
                os.remove(p['path'])
            except Exception:
                pass
        else:
            dur_ms = int(round(p.get('duration', 0.0) * 1000))
            if dur_ms > 0:
                final += AudioSegment.silent(duration=dur_ms)

    if final is None:
        final = AudioSegment.silent(duration=1000)

    out_mp3 = os.path.join(tmpdir, "final_audio.mp3")
    final.export(out_mp3, format="mp3", bitrate=BITRATE)
    return out_mp3

def ensure_audio_length(final_mp3_path: str, expected_duration_sec: Optional[float]):
    audio = AudioSegment.from_file(final_mp3_path, format="mp3")
    duration_ms = len(audio)
    if expected_duration_sec is not None:
        expected_ms = int(round(expected_duration_sec * 1000))
        if duration_ms < expected_ms:
            pad_ms = expected_ms - duration_ms
            audio += AudioSegment.silent(duration=pad_ms)
            audio.export(final_mp3_path, format="mp3", bitrate=BITRATE)
            duration_ms = expected_ms
    return duration_ms / 1000.0
