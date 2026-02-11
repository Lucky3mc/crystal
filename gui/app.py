import sys
import os
import json
import threading
import time
import pyaudio
import wave
import random
import streamlit as st
from vosk import Model, KaldiRecognizer
import numpy as np
import importlib

# 1️⃣ SETUP SYSTEM PATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2️⃣ CORE IMPORTS
from tts_bridge import speak, stop_speaking
from brain.brain import CrystalBrain
from skill_manager import SkillManager, Skill  # import both the manager and base class

# 3️⃣ CREATE SKILL MANAGER INSTANCE
skill_manager = SkillManager()

# 4️⃣ Automatically import all Python files in the skills folder
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")
for filename in os.listdir(SKILLS_DIR):
    if filename.endswith(".py") and not filename.startswith("__"):
        module_name = f"skills.{filename[:-3]}"
        importlib.import_module(module_name)


# 6️⃣ CREATE BRAIN INSTANCE
brain = CrystalBrain(skill_manager)

# =====================
# CONFIGURATION
# =====================
VOSK_PATH = r"C:\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15"
MEMORY_FILE = "crystal_memory.json"

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Use relative paths for images
IMG_IDLE = os.path.join(SCRIPT_DIR, "download (1).jpg")   # Photo with gold eyes
IMG_THINKING = os.path.join(SCRIPT_DIR, "download (2).jpg") # Photo with blue eyes/vest

AUDIO_CONFIG = {
    "format": pyaudio.paInt16,
    "channels": 1,
    "rate": 16000,
    "chunk_size": 4096,
    "input_device_index": None,
}

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="💎 Crystal AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# CUSTOM CSS
# =====================
st.markdown("""
<style>
/* All your CSS for gradient, glowing title, chat bubbles, avatar, status, thinking animation, buttons */
.stApp {
    background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e, #1a1a2e);
    background-size: 400% 400%;
    animation: gradient 15s ease infinite;
    min-height: 100vh;
}
@keyframes gradient { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

.glowing-title { text-align:center;font-size:3.5rem;font-weight:900;background:linear-gradient(90deg,#ff00cc,#3333ff,#00ccff);background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shine 3s linear infinite;margin-bottom:0.5rem;text-shadow:0 0 10px rgba(255,0,204,0.3);}
@keyframes shine { to { background-position:200% center; } }

.crystal-icon { display:inline-block; animation:pulse 2s infinite; filter: drop-shadow(0 0 8px rgba(0,200,255,0.5)); }
@keyframes pulse { 0% { transform: scale(1); opacity:1; } 50% { transform: scale(1.1); opacity:0.8; } 100% { transform: scale(1); opacity:1; } }

.user-message { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; color: white !important; border-radius: 20px 20px 5px 20px !important; padding: 15px !important; margin: 10px 0 !important; border: 1px solid rgba(255,255,255,0.2); box-shadow:0 5px 15px rgba(0,0,0,0.2); animation: slideInRight 0.3s ease-out;}
.assistant-message { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important; color:#e0e0ff !important; border-radius:20px 20px 20px 5px !important; padding:15px !important; margin:10px 0 !important; border:1px solid rgba(0,200,255,0.3); box-shadow:0 5px 15px rgba(0,200,255,0.1); animation: slideInLeft 0.3s ease-out;}
@keyframes slideInRight { from { transform: translateX(30px); opacity:0; } to { transform: translateX(0); opacity:1; } }
@keyframes slideInLeft { from { transform: translateX(-30px); opacity:0; } to { transform: translateX(0); opacity:1; } }

.avatar-img { width:200px; border-radius:20px; border:2px solid #00ccff; box-shadow:0 0 20px rgba(0,204,255,0.4); transition:all 0.5s ease; margin:0 auto; display:block; }

.status-active { display:inline-block; width:10px; height:10px; background:#00ff88; border-radius:50%; margin-right:8px; animation:blink 1s infinite; box-shadow:0 0 10px #00ff88; }
.status-thinking { display:inline-block; width:10px; height:10px; background:#ff0080; border-radius:50%; margin-right:8px; animation:blink 1s infinite; box-shadow:0 0 10px #ff0080; }
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.5; } }

.thinking-dots { display:inline-flex; gap:5px; }
.thinking-dots span { width:8px; height:8px; background:#00ccff; border-radius:50%; animation:bounce 1.4s infinite ease-in-out both; }
.thinking-dots span:nth-child(1) { animation-delay:-0.32s; }
.thinking-dots span:nth-child(2) { animation-delay:-0.16s; }
.thinking-dots span:nth-child(3) { animation-delay:0s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }

.stButton > button { background: linear-gradient(45deg, #667eea, #764ba2) !important; color:white !important; border:none !important; border-radius:10px !important; padding:10px 20px !important; font-weight:bold !important; transition:all 0.3s ease !important; box-shadow:0 4px 15px rgba(102,126,234,0.4) !important;}
.stButton > button:hover { transform:translateY(-2px) !important; box-shadow:0 8px 25px rgba(102,126,234,0.6) !important; }

.mic-button { background: linear-gradient(45deg,#ff0080,#ff8c00) !important; animation:pulse-glow 2s infinite !important; }
@keyframes pulse-glow { 0% { box-shadow:0 0 10px rgba(255,0,128,0.5);} 50% { box-shadow:0 0 20px rgba(255,0,128,0.8);} 100% { box-shadow:0 0 10px rgba(255,0,128,0.5);} }
</style>
""", unsafe_allow_html=True)

