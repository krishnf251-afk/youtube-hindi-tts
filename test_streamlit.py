import os
import tempfile
import streamlit as st
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import google.generativeai as genai

# 1. Playwright Setup
os.system("playwright install chromium")
os.system("playwright install-deps")

st.set_page_config(page_title="AnimeTube Hindi TTS", page_icon="🎙️", layout="wide")

st.title("🎙️ AnimeTube Hindi TTS Dashboard")

# Sidebar for Configuration
st.sidebar.header("⚙️ App Settings")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
cookies_text = st.sidebar.text_area("YouTube Cookies (TXT Format)")

# Environment variable fallback for Secrets
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
        
        # Temp file for cookies if provided
        cookie_file_path = None
        if cookies_text.strip():
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as tf:
                tf.write(cookies_text)
                cookie_file_path = tf.name

        try:
            # Step 1: Fetching video details with yt-dlp
            status_box.update(label="YouTube से वीडियो की जानकारी निकाली जा रही है...", state="running")
            
            # ⚠️ ULTIMATE ANTI-BLOCK & AUTO-CLEAN SETTINGS ⚠️
            ydl_opts = {
                'quiet': True, 
                'nocheckcertificate': True,
                'force_ipv4': True,      
                'extractor_retries': 3,  
                'socket_timeout': 30,    
                'impersonate': ImpersonateTarget(client='chrome'), # 🚨 असली ब्राउज़र का मुखौटा
                'cachedir': False,        # 🧹 कचरा (Cache) जमा नहीं होने देगा
                'geo_bypass': True
            }
            
            if cookie_file_path:
                ydl_opts['cookiefile'] = cookie_file_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_title = info.get('title', 'YouTube Video')
                
            st.success(f"वीडियो मिल गया: **{video_title}**")
            
            # Step 2: Gemini API Integration Test
            if gemini_key:
                status_box.update(label="Gemini AI मॉडल से कनेक्ट किया जा रहा है...", state="running")
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'Gemini AI connection successful!' in Hindi.")
                st.info(f"🤖 Gemini AI का रिस्पॉन्स: {response.text}")
            else:
                st.warning("Gemini API Key नहीं मिली, AI ट्रांसलेशन स्किप किया गया।")

            status_box.update(label="प्रोसेसिंग पूर्ण हुई!", state="complete")

        except Exception as e:
            status_box.update(label="एरर आया!", state="error")
            st.error(f"कुछ गड़बड़ हुई: {str(e)}")
            
        finally:
            # यह हिस्सा टेस्ट के तुरंत बाद टेम्परेरी कुकी फाइल को भी डिलीट कर देता है
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)
