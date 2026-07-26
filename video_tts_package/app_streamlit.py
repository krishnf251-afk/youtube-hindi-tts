import streamlit as st
import time
import os
import uuid
import tempfile
import shutil
import traceback
from dotenv import load_dotenv

load_dotenv()

# Import refactored modules directly
from transcript import fetch_transcript_segments
from tts import synthesize_and_align, ensure_audio_length

st.set_page_config(page_title="YouTube TTS", page_icon="🎙️")

st.title("YouTube Transcript → Hindi TTS")

video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if st.button("Process Video"):
    if not video_url:
        st.error("Please enter a valid YouTube URL.")
    else:
        job_id = uuid.uuid4().hex[:16]
        # JOBS dict to pass to synthesize_and_align to track progress message
        job_state = {job_id: {"message": "starting"}}

        tmpdir = None

        try:
            with st.status("Processing video...") as status:
                st.write("Fetching transcript...")
                segments = fetch_transcript_segments(video_url)

                st.write(f"Fetched {len(segments)} segments. Synthesizing TTS...")
                tmpdir = tempfile.mkdtemp(prefix="vt_")

                # We can't easily hook into the exact message updates inside the loop in tts.py using st.status dynamically without threading,
                # but we can just run it synchronously since this is Streamlit.
                final_mp3 = synthesize_and_align(segments, tmpdir, job_id, job_state)

                st.write("Ensuring audio length...")
                last_seg = segments[-1]
                expected = last_seg['start'] + last_seg['duration']
                actual_sec = ensure_audio_length(final_mp3, expected)

                status.update(label="Audio processing complete!", state="complete", expanded=True)

            st.success(f"Processing complete! Audio length: {actual_sec:.2f}s")

            # Read audio file before cleanup
            with open(final_mp3, "rb") as f:
                audio_bytes = f.read()

            st.audio(audio_bytes, format="audio/mpeg")
            st.download_button(label="Download MP3", data=audio_bytes, file_name=f"{job_id}.mp3", mime="audio/mpeg")

        except Exception as e:
            st.error(f"Failed to process video: {str(e)}")
            st.error(traceback.format_exc())
        finally:
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)
