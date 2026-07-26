import streamlit as st
import os
import tempfile
import uuid
import shutil
import traceback
from transcript import fetch_transcript_segments
from tts import synthesize_and_align, ensure_audio_length

st.set_page_config(page_title="YouTube TTS", page_icon="🎙️")

st.title("YouTube Transcript → Hindi TTS")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if st.button("Process Video"):
    if not video_url:
        st.error("Please enter a valid YouTube URL.")
    else:
        with st.status("Processing Video...", expanded=True) as status:
            job_id = uuid.uuid4().hex[:16]
            st.write(f"Job ID: {job_id}")

            tmpdir = None
            try:
                st.write("Fetching transcript...")
                segments = fetch_transcript_segments(video_url)
                st.write(f"Transcript fetched! Found {len(segments)} segments.")

                tmpdir = tempfile.mkdtemp(prefix="vt_")
                st.write("Translating and synthesizing audio (this may take a while)...")

                final_mp3 = synthesize_and_align(segments, tmpdir, job_id)

                st.write("Ensuring proper audio length...")
                last_seg = segments[-1]
                expected = last_seg['start'] + last_seg['duration']
                actual_sec = ensure_audio_length(final_mp3, expected)

                out_name = f"{job_id}.mp3"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                shutil.move(final_mp3, out_path)

                status.update(label="Audio processing complete!", state="complete", expanded=False)

                st.success(f"Processing complete! Length: {actual_sec:.2f}s")

                # Provide audio player
                with open(out_path, "rb") as f:
                    audio_bytes = f.read()

                st.audio(audio_bytes, format="audio/mpeg")

                # Provide download button
                st.download_button(
                    label="Download MP3",
                    data=audio_bytes,
                    file_name=out_name,
                    mime="audio/mpeg"
                )

            except Exception as e:
                status.update(label="Processing failed", state="error", expanded=True)
                st.error(f"Error: {e}")
                st.code(traceback.format_exc())
            finally:
                if tmpdir and os.path.isdir(tmpdir):
                    shutil.rmtree(tmpdir)
