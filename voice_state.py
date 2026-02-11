# voice_state.py

import json
import os

class VoiceState:
    def __init__(self, path="voice_state.json"):
        self.path = path
        self.emotion = "neutral"
        self.intimacy = 0.3
        self.trust = 0.5
        self.personality = "gentle"
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.__dict__.update(json.load(f))

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.__dict__, f, indent=2)
