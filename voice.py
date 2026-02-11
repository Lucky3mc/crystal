# voice.py

from voice_state import VoiceState
from voice_ssml import build_ssml
from tts_bridge import speak
import threading
import hashlib

voice_state = VoiceState()
_speech_lock = threading.Lock()
_last_hash = None


def handle_voice(text):
    global _last_hash

    # Create a stable fingerprint of the response
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    with _speech_lock:
        # HARD STOP: never speak the same response twice
        if _last_hash == text_hash:
            return
        _last_hash = text_hash

    ssml = build_ssml(text, voice_state)
    speak(ssml)
    voice_state.save()
