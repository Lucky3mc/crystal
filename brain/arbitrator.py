# arbitrator.py
from typing import Optional
from brain.llm import run_llm

class SkillArbitrator:
    """
    Resolves multiple potential skill matches for a given user input.
    Uses LLM classification and optional user confirmation.
    """
    def __init__(self, skill_manager, skill_bridge=None):
        self.skill_manager = skill_manager
        self.skill_bridge = skill_bridge

    def select_skill(self, user_input: str) -> Optional[str]:
        """
        Returns either the skill output or None if no match is found.
        Handles:
        1. Single match → execute directly
        2. Multiple matches → classify & ask for user confirmation
        3. No match → return None
        """
        # 1️⃣ Use SkillBridge if available to find best candidate
        best_skill_name = None
        if self.skill_bridge:
            best_skill_name = self.skill_bridge._find_skill_by_keywords(user_input)

        # 2️⃣ Use SkillManager keyword matching for potential candidates
        candidates = []
        clean_input = user_input.lower().strip("?!. ")
        for skill in self.skill_manager.skills:
            if any(word.lower() in clean_input for word in skill["keywords"]):
                candidates.append(skill)

        if not candidates:
            return None  # No skill found

        # 3️⃣ Single candidate → execute directly
        if len(candidates) == 1:
            instance = candidates[0]["instance"]
            output = instance.run({"user_input": user_input})
            return output

        # 4️⃣ Multiple candidates → classify with LLM
        skill_descriptions = "\n".join(
            [f"- {s['name']}: {s['description']}" for s in candidates]
        )
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a tool arbitrator. The user input may match multiple skills. "
                    "Return ONLY the exact skill name that best fits the user's intent."
                ),
            },
            {
                "role": "user",
                "content": f"User input: {user_input}\nAvailable skills:\n{skill_descriptions}"
            }
        ]
        try:
            decision = run_llm(prompt, task_type="skill_routing").strip()
        except Exception as e:
            print(f"❌ [ARBITRATOR]: LLM classification failed: {e}")
            decision = ""

        # 5️⃣ Match LLM decision to candidate
        selected_skill = None
        for s in candidates:
            if s["name"].lower() in decision.lower():
                selected_skill = s
                break

        # 6️⃣ If LLM fails, ask user to classify (fallback)
        if not selected_skill:
            print("⚖️ [ARBITRATOR]: Multiple skills matched. Please classify:")
            for i, s in enumerate(candidates):
                print(f"{i+1}: {s['name']} - {s['description']}")
            choice = input("Enter the number of the desired skill: ").strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(candidates):
                    selected_skill = candidates[choice_idx]
            except Exception:
                print("❌ Invalid choice. No skill executed.")
                return None

        # 7️⃣ Execute the selected skill
        if selected_skill:
            instance = selected_skill["instance"]
            try:
                return instance.run({"user_input": user_input})
            except Exception as e:
                print(f"❌ [ARBITRATOR]: Skill execution failed: {e}")
                return None

        return None
