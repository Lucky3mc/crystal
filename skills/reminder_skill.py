import json
import os
import time
from datetime import datetime, timedelta
from skill_manager import Skill

class ReminderSkill(Skill):
    name = "Reminder Skill"
    description = "Sets timed reminders and alerts you in the background."
    keywords = ["remind", "reminder", "task", "todo"]
    supported_intents = ["reminder_skill"]
    def __init__(self):
        self.db_file = "tasks.json"
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump([], f)

    def reminder_monitor(self):
        """Called by CrystalBrain's background loop every second."""
        try:
            with open(self.db_file, 'r') as f:
                tasks = json.load(f)

            now = datetime.now()
            updated = False

            for t in tasks:
                task_time = datetime.strptime(t['time'], "%Y-%m-%d %H:%M:%S")
                if now >= task_time and not t['notified']:
                    # 🔥 TRIGGER THE ALERT
                    print(f"\n🔔 [REMINDER]: Lucky, it's time to: {t['task']}!")
                    t['notified'] = True
                    updated = True

            if updated:
                with open(self.db_file, 'w') as f:
                    json.dump(tasks, f, indent=4)
        except Exception as e:
            print(f"⚠️ [REMINDER ERROR]: {e}")

    def run(self, parameters: dict):
        text = parameters.get("user_input", "").lower()
        
        # Simple Logic: "remind me to [task] in [X] minutes"
        if "in" in text and "minute" in text:
            try:
                task_part = text.split("remind me to")[-1].split("in")[0].strip()
                minutes = int([s for s in text.split() if s.isdigit()][0])
                
                remind_time = datetime.now() + timedelta(minutes=minutes)
                time_str = remind_time.strftime("%Y-%m-%d %H:%M:%S")

                with open(self.db_file, 'r') as f:
                    tasks = json.load(f)
                
                tasks.append({"task": task_part, "time": time_str, "notified": False})
                
                with open(self.db_file, 'w') as f:
                    json.dump(tasks, f, indent=4)

                return f"Clock synchronized. I'll remind you to '{task_part}' in {minutes} minutes, Lucky."
            except:
                return "I couldn't parse the time. Try: 'remind me to [task] in [number] minutes'."

        return "I can set reminders. Just say 'remind me to [task] in [x] minutes'."