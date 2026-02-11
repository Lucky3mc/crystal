import threading
import time
import psutil
import re
from typing import Any, Dict, List

from .memory import Memory
from .guard import build_prompt, judge, enforce, Judgment
from .llm import generate_response
from .intent_judge import detect_intent
from skill_manager import SkillManager


class CrystalBrain:
    """
    CrystalBrain: Hardened Cognitive Core

    Architecture:
    - Intent Judge decides WHICH skill
    - Skill decides WHAT action
    - LLM is fallback only
    """

    # ==================================================
    # INIT
    # ==================================================

    def __init__(
        self,
        skill_manager: SkillManager,
        awareness: dict = None,
        temp_conversation: float = 0.2,
        temp_skill: float = 0.1,
    ):
        self.memory = Memory()
        self.skill_manager = skill_manager
        self.commands_path = "core/custom_commands.json"
        self.awareness = awareness or {}
        self.temp_conversation = temp_conversation
        self.temp_skill = temp_skill

        # Build intent → skill mapping
        self.intent_skill_map = self._build_intent_skill_map()
        print(f"🌌 [SYSTEM]: Intent-Skill mapping loaded: {self.intent_skill_map}")

        # Background monitor
        self.monitor_active = True
        self.monitor_thread = threading.Thread(
            target=self._background_monitor,
            daemon=True
        )
        self.monitor_thread.start()

        print("🌌 [SYSTEM]: Crystal Brain initialized (NLU v4.0).")

    # ==================================================
    # TRACING
    # ==================================================

    def _trace(self, direction: str, branch: str, payload: Any):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [BRAIN:{branch}] {direction} -> {payload}", flush=True)

    # ==================================================
    # BACKGROUND MONITOR
    # ==================================================

    def _background_monitor(self):
        while self.monitor_active:
            try:
                if psutil.cpu_percent() > 90:
                    time.sleep(10)
                    continue

                for skill_info in self.skill_manager.skills:
                    instance = skill_info.get("instance")
                    if not instance:
                        continue

                    for hook in (
                        "check_queue_loop",
                        "price_monitor",
                        "weather_monitor",
                        "reminder_monitor",
                    ):
                        fn = getattr(instance, hook, None)
                        if callable(fn):
                            fn()

                time.sleep(5)

            except Exception as e:
                print(f"⚠️ [MONITOR ERROR]: {e}")
                time.sleep(10)

    # ==================================================
    # CUSTOM COMMANDS
    # ==================================================

    def _check_custom_commands(self, text: str):
        import os, json

        if not os.path.exists(self.commands_path):
            return None

        try:
            with open(self.commands_path, "r", encoding="utf-8") as f:
                commands = json.load(f)

            trigger = text.lower().strip()
            if trigger not in commands:
                return None

            mapped = commands[trigger]

            if isinstance(mapped, str) and mapped.startswith("skill:"):
                return self.skill_manager.run_skill(trigger)

            return mapped

        except Exception as e:
            print(f"⚠️ [COMMAND ERROR]: {e}")
            return None

    # ==================================================
    # MAIN PIPELINE
    # ==================================================

    def process(self, user_text: str) -> str:

        self._trace("RECV", "GUI", user_text)

        # 1️⃣ Entity extraction
        entities = self._extract_entities(user_text)
        self.memory.add("user", user_text, meta={"entities": entities})

        # 2️⃣ Memory recall
        recall = self.memory.query_entities(user_text)
        if recall:
            self._trace("RECV", "MEMORY", recall)
            self.memory.add("assistant", recall)
            return recall

        # 3️⃣ Guard
        gate = build_prompt(user_text)
        system_prompt = gate["system_prompt"]

        if self.awareness:
            system_prompt += "\n" + "\n".join(
                f"[Aware of {k}: {v}]" for k, v in self.awareness.items()
            )

        # 4️⃣ Custom commands
        custom = self._check_custom_commands(user_text)
        if custom:
            self._trace("RECV", "CUSTOM_CMD", custom)
            self.memory.add("assistant", custom)
            return custom

        # ==================================================
        # 5️⃣ INTENT DETECTION
        # ==================================================

        self._trace("SEND", "INTENT_JUDGE", user_text)
        intent_result = detect_intent(user_text)
        self._trace("RECV", "INTENT_JUDGE", intent_result)

        action = intent_result.get("action")
        intent_name = intent_result.get("intent")

        # --------------------------------------------------
        # Clarify
        # --------------------------------------------------

        if action == "clarify":
            candidates = intent_result.get("candidates", [])
            options = ", ".join(candidates)
            reply = f"I detected multiple possible commands: {options}. Which one should I run?"
            self.memory.add("assistant", reply)
            return reply

        # --------------------------------------------------
        # Confirm
        # --------------------------------------------------

        if action == "confirm":
            reply = f"Did you want me to run the '{intent_name.replace('_', ' ')}' command?"
            self.memory.add("assistant", reply)
            return reply

        # --------------------------------------------------
        # Execute
        # --------------------------------------------------

        if action == "execute" and intent_name:

            skill_name = self._map_intent_to_skill(intent_name)
            self._trace("INFO", "ROUTER", f"{intent_name} → {skill_name}")

            if skill_name:
                self._trace("SEND", "SKILL", skill_name)

                output = self.skill_manager.run_skill(
                    user_input=user_text,
                    intent_result=intent_result,
                    entities=entities
                )

                self._trace("RECV", "SKILL", output)

                if output:
                    final = output
                else:
                    final = "Command executed."

            else:
                final = "Intent recognized but no skill is mapped."

        else:
            # --------------------------------------------------
            # LLM FALLBACK
            # --------------------------------------------------

            context = self.memory.context(last_n=6)

            self._trace("SEND", "LLM", user_text)

            final = generate_response(
                system_prompt=system_prompt,
                messages=context,
                temperature=self.temp_conversation,
            )

            self._trace("RECV", "LLM", final)

        # ==================================================
        # GUARD ENFORCEMENT
        # ==================================================

        if judge(final, gate["rules"]) == Judgment.FAIL:
            final = enforce(final, gate["rules"])

        # ==================================================
        # MEMORY WRITE
        # ==================================================

        if final and len(final) < 500:
            self.memory.add("assistant", final)

        return final

    # ==================================================
    # INTENT → SKILL MAP
    # ==================================================

    def _build_intent_skill_map(self) -> Dict[str, str]:
        mapping = {}

        for skill_info in self.skill_manager.skills:
            instance = skill_info.get("instance")
            if not instance:
                continue

            intents = getattr(instance, "supported_intents", [])

            for intent in intents:
                mapping[intent.lower()] = skill_info.get("name")

        return mapping

    def _map_intent_to_skill(self, intent_name: str):
        return self.intent_skill_map.get(intent_name.lower())

    # ==================================================
    # LIGHTWEIGHT ENTITY EXTRACTION
    # ==================================================

    def _extract_entities(self, text: str) -> List[Dict]:
        entities: List[Dict] = []

        for u in re.findall(r"(https?://[^\s]+)", text):
            entities.append({"type": "url", "value": u})

        for m in re.findall(
            r"(youtube|spotify|netflix|9anime|juice\s*wrld)",
            text,
            re.IGNORECASE,
        ):
            entities.append({"type": "media", "value": m})

        for w in text.split():
            if w[:1].isupper() and len(w) > 2:
                entities.append({"type": "thing", "value": w})

        return entities
