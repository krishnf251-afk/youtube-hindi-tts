import os
import tempfile
import traceback
import subprocess
import asyncio
import re
import streamlit as st
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import google.generativeai as genai
import edge_tts

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def extract_text_from_vtt(vtt_file):
    """VTT सबटाइटल फ़ाइल से केवल टेक्स्ट निकालता है"""
    extracted_text = []
    with open(vtt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if not re.match(r'^[0-9:\.]+\s-->', line) and not line.startswith('WEBVTT') and line.strip():
                clean_line = line.strip()
                if not extracted_text or extracted_text[-1] != clean_line:
                    extracted_text.append(clean_line)
    return " ".join(extracted_text)

async def generate_tts(text, voice, output_path):
    """Edge TTS का उपयोग करके AI आवाज़ बनाता है"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def run_async_task(coro):
    """Streamlit में Asyncio क्रैश को रोकने का फिक्स"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def apply_audio_ducking(video_input, dubbed_audio_path, output_path, is_stream=False):
    """FFmpeg का उपयोग करके डकिंग करता है (ओरिजिनल 30%, नई आवाज़ 150%)"""
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', video_input,
        '-i', dubbed_audio_path,
        '-filter_complex',
        '[0:a]volume=0.3[bg]; '
        '[1:a]volume=1.5[fg]; '
        '[bg][fg]sidechaincompress=threshold=0.015:ratio=6:attack=50:release=300[ducked_bg]; '
        '[ducked_bg][fg]amix=inputs=2:duration=first[final_audio]',
        '-map', '0:v',
        '-map', '[final_audio]',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_path
    ]
    
    if is_stream:
        ffmpeg_cmd.insert(1, '-reconnect')
        ffmpeg_cmd.insert(2, '1')
        ffmpeg_cmd.insert(3, '-reconnect_streamed')
        ffmpeg_cmd.insert(4, '1')
        ffmpeg_cmd.insert(5, '-reconnect_delay_max')
        ffmpeg_cmd.insert(6, '5')

    subprocess.run(ffmpeg_cmd, check=True)

# ==========================================
# 🖥️ MAIN UI & APP ENGINE (Personal Use)
# ==========================================

st.set_page_config(page_title="Vayu Anime Dub Studio", page_icon="🌪️", layout="wide")

st.title("🌪️ Vayu Anime Dub Studio")
st.write("पर्सनल डबिंग इंजन: लिंक डालें और AI ऑटोमैटिक ट्रांसलेट करके डब कर देगा।")

# Sidebar Configuration
st.sidebar.header("⚙️ Settings")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
cookies_text = st.sidebar.text_area("YouTube Cookies (Optional)", value=os.environ.get("YOUTUBE_COOKIES", ""))

# Main Inputs
youtube_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2, col3 = st.columns(3)

with col1:
    process_mode = st.radio("डबिंग का तरीका:", ["डायरेक्ट स्ट्रीम (Fast)", "वीडियो डाउनलोड करके (Stable)"])

with col2:
    ai_model_choice = st.radio("AI ट्रांसलेशन मॉडल चुनें:", ["Gemini 3.5 (Fast)", "Gemini 3.1 Pro (Deep Translation)"])

with col3:
    tts_voice = st.selectbox("आवाज़ (Voice)", ["hi-IN-MadhurNeural (Male)", "hi-IN-SwaraNeural (Female)"])
    actual_voice_id = "hi-IN-MadhurNeural" if "Madhur" in tts_voice else "hi-IN-SwaraNeural"

