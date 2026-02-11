import os
import importlib.util
import re
from typing import List, Dict, Optional
from core.base_skill import Skill
import sys, io

# =====================================================
# Ensure UTF-8 stdout/stderr (Windows-safe)
# =====================================================
if not sys.stdout.closed:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if not sys.stderr.closed:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


class SkillManager:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills: List[Dict] = []
        self.load_skills()

    # =====================================================
    # LOAD SKILLS
    # =====================================================
    def load_skills(self):
        self.skills.clear()

        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)
            print(f"📁 Created skills directory: {self.skills_dir}")
            return

        for file in os.listdir(self.skills_dir):
            if not file.endswith(".py") or file == "__init__.py":
                continue

            path = os.path.join(self.skills_dir, file)
            try:
                module_name = file[:-3]
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Skill)
                        and attr is not Skill
                    ):
                        instance = attr()

                        if not hasattr(instance, "supported_intents"):
                            print(
                                f"⚠️ Warning: {attr_name} missing supported_intents, skipping"
                            )
                            continue

                        self.skills.append({
                            "instance": instance,
                            "name": getattr(instance, "name", attr_name),
                            "keywords": getattr(instance, "keywords", []),
                            "supported_intents": instance.supported_intents,
                        })

                        print(
                            f"✅ Loaded skill: {attr_name} → {instance.supported_intents}"
                        )

            except Exception as e:
                print(f"⚠️ Failed loading {file}: {e}")

        # Debug map
        print("\n🧠 Skill → Intent map:")
        for s in self.skills:
            print(
                f"- {s['instance'].__class__.__name__}: {s['supported_intents']}"
            )

    # =====================================================
    # RUN SKILL (INTENT-AWARE)
    # =====================================================
    def run_skill(
        self,
        user_input: str,
        intent_result: Optional[Dict] = None,
        entities: Optional[List[Dict]] = None
    ) -> Optional[str]:

        # =================================================
        # 0️⃣ INTENT RESULT HANDLING (NEW CORE LOGIC)
        # =================================================
        if intent_result:
            action = intent_result.get("action")
            intent = intent_result.get("intent")
            confidence = intent_result.get("confidence", 0.0)
            candidates = intent_result.get("candidates", [])

            # ❌ Explicitly do nothing → LLM fallback
            if action == "none":
                return None

            # 🤔 Ambiguous intent → ask user
            if action == "clarify":
                opts = ", ".join(candidates)
                return f"🤔 I found multiple possible actions: {opts}. Which one should I run?"

            # ❓ Medium confidence → confirmation
            if action == "confirm":
                return f"❓ Do you want me to run '{intent}'? (yes / no)"

            # ✅ EXECUTE → continue below
            if action != "execute":
                return None

            # =================================================
            # 1️⃣ INTENT-BASED EXECUTION (PRIMARY PATH)
            # =================================================
            matches = [
                s["instance"]
                for s in self.skills
                if intent in s["supported_intents"]
            ]

            if not matches:
                return f"⚠️ Intent '{intent}' has no mapped skills."

            for instance in matches:
                can_run, msg = instance.check_requirements()
                if not can_run:
                    continue

                result = instance.run({
                    "user_input": user_input,
                    "intent": intent,
                    "confidence": confidence,
                    "entities": entities
                })

                if result is not None:
                    return result

            return f"⚠️ No skill could execute intent '{intent}'."

        # =================================================
        # 2️⃣ EXACT SKILL NAME (MANUAL / DEBUG)
        # =================================================
        for s in self.skills:
            if user_input.lower() == s["name"].lower():
                inst = s["instance"]
                can_run, msg = inst.check_requirements()
                if can_run:
                    return inst.run({
                        "user_input": user_input,
                        "intent": None,
                        "entities": entities
                    })

        # =================================================
        # 3️⃣ KEYWORD FALLBACK (ONLY IF NO INTENT RESULT)
        # =================================================
        for s in self.skills:
            for kw in s["keywords"]:
                if re.search(rf"\b{re.escape(kw.lower())}\b", user_input.lower()):
                    inst = s["instance"]
                    can_run, msg = inst.check_requirements()
                    if can_run:
                        return inst.run({
                            "user_input": user_input,
                            "intent": None,
                            "entities": entities
                        })

        return None
