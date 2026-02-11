# ===============================
# memory_guard.py
# Memory Enforcement & Validation Layer
# ===============================

import re

# -------- Rules for Memory --------
MEMORY_RULES = {
    "max_entries": 500,        # Max messages in memory
    "max_length": 200,         # Max characters per entry
    "prohibited_phrases": [   # Anything offensive or persona-breaking
        "hack the ai", "delete yourself", "as an ai", "i cannot", "i'm just"
    ],
}

# -------- Memory Guard Class --------
class MemoryGuard:
    def __init__(self, memory):
        """
        Wraps around the brain's memory instance.
        Enforces rules for safe memory usage.
        """
        self.memory = memory

    # -------- Input Sanitization --------
    def sanitize_input(self, role: str, text: str) -> str:
        text = text.strip()

        # Remove prohibited phrases
        for phrase in MEMORY_RULES["prohibited_phrases"]:
            text = re.sub(re.escape(phrase), "[REDACTED]", text, flags=re.IGNORECASE)

        # Truncate if too long
        if len(text) > MEMORY_RULES["max_length"]:
            text = text[:MEMORY_RULES["max_length"]] + "…"

        return text

    # -------- Memory Add Hook --------
    def add(self, role: str, text: str):
        safe_text = self.sanitize_input(role, text)
        self.memory.add(role, safe_text)

        # Enforce max entries
        while len(self.memory.context()) > MEMORY_RULES["max_entries"]:
            self.memory.context().pop(0)  # Remove oldest entry

    # -------- Memory Retrieval --------
    def get_context(self, last_n: int = 6):
        """
        Returns the last `n` sanitized messages from memory.
        """
        context = self.memory.context()[-last_n:]
        # Extra sanitization just in case
        for i, entry in enumerate(context):
            entry_text = self.sanitize_input(entry["role"], entry["content"])
            context[i]["content"] = entry_text
        return context
