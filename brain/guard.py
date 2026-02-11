# guard.py
import re
from enum import Enum

class Intent(Enum):
    GREETING = "greeting"
    INSTRUCTION = "instruction"
    SYSTEM = "system"
    GENERAL = "general"

class Judgment(Enum):
    PASS = "pass"
    FAIL = "fail"
RULES = [
    "Do not roleplay unless explicitly asked",
    "Do not describe actions or emotions",
    "Respond as an AI assistant only",
    "Never simulate pauses, thoughts, or narration"
]

SYSTEM_RULES = {
    "persona": "Crystal",
    "priority": "instructions_over_content",
    "max_words": None,
    "tone": "controlled",
}

def classify_intent(text: str) -> Intent:
    text_l = text.lower().strip()
    if re.match(r"^(hi|hello|hey|yo)\b", text_l):
        return Intent.GREETING
    if any(k in text_l for k in ["respond with", "answer with", "only", "exactly"]):
        return Intent.INSTRUCTION
    if text_l.startswith("/"):
        return Intent.SYSTEM
    return Intent.GENERAL

def extract_instruction(text: str):
    match = re.search(r"respond with (\d+) words?", text.lower())
    if match:
        return {"max_words": int(match.group(1))}
    return {}

def strip_story(text: str) -> str:
    lines = text.split("\n")
    for line in lines:
        if "respond with" in line.lower() or "only" in line.lower():
            return line
    return text

def build_prompt(user_input: str) -> dict:
    intent = classify_intent(user_input)
    enforced_rules = SYSTEM_RULES.copy()
    if intent == Intent.INSTRUCTION:
        enforced_rules.update(extract_instruction(user_input))
        user_input = strip_story(user_input)

    system_prompt = f"""
You are Crystal.
Persona is immutable.
Instructions have absolute priority over content.
Tone: {enforced_rules['tone']}
Response must obey enforced limits.
"""
    return {
        "intent": intent,
        "rules": enforced_rules,
        "system_prompt": system_prompt.strip(),
        "user_input": user_input.strip(),
    }

def word_count(text: str) -> int:
    return len(text.strip().split())

def violates_length(text: str, rules: dict) -> bool:
    if rules.get("max_words") is None:
        return False
    return word_count(text) != rules["max_words"]

def violates_persona(text: str) -> bool:
    banned = ["as an ai", "i cannot", "i'm just"]
    return any(b in text.lower() for b in banned)

def judge(output: str, rules: dict) -> Judgment:
    if violates_length(output, rules):
        return Judgment.FAIL
    if violates_persona(output):
        return Judgment.FAIL
    return Judgment.PASS

def enforce(output: str, rules: dict) -> str:
    if rules.get("max_words"):
        words = output.strip().split()
        return " ".join(words[:rules["max_words"]])
    return output
def enforce(text: str, rules):
    forbidden = ["*", "...", "pauses", "watching", "smiles"]
    for f in forbidden:
        text = text.replace(f, "")
    return text.strip()
