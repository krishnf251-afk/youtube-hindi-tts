# app.py
import os
import uuid
import shutil
import tempfile
import traceback
from typing import Optional
from fastapi import FastAPI, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Import refactored modules
from transcript import fetch_transcript_segments
from tts import synthesize_and_align, ensure_audio_length

load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# In-memory job store (keeps tiny state only)
JOBS = {}  # job_id -> {status, message, output_path or error}

app = FastAPI(title="Lightweight YouTube Transcript → Hindi TTS (no-download)")

def process_video_task(video_url: str, job_id: str):
    JOBS[job_id] = {"status": "started", "message": "queued", "output": None, "error": None}
    tmpdir = None
    try:
        JOBS[job_id]['status'] = "fetching_transcript"
        JOBS[job_id]['message'] = "fetching_transcript"
        segments = fetch_transcript_segments(video_url)
        JOBS[job_id]['status'] = "transcript_fetched"
        JOBS[job_id]['message'] = f"segments:{len(segments)}"

        tmpdir = tempfile.mkdtemp(prefix="vt_")
        JOBS[job_id]['message'] = "synthesizing_tts"
        # pass JOBS so the dict updates in place
        final_mp3 = synthesize_and_align(segments, tmpdir, job_id, JOBS)

        JOBS[job_id]['message'] = "ensuring_length"
        last_seg = segments[-1]
        expected = last_seg['start'] + last_seg['duration']
        actual_sec = ensure_audio_length(final_mp3, expected)

        out_name = f"{job_id}.mp3"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        shutil.move(final_mp3, out_path)

        JOBS[job_id]['status'] = "done"
        JOBS[job_id]['message'] = f"ready length={actual_sec:.2f}s"
        JOBS[job_id]['output'] = out_path
        return
    except Exception as e:
        tb = traceback.format_exc()
        JOBS[job_id]['status'] = "error"
        JOBS[job_id]['error'] = str(e)
        JOBS[job_id]['message'] = f"error:{str(e)}"
        print("PROCESS ERROR:", str(e))
        print(tb)
    finally:
        try:
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir)
        except Exception:
            pass

import threading

@app.post("/process/")
async def process_endpoint(video_url: str = Form(...), background_tasks: BackgroundTasks = None):
    job_id = uuid.uuid4().hex[:16]
    JOBS[job_id] = {"status": "queued", "message": "job_created", "output": None, "error": None}
    if background_tasks is not None:
        background_tasks.add_task(process_video_task, video_url, job_id)
    else:
        t = threading.Thread(target=process_video_task, args=(video_url, job_id), daemon=True)
        t.start()
    return {"job_id": job_id, "status_url": f"/status/{job_id}", "output_url": f"/output/{job_id}"}

@app.get("/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "status": job.get("status"), "message": job.get("message"), "error": job.get("error")}

@app.get("/output/{job_id}")
def output(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done" or not job.get("output"):
        raise HTTPException(status_code=400, detail="output not ready")
    return FileResponse(job["output"], media_type="audio/mpeg", filename=os.path.basename(job["output"]))

@app.get("/")
def root():
    return JSONResponse({"info": "Lightweight transcript->translate->TTS service. POST /process/ with form field video_url."})
