# ===============================
# llm.py
# Crystal Language Model Interface
# (Response generation ONLY)
# ===============================

import requests
import datetime
import psutil
from dotenv import load_dotenv

load_dotenv()

# ==========================
# CONFIGURATION
# ==========================
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "crystal"

SYSTEM_CLEAN = {
    "role": "system",
    "content": (
        "You are Crystal, a voice assistant. "
        "Respond clearly, concisely, and professionally. "
        "Answer the user's request directly. "
        "Do not narrate your reasoning. "
        "Do not role-play. "
        "Do not add commentary or personality unless explicitly asked. "
        "Do not include labels, headings, logs, or metadata."
    )
}


def get_dynamic_context():
    now = datetime.datetime.now().strftime("%I:%M %p, %A, %B %d, %Y")

    battery = psutil.sensors_battery()
    bat = f"{battery.percent}%" if battery else "Unknown"
    charging = "charging" if battery and battery.power_plugged else "not charging"

    city = "Nairobi, Kenya"

    return f"Current time: {now}. User location: {city}. Device battery: {bat}, {charging}. Use this silently for context only."


def generate_response(system_prompt: str, messages: list, temperature: float = 0.3) -> str:
    """
    Generates a conversational response.
    """
    context_message = {"role": "system", "content": get_dynamic_context()}

    full_messages = [
        SYSTEM_CLEAN,
        {"role": "system", "content": system_prompt},
        context_message
    ]

    for m in messages:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            full_messages.append(m)

    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 1.0,
            "num_predict": 512
        }
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"LLM core error: {str(e)}"


# ─────────────────────────────────────────────
# BACKWARD-COMPATIBILITY FUNCTION
# ─────────────────────────────────────────────
def run_llm(messages, task_type="conversation") -> str:
    """
    Legacy compatibility wrapper for SkillManager and older imports.
    Delegates to generate_response().
    """
    # If messages is a list of dicts (user/assistant), pass as-is
    # Otherwise, wrap string input
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    system_prompt = ""  # legacy, empty system prompt
    return generate_response(system_prompt, messages)
