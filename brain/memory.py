import json
import os
import time
from typing import List, Dict, Optional

class Memory:
    """
    Memory for Crystal AI.
    Stores recent conversation and entities.
    """

    def __init__(self, file="crystal_memory.json", max_turns=20):
        self.file = file
        self.history: List[Dict] = []
        self.max_turns = max_turns
        self.system_prompt = {
            "role": "system",
            "content": "You are Crystal, Lucky's personal AI. Be concise, technical, and intelligent."
        }
        self.load()

    def add(self, role: str, text: str, meta: Optional[Dict] = None):
        if meta is None:
            meta = {}
        self.history.append({
            "role": role,
            "content": text,
            "timestamp": time.time(),
            "entities": meta.get("entities", [])
        })
        self.history = self.history[-self.max_turns:]
        self.save()

    def save(self):
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Memory Save Error: {e}")

    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"❌ Memory Load Error: {e}")
                self.history = []

    def context(self, last_n: int = 6):
        msgs = self.history[-last_n:] if last_n >= 0 else self.history[last_n:]
        return [self.system_prompt] + msgs

    def query(self, text: str) -> str:
        return f"[Memory Query] I don't have a detailed answer for: {text}"

    def get_recent_entities(self, entity_type: Optional[str] = None, limit: int = 10) -> List[str]:
        entities = []
        for entry in reversed(self.history):
            for e in entry.get("entities", []):
                if entity_type is None or e.get("type") == entity_type:
                    if e["value"] not in entities:
                        entities.append(e["value"])
            if len(entities) >= limit:
                break
        return entities[:limit]

    def query_entities(self, query_text: str) -> str:
        """
        Responds to "who did I ask about?" or "what have I asked about?"
        """
        lower = query_text.lower()
        if "who did i ask" in lower or "what did i ask" in lower:
            recent = self.get_recent_entities()
            if recent:
                return "You recently asked about: " + ", ".join(recent)
            else:
                return "You haven't asked me about anyone or anything recently."
        return ""  # Not an entity query
