import logging
import json
import os

logger = logging.getLogger("Skill.LearnCommand")

class LearnCommandSkill:
    def __init__(self, memory_path="core/custom_commands.json", skill_manager=None):
        self.memory_path = memory_path
        self.skill_manager = skill_manager
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        logger.info("LearnCommandSkill with Delete capability initialized.")

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r") as f:
                return json.load(f)
        return {}

    def _save_memory(self, data):
        with open(self.memory_path, "w") as f:
            json.dump(data, f, indent=2)

    def run(self, input_text: str, brain=None) -> str:
        input_text = input_text.lower().strip()
        commands = self._load_memory()

        # --- 1. DELETE LOGIC (The "Forget" Command) ---
        if input_text.startswith("forget this:"):
            trigger_to_remove = input_text.replace("forget this:", "").strip()
            
            if trigger_to_remove in commands:
                deleted_val = commands.pop(trigger_to_remove)
                self._save_memory(commands)
                return f"🗑️ Forgotten: I will no longer respond to '{trigger_to_remove}'."
            else:
                return f"❓ I don't have '{trigger_to_remove}' in my memory."

        # --- 2. MASS CLEAR LOGIC ---
        elif input_text == "clear all learned commands":
            self._save_memory({})
            return "🧹 Memory wiped. All custom commands have been deleted."

        # --- 3. LEARN LOGIC (Existing) ---
        elif input_text.startswith("learn this:"):
            try:
                parts = input_text.replace("learn this:", "", 1).split("=>")
                if len(parts) != 2:
                    return "Format: learn this: [trigger] => [response/skill:name]"
                
                trigger, response = parts[0].strip(), parts[1].strip()
                commands[trigger] = response
                self._save_memory(commands)
                return f"✅ Learned: '{trigger}' now maps to '{response}'."
            except Exception as e:
                return f"❌ Failed to learn: {str(e)}"

        # --- 4. LIST LOGIC ---
        elif input_text == "what did you learn":
            if not commands: return "My custom memory is empty."
            output = ["📋 **Learned Commands:**"]
            for k, v in commands.items():
                output.append(f"• {k} → {v}")
            return "\n".join(output)

        return "Commands: 'learn this: x => y', 'forget this: x', or 'what did you learn'."

# Integration entry point
_skill_instance = LearnCommandSkill()
def get_skill_entry_point():
    return _skill_instance.run