if st.button("🚀 Start Auto-Dubbing", type="primary"):
    if not youtube_url:
        st.warning("कृपया YouTube वीडियो का URL दर्ज करें!")
    elif not gemini_key:
        st.warning("AI ट्रांसलेशन के लिए Gemini API Key की ज़रूरत है!")
    else:
        status = st.status("इंजन चालू हो रहा है...", expanded=True)
        temp_dir = tempfile.mkdtemp()
        
        cookie_file = None
        if cookies_text.strip():
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as tf:
                tf.write(cookies_text)
                cookie_file = tf.name

        try:
            # STEP 1: Extract Subtitles (With Geo-Bypass applied)
            status.update(label="1/4: YouTube से सबटाइटल निकाले जा रहे हैं...", state="running")
            subtitle_path_base = os.path.join(temp_dir, "subs")
            
            ydl_opts_subs = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'ja'],
                'outtmpl': subtitle_path_base,
                'quiet': True,
                'nocheckcertificate': True,
                'force_ipv4': True,
                'impersonate': ImpersonateTarget(client='chrome'),
                'geo_bypass': True,           # 🚨 Geo-Block Fix 
                'geo_bypass_country': 'IN'    # 🚨 India Location
            }
            if cookie_file: ydl_opts_subs['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts_subs) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                video_title = info_dict.get('title', 'video')
                stream_url = info_dict.get('url', None)

            sub_files = [f for f in os.listdir(temp_dir) if f.endswith('.vtt')]
            if not sub_files:
                st.error("❌ इस वीडियो में कोई इंग्लिश या जापानी सबटाइटल नहीं मिला।")
                st.stop()
            
            extracted_text = extract_text_from_vtt(os.path.join(temp_dir, sub_files[0]))
            
            # STEP 2: Gemini AI Translation (Using Latest Models)
            status.update(label=f"2/4: {ai_model_choice} ट्रांसलेट कर रहा है...", state="running")
            genai.configure(api_key=gemini_key)
            
            selected_model = 'gemini-3.1-pro' if "3.1 Pro" in ai_model_choice else 'gemini-3.5-flash'
            model = genai.GenerativeModel(selected_model)
            
            prompt = f"Translate the following YouTube video transcript to natural sounding Hindi for a voiceover. Only return the Hindi translation, nothing else:\n\n{extracted_text[:5000]}"
            response = model.generate_content(prompt)
            hindi_script = response.text.strip()
            
            with st.expander("AI द्वारा जनरेट की गई स्क्रिप्ट देखें"):
                st.write(hindi_script)

            # STEP 3: Generate Voice
            status.update(label="3/4: स्क्रिप्ट से AI आवाज़ बनाई जा रही है...", state="running")
            tts_audio_path = os.path.join(temp_dir, "tts_audio.wav")
            run_async_task(generate_tts(hindi_script, actual_voice_id, tts_audio_path)) # 🚨 Asyncio Fix

            # STEP 4: Audio Ducking & Final Render
            final_output_path = os.path.join(temp_dir, f"Dubbed_Vayu_Personal.mp4")
            
            if "स्ट्रीम" in process_mode:
                status.update(label="4/4: डायरेक्ट स्ट्रीम से डबिंग हो रही है (No Download)...", state="running")
                apply_audio_ducking(stream_url, tts_audio_path, final_output_path, is_stream=True)
            else:
                status.update(label="4/4: वीडियो सर्वर पर डाउनलोड करके डबिंग हो रही है...", state="running")
                original_vid_path = os.path.join(temp_dir, "original.mp4")
                ydl_opts_vid = {
                    'format': 'best',
                    'outtmpl': original_vid_path,
                    'quiet': True,
                    'impersonate': ImpersonateTarget(client='chrome'),
                    'geo_bypass': True,           # 🚨 Geo-Block Fix
                    'geo_bypass_country': 'IN'    # 🚨 India Location
                }
                with yt_dlp.YoutubeDL(ydl_opts_vid) as ydl:
                    ydl.download([youtube_url])
                
                apply_audio_ducking(original_vid_path, tts_audio_path, final_output_path, is_stream=False)

            status.update(label="🎉 वीडियो डबिंग पूरी हुई!", state="complete")
            st.success("✅ आपका Vayu AI डब वीडियो तैयार है!")

            # Download Button
            with open(final_output_path, "rb") as file:
                st.download_button(
                    label="⬇️ डब किया हुआ वीडियो डाउनलोड करें",
                    data=file,
                    file_name="Vayu_Dubbed_Video.mp4",
                    mime="video/mp4",
                    type="primary"
                )

        except Exception as e:
            status.update(label="❌ एरर आया!", state="error")
            st.error("प्रोसेस फेल हो गया।")
            st.code(traceback.format_exc(), language="python")
            
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)
            
