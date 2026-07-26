import streamlit as st
import requests
import time
import os

st.set_page_config(page_title="YouTube TTS", page_icon="🎙️")

st.title("YouTube Transcript → Hindi TTS")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if st.button("Process Video"):
    if not video_url:
        st.error("Please enter a valid YouTube URL.")
    else:
        # submit job
        try:
            resp = requests.post(f"{API_BASE_URL}/process/", data={"video_url": video_url})
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("job_id")

            st.success(f"Job started! ID: {job_id}")

            status_placeholder = st.empty()

            while True:
                status_resp = requests.get(f"{API_BASE_URL}/status/{job_id}")
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    message = status_data.get("message")

                    status_placeholder.info(f"Status: {status} | Message: {message}")

                    if status == "done":
                        st.success("Audio processing complete!")
                        st.markdown(f"[Download MP3 here]({API_BASE_URL}/output/{job_id})")

                        # also provide a direct audio player
                        output_resp = requests.get(f"{API_BASE_URL}/output/{job_id}")
                        if output_resp.status_code == 200:
                            st.audio(output_resp.content, format="audio/mpeg")
                        break
                    elif status == "error":
                        st.error(f"Error: {status_data.get('error')}")
                        break
                else:
                    status_placeholder.warning("Waiting for status...")

                time.sleep(2)

        except Exception as e:
            st.error(f"Failed to submit request: {e}")
