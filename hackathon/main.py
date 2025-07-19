import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
from utils.voice_matcher import enroll_user, identify_user
import numpy as np
import av
import wave
import tempfile
import os
import time
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Initialize session state
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

st.set_page_config(page_title="FinSight(TBD)", layout="centered")

st.markdown("""
    <style>
    .fade-in {
        animation: fadeIn 1.5s ease-in forwards;
    }

    .slide-up {
        animation: slideUp 1.3s ease-out forwards;
    }

    .pulse {
        animation: pulse 2s infinite;
    }

    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(10px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideUp {
        0% { transform: translateY(30px); opacity: 0; }
        100% { transform: translateY(0); opacity: 1; }
    }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    </style>
""", unsafe_allow_html=True)

# Collapse sidebar on initial load (once)
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = True

    st.markdown("""
        <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)

    st.rerun()

st.title("FinSight")

PAGES = ["Login (Authenticate)", "Onboarding (Enroll)"]  # login first
default_page = PAGES[0]

if "current_page" not in st.session_state:
    st.session_state.current_page = default_page

if not st.session_state.authenticated_user:
    page = st.sidebar.radio("Navigation", PAGES, index=PAGES.index(st.session_state.current_page))
else:
    page = "Dashboard"


# AudioProcessor definition
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        audio = frame.to_ndarray()
        self.frames.append(audio)
        return frame

    def get_audio_data(self):
        if self.frames:
            return np.concatenate(self.frames)
        return None


# Save recorded audio
def save_audio(audio_data, sample_rate=48000):
    wav_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return wav_path


# ------------------ Onboarding -------------------
if page == "Onboarding (Enroll)":
    st.subheader("🧾 Onboarding: Enroll Your Voice")
    user_id = st.text_input("Enter a unique username to enroll")

    st.markdown("🎙️ Say something like: 'My name is John and this is my voice.'")

    ctx = webrtc_streamer(
        key="voice-auth-enroll",
        mode=WebRtcMode.SENDRECV,
        audio_receiver_size=1024,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        audio_processor_factory=AudioProcessor,
    )

    if ctx.audio_processor and st.button("🎤 Enroll Voice"):
        audio_data = ctx.audio_processor.get_audio_data()
        if audio_data is not None:
            wav_path = save_audio(audio_data)
            enroll_user(wav_path, user_id)
            os.remove(wav_path)
            st.success(f"✅ Enrolled voice for user: {user_id}")
        else:
            st.warning("⚠️ No audio detected.")


# ------------------ Login & Voice Authentication -------------------
elif page == "Login (Authenticate)":
    st.subheader("🔐 Login: Identify and Authenticate by Voice")
    st.markdown("🎙️ Click **Start** and speak your phrase. We’ll auto-process after 5 seconds.")

    ctx = webrtc_streamer(
        key="voice-auth-login",
        mode=WebRtcMode.SENDRECV,
        audio_receiver_size=1024,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        audio_processor_factory=AudioProcessor,
    )

    if ctx.state.playing:
        st.info("🎧 Recording... please speak now.")
        time.sleep(3)  # Wait while user speaks

        audio_data = ctx.audio_processor.get_audio_data()
        if audio_data is not None:
            wav_path = save_audio(audio_data)
            user_id, score, matched = identify_user(wav_path)
            os.remove(wav_path)

            st.write(f"🧠 Best match: `{user_id or 'None'}` with score `{score:.2f}`")
            if matched:
                st.success(f"✅ Welcome back, {user_id}!")
                st.session_state.authenticated_user = user_id
                st.rerun()  # Trigger dashboard
            else:
                st.error("❌ No matching user found.")
        else:
            st.warning("⚠️ No audio data captured.")


# ------------------ Dashboard -------------------

elif page == "Dashboard":
    user = st.session_state.authenticated_user
    st.title(f"📊 Welcome, {user}")
    st.markdown("Here are your personalized financial insights:")

    # Hardcoded mock data for demo purposes
    user_profiles = {
        "alice": {"savings": 4800, "spending": 1050, "goal": 0.72},
        "bob": {"savings": 2500, "spending": 890, "goal": 0.49},
        "lincoln": {"savings": 3200, "spending": 890, "goal": 0.65}
    }

    profile = user_profiles.get(user.lower(), {"savings": 0, "spending": 0, "goal": 0.0})

    st.metric("💰 Total Savings", f"${profile['savings']:,}")
    st.metric("🛒 Monthly Spending", f"${profile['spending']:,}")
    st.progress(profile["goal"], text=f"{int(profile['goal'] * 100)}% of savings goal reached")

    # Pulse warning
    st.markdown("""
        <div class='pulse'>
            <h4 style='color: red;'>⚡ Budget Alert: You're approaching your spending limit</h4>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📈 Spending Breakdown")
    st.bar_chart({
        "Categories": ["Rent", "Food", "Transport", "Subscriptions", "Other"],
        "Amount": [600, 150, 80, 50, 10]
    })

    st.markdown("### 📉 Savings Over Time")
    st.line_chart([1000, 1800, 2400, profile['savings']])


    # Rotating Insights using st_autorefresh

    st_autorefresh(interval=5000, key="rotate")  # Refresh every 5 sec

    # Cycle through chart types or insight messages
    if "chart_index" not in st.session_state:
        st.session_state.chart_index = 0

    chart_types = ["bar", "line", "area"]
    current = chart_types[st.session_state.chart_index % len(chart_types)]

    st.markdown(f"<div class='fade-in'><h4>Chart Type: {current.capitalize()}</h4></div>", unsafe_allow_html=True)
    data = pd.DataFrame(np.random.randn(20, 3), columns=["A", "B", "C"])

    if current == "Monthly Goals":
        st.bar_chart(data)
    elif current == "Trends":
        st.line_chart(data)
    elif current == "Investments":
        st.area_chart(data)

    st.session_state.chart_index += 1

    if st.button("🚪 Logout"):
        st.session_state.authenticated_user = None
        st.session_state.current_page = "Login (Authenticate)"
        st.rerun()