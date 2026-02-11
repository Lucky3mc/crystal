from flashtext import KeywordProcessor
from sentence_transformers import SentenceTransformer, util

# =========================================================
# Crystal Intent Judge v4.0 (Skill-Level Routing)
# Clean, High-Confidence, Production Version
# =========================================================

MODEL_NAME = "all-MiniLM-L6-v2"

HIGH_CONFIDENCE = 0.70
MEDIUM_CONFIDENCE = 0.50
AMBIGUITY_MARGIN = 0.07

model = SentenceTransformer(MODEL_NAME)

# ---------------------------------------------------------
# SKILL-LEVEL INTENTS (Must match supported_intents)
# ---------------------------------------------------------

INTENTS = {

    # 🧭 App Control / Streaming / Browser
    "app_pilot": [
        "open application",
        "launch app",
        "start program",
        "open website",
        "go to website",
        "watch movie",
        "watch anime",
        "stream show",
        "open youtube",
        "open browser",
        "search online",
        "type text",
        "navigate to site",
        "visit website"
    ],

    # 🎵 Music
    "music_skill": [
        "play music",
        "play song",
        "play audio",
        "pause music",
        "resume music",
        "stop music",
        "skip song",
        "next track",
        "volume up",
        "volume down"
    ],

    # 📷 Camera
    "camera_skill": [
        "open camera",
        "take picture",
        "take photo",
        "capture image",
        "snapshot"
    ],

    # 🌤 Weather
    "weather_sentinel": [
        "weather forecast",
        "current weather",
        "temperature outside",
        "weather today"
    ],

    # ⏰ Time
    "clock": [
        "what time is it",
        "current time",
        "tell me the time"
    ],

    # 📁 File Manager
    "file_commander": [
        "move file",
        "copy file",
        "rename file",
        "delete file",
        "show files",
        "list files",
        "open folder"
    ],

    # 📧 Email
    "email_skill": [
        "check email",
        "open inbox",
        "send email",
        "compose email"
    ],

    # 🌐 Web Research
    "web_researcher": [
        "research topic",
        "summarize article",
        "latest news",
        "find information"
    ],

    # 🔔 Reminders
    "reminder_skill": [
        "set reminder",
        "remind me",
        "create task",
        "todo"
    ],

    # 🏠 Smart Home
    "smart_home": [
        "turn on light",
        "turn off device",
        "activate scene",
        "home automation"
    ],

    # 💻 System Monitor
    "system_sentinel": [
        "system status",
        "battery level",
        "cpu usage",
        "system health"
    ],

    # 📡 WiFi
    "wifi_scanner": [
        "scan wifi",
        "who is on network",
        "network scan"
    ],

    # 🔍 OSINT
    "osint_investigator": [
        "find person",
        "background check",
        "investigate profile",
        "osint search"
    ],

    # 📍 Location
    "location_sentinel": [
        "where am i",
        "current location",
        "my location"
    ],

    # 👋 Greeting
    "greet": [
        "hello",
        "hi crystal",
        "wake up"
    ]
}

# ---------------------------------------------------------
# Imperative verbs (command boost)
# ---------------------------------------------------------

IMPERATIVE_VERBS = [
    "open", "launch", "start", "play",
    "search", "watch", "stream",
    "type", "move", "delete",
    "rename", "copy"
]

# ---------------------------------------------------------
# Precompute embeddings
# ---------------------------------------------------------

INTENT_EMBEDDINGS = {
    intent: model.encode(phrases, convert_to_tensor=True)
    for intent, phrases in INTENTS.items()
}

# ---------------------------------------------------------
# FlashText Gate
# ---------------------------------------------------------

keyword_processor = KeywordProcessor(case_sensitive=False)

for phrases in INTENTS.values():
    for phrase in phrases:
        if len(phrase.split()) == 1:
            keyword_processor.add_keyword(phrase)

for verb in IMPERATIVE_VERBS:
    keyword_processor.add_keyword(verb)

# ---------------------------------------------------------
# Intent Detection
# ---------------------------------------------------------

def detect_intent(text: str):

    text = text.lower().strip()
    if not text:
        return {"action": "none"}

    # -----------------------
    # 1️⃣ Keyword / Verb Gate
    # -----------------------

    keywords = keyword_processor.extract_keywords(text)
    first_word = text.split()[0]

    if not keywords and first_word not in IMPERATIVE_VERBS:
        return {"action": "none"}

    # -----------------------
    # 2️⃣ Embedding Similarity
    # -----------------------

    text_emb = model.encode(text, convert_to_tensor=True)

    scores = []
    for intent, emb in INTENT_EMBEDDINGS.items():
        score = util.cos_sim(text_emb, emb).max().item()
        scores.append((intent, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    top_intent, top_score = scores[0]

    # -----------------------
    # 3️⃣ Ambiguity Check
    # -----------------------

    close_matches = [
        intent for intent, score in scores[1:]
        if abs(top_score - score) <= AMBIGUITY_MARGIN
    ]

    if close_matches and top_score >= MEDIUM_CONFIDENCE:
        return {
            "action": "clarify",
            "intent": top_intent,
            "confidence": round(top_score, 3),
            "candidates": [top_intent] + close_matches
        }

    # -----------------------
    # 4️⃣ Execute
    # -----------------------

    if top_score >= HIGH_CONFIDENCE:
        return {
            "action": "execute",
            "intent": top_intent,
            "confidence": round(top_score, 3)
        }

    # -----------------------
    # 5️⃣ Confirm
    # -----------------------

    if top_score >= MEDIUM_CONFIDENCE:
        return {
            "action": "confirm",
            "intent": top_intent,
            "confidence": round(top_score, 3)
        }

    return {"action": "none"}
