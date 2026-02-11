import pyttsx3
import threading

# Global reference to allow interruption
_current_engine = None
_engine_lock = threading.Lock()

def stop_speaking():
    """Immediately terminates any current speech."""
    global _current_engine
    if _current_engine:
        try:
            _current_engine.stop()
        except Exception as e:
            print(f"Stop Error: {e}")

def speak(text: str, emotion: str = None):
    """
    Threaded TTS that can be interrupted via stop_speaking().
    """
    def run():
        global _current_engine
        try:
            with _engine_lock:
                engine = pyttsx3.init()
                _current_engine = engine 
                
                # Voice setup
                voices = engine.getProperty("voices")
                for v in voices:
                    name = v.name.lower()
                    if "zira" in name or "female" in name or "woman" in name:
                        engine.setProperty("voice", v.id)
                        break

                # Emotion-based rate
                rate = 165
                if emotion == "happy": rate = 180
                elif emotion == "sad": rate = 140
                
                engine.setProperty("rate", rate)
                engine.setProperty("volume", 0.9)

                engine.say(text)
                engine.runAndWait()
                _current_engine = None # Reset after finishing
        except Exception as e:
            print("TTS Error:", e)
            _current_engine = None

    threading.Thread(target=run, daemon=True).start()