from skill_manager import Skill
import psutil # You may need to: pip install psutil

class SystemSentinel(Skill):
    name = "System Sentinel"
    description = "Checks hardware health and self-awareness"
    keywords = ["status", "how are you", "system", "health", "battery"]
    supported_intents = ["system_sentinel"]
    def run(self, parameters: dict):
        # 1. Gather Hardware Data
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        batt_percent = battery.percent if battery else "Unknown"
        
        # 2. Self-Aware Logic (The "Mood" of Crystal)
        if cpu_usage > 80 or ram_usage > 90:
            status = f"I'm feeling very overwhelmed, Lucky. My CPU is at {cpu_usage}% and I'm struggling to think clearly."
        elif battery and battery.percent < 20 and not battery.power_plugged:
            status = f"I'm feeling a bit faint... my battery is down to {batt_percent}%. We should find a charger soon."
        else:
            status = f"I'm feeling great! Everything is running smoothly. CPU is at {cpu_usage}% and RAM is at {ram_usage}%."

        return status