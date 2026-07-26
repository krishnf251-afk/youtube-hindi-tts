
# Lightweight YouTube Transcript → Hindi TTS

This package contains a single-file FastAPI app that:
- Fetches YouTube transcripts (no video download)
- Translates segments to Hindi via Gemini HTTP endpoint
- Synthesizes Hindi audio using edge-tts (hi-IN-MadhurNeural)
- Aligns audio with transcript timestamps using pydub
- Produces a single synced MP3 per job

## Quick start

1. Install system dependency ffmpeg (required by pydub).
2. Create a virtualenv and install Python packages:
   pip install -r requirements.txt

3. Copy `.env.example` to `.env` and fill GEMINI_API_URL and GEMINI_API_KEY.

4. Run the app:
   uvicorn app:app --host 0.0.0.0 --port 8000

5. Use the API:
   POST /process/ with form field `video_url`
   GET /status/{job_id}
   GET /output/{job_id} to download the mp3 when ready

## Notes
- The app requires that the YouTube video has subtitles (auto/manual). If no transcript exists, the job will error.
- Adjust GEMINI API request/response parsing in app.py if your Gemini wrapper uses a different JSON schema.
- Do not commit your API keys to source control.
