import os
import streamlit as st

# 1. Playwright Setup
os.system("playwright install chromium")
os.system("playwright install-deps")

st.set_page_config(page_title="AnimeTube Hindi TTS", page_icon="🎙️", layout="wide")

st.title("🎙️ AnimeTube Hindi TTS Dashboard")

# Sidebar for Configuration (API Keys & Secrets)
st.sidebar.header("⚙️ App Settings")

# Gemini API Key input
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", help="Gemini API Key यहाँ डालें या Hugging Face Secrets में सेट करें")

# Cookies Input
cookies_text = st.sidebar.text_area("YouTube Cookies (TXT Format)", help="यहाँ अपनी youtube.com की cookies पेस्ट करें ताकि ब्लॉक न हो")

# Secrets check (अगर Hugging Face Secrets में सेट है तो वहाँ से पढ़ेगा)
if not gemini_key and "GEMINI_API_KEY" in os.environ:
    gemini_key = os.environ["GEMINI_API_KEY"]

# Main Interface for YouTube Link
st.subheader("1. YouTube वीडियो लिंक डालें")
youtube_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)

with col1:
    target_language = st.selectbox("अनुवाद की भाषा (Target Language)", ["Hindi", "English", "Japanese"])

with col2:
    tts_voice = st.selectbox("आवाज़ का प्रकार (Voice)", ["Male (hi-IN-MadhurNeural)", "Female (hi-IN-SwaraNeural)"])

if st.button("🚀 Process Video", type="primary"):
    if not youtube_url:
        st.warning("कृपया पहले YouTube वीडियो का URL दर्ज करें!")
    else:
        st.info("प्रोसेसिंग शुरू हो रही है... (अगले स्टेप में हम इस पर AI मॉडल कनेक्ट करेंगे)")