# =====================
# CORE FUNCTIONS
# =====================
@st.cache_resource
def load_crystal_core():
    manager = SkillManager()
    brain = CrystalBrain(manager)
    vosk_model = Model(VOSK_PATH)
    return brain, manager, vosk_model

brain, skill_manager, vosk_model = load_crystal_core()

def emoji_rain(emoji="✨", count=20):
    emoji_html = f"""
    <div id="emoji-container"></div>
    <script>
        const container = document.getElementById('emoji-container');
        for(let i=0;i<{count};i++){{
            setTimeout(()=>{{
                const e = document.createElement('div');
                e.innerHTML='{emoji}';
                e.style.position='fixed';
                e.style.left=Math.random()*100+'vw';
                e.style.top='-5vh';
                e.style.fontSize=(Math.random()*20+20)+'px';
                e.style.zIndex=9999;
                e.animate([{{transform:'translateY(0vh)'}},{{transform:'translateY(110vh)'}}],{{duration:2000,easing:'linear'}});
                document.body.appendChild(e);
                setTimeout(()=>e.remove(),2000);
            }},i*100);
        }}
    </script>
    """
    st.markdown(emoji_html, unsafe_allow_html=True)

# =====================
# VOICE INPUT FUNCTION
# =====================
def listen_voice(timeout=5):
    """
    Records from microphone and returns recognized text using Vosk.
    """
    rec = KaldiRecognizer(vosk_model, AUDIO_CONFIG["rate"])
    audio = pyaudio.PyAudio()
    try:
        stream = audio.open(
            format=AUDIO_CONFIG["format"],
            channels=AUDIO_CONFIG["channels"],
            rate=AUDIO_CONFIG["rate"],
            input=True,
            frames_per_buffer=AUDIO_CONFIG["chunk_size"],
            input_device_index=AUDIO_CONFIG["input_device_index"]
        )
    except Exception as e:
        st.error(f"Microphone error: {e}")
        return ""

    st.info("🎤 Listening... Speak now!")
    stream.start_stream()
    start_time = time.time()
    text = ""

    while True:
        data = stream.read(AUDIO_CONFIG["chunk_size"], exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            break
        if time.time() - start_time > timeout:
            partial = json.loads(rec.PartialResult())
            text = partial.get("partial", "")
            break

    stream.stop_stream()
    stream.close()
    audio.terminate()
    st.success(f"📝 Recognized: {text}")
    return text

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    if "is_thinking" not in st.session_state:
        st.session_state.is_thinking = False

    status_color = "#ff0080" if st.session_state.is_thinking else "#00ff88"
    status_class = "status-thinking" if st.session_state.is_thinking else "status-active"
    status_text = "PROCESSING..." if st.session_state.is_thinking else "SYSTEM ACTIVE"

    st.markdown(f"""
    <div style="text-align:center;padding:10px;background:rgba(0,0,0,0.3);border-radius:10px;margin-bottom:20px;">
        <span class="{status_class}"></span>
        <span style="color:{status_color};font-weight:bold;">{status_text}</span><br>
        <small style="color:#888;">v1.0.0 | Neural Core Online</small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🎭 **Crystal Avatar**")
    avatar_to_show = IMG_THINKING if st.session_state.is_thinking else IMG_IDLE
    avatar_state = "💙 THINKING" if st.session_state.is_thinking else "💛 IDLE"
    st.markdown(f"**Current State:** {avatar_state}")
    st.image(avatar_to_show, width='stretch', caption=f"Crystal - {avatar_state}")

    st.markdown("### 🔮 **Active Skills**")
    if hasattr(skill_manager, 'skills') and skill_manager.skills:
        for s in skill_manager.skills:
            name = getattr(s.get('instance', {}), "name", s.get('name', 'Unknown Skill'))
            st.markdown(f"✅ **{name}**")
    else:
        st.markdown("*No skills loaded*")

# =====================
# CHAT LOGIC
# =====================
if "messages" not in st.session_state:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
        except:
            st.session_state.messages = []
    else:
        st.session_state.messages = []

chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div style="display:flex;justify-content:flex-end;margin:10px 0;"><div class="user-message">{msg["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display:flex;justify-content:flex-start;margin:10px 0;"><div class="assistant-message">{msg["content"]}</div></div>', unsafe_allow_html=True)

# Scroll to bottom
st.markdown("""
<script>
const blocks = window.parent.document.querySelectorAll('[data-testid="stVerticalBlock"]');
const lastBlock = blocks[blocks.length-1];
if(lastBlock){lastBlock.scrollTop = lastBlock.scrollHeight;}
</script>
""", unsafe_allow_html=True)

# =====================
# INTERACTION HANDLING
# =====================
def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, indent=2)
    except Exception as e:
        st.error(f"Error saving memory: {e}")

def handle_interaction(user_text):
    if not user_text.strip(): return
    stop_speaking()
    st.session_state.messages.append({"role":"user","content":user_text})
    st.session_state.is_thinking = True

    thinking_container = st.empty()
    thinking_container.markdown("""
    <div style="text-align:center;padding:20px;">
        <div style="font-size:2rem;margin-bottom:10px;">🔮</div>
        <div style="color:#00ccff;font-weight:bold;margin-bottom:10px;">Crystal is thinking</div>
        <div class="thinking-dots"><span></span><span></span><span></span></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        reply = brain.process(user_text)
        if not reply: reply = "Processing your input..."
    except Exception as e:
        reply = f"Cognitive error: {e}"

    thinking_container.empty()
    st.session_state.is_thinking = False
    st.session_state.messages.append({"role":"assistant","content":reply})
    save_memory()
    speak(reply)
    emoji_rain("💫",15)
    st.rerun()

# =====================
# INPUT CONTROLS
# =====================
control_col1, control_col2, control_col3 = st.columns([3,1,1])
with control_col1:
    if prompt := st.chat_input("💬 Type your message here..."):
        handle_interaction(prompt)

with control_col2:
    if st.button("🎤 Voice Input", type="primary", key="voice_btn"):
        stop_speaking()
        with st.spinner("Preparing microphone..."):
            voice_input = listen_voice()
        if voice_input:
            handle_interaction(voice_input)

with control_col3:
    if st.button("🧹 Clear Chat", key="clear_btn"):
        st.session_state.messages = []
        save_memory()
        st.rerun()
