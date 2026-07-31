import os
import tempfile
import traceback
import streamlit as st
import yt_dlp
import google.generativeai as genai

st.set_page_config(page_title="AnimeTube Hindi TTS", page_icon="🎙️", layout="wide")

st.title("🎙️ AnimeTube Hindi TTS Dashboard")

# Sidebar for Configuration
st.sidebar.header("⚙️ App Settings")
st.sidebar.info("💡 API Key और Cookies अब Hugging Face Secrets से अपने आप ले लिए जाएंगे।")
gemini_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password")
cookies_text = st.sidebar.text_area("YouTube Cookies (Optional)")

# 🚨 HUGGING FACE SECRETS SE AUTOMATIC FETCHING 🚨
if not gemini_key and "GEMINI_API_KEY" in os.environ:
    gemini_key = os.environ["GEMINI_API_KEY"]

if not cookies_text and "YOUTUBE_COOKIES" in os.environ:
    cookies_text = os.environ["YOUTUBE_COOKIES"]

# Main UI
st.subheader("1. YouTube वीडियो लिंक डालें")
youtube_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    target_language = st.selectbox("अनुवाद की भाषा (Target Language)", ["Hindi", "English", "Japanese"])
with col2:
    tts_voice = st.selectbox("आवाज़ का प्रकार (Voice)", ["hi-IN-MadhurNeural (Male)", "hi-IN-SwaraNeural (Female)"])

if st.button("🚀 Process Video", type="primary"):
    if not youtube_url:
        st.warning("कृपया पहले YouTube वीडियो का URL दर्ज करें!")
    else:
        status_box = st.status("प्रोसेसिंग शुरू हो रही है...", expanded=True)
        
        cookie_file_path = None
        if cookies_text and cookies_text.strip():
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as tf:
                tf.write(cookies_text)
                cookie_file_path = tf.name

        try:
            status_box.update(label="YouTube से वीडियो की जानकारी निकाली जा रही है...", state="running")
            
            # ⚠️ LATEST ANTI-BLOCK SETTINGS (Impersonate हटा दिया गया है) ⚠️
            ydl_opts = {
                'quiet': True, 
                'nocheckcertificate': True,
                'force_ipv4': True,      
                'extractor_retries': 3,  
                'socket_timeout': 30,    
                'cachedir': False
            }
            
            if cookie_file_path:
                ydl_opts['cookiefile'] = cookie_file_path

            # Fetch Video Info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_title = info.get('title', 'YouTube Video')
                
            st.success(f"✅ वीडियो मिल गया: **{video_title}**")
            
            # Test Gemini Connection
            if gemini_key:
                status_box.update(label="Gemini AI मॉडल से कनेक्ट किया जा रहा है...", state="running")
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'Gemini AI connection successful!' in Hindi.")
                st.info(f"🤖 Gemini AI का रिस्पॉन्स: {response.text}")
            else:
                st.warning("⚠️ Gemini API Key नहीं मिली, AI ट्रांसलेशन स्किप किया गया।")

            status_box.update(label="प्रोसेसिंग पूर्ण हुई!", state="complete")

        except Exception as e:
            status_box.update(label="एरर आया!", state="error")
            st.error("❌ प्रोसेस फेल हो गया। नीचे दी गई जानकारी देखें:")
            st.code(traceback.format_exc(), language="python")
            
        finally:
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)
