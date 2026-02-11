import datetime
import requests
import pytz
from timezonefinder import TimezoneFinder
from skill_manager import Skill

class TimeSkill(Skill):
    name = "Clock"
    description = "Automatically detects local time via IP and handles global queries."
    keywords = ["time", "clock", "hour", "timezone"]
    supported_intents = ["time_skill"]
    def __init__(self):
        self.tf = TimezoneFinder()
        self.local_tz_name = self._detect_local_timezone()

    def _detect_local_timezone(self):
        """Uses IP to find coordinates, then finds the timezone name."""
        try:
            # Re-using the logic from your Weather Sentinel
            res = requests.get('https://ipapi.co/json/', timeout=5).json()
            lat, lon = res.get("latitude"), res.get("longitude")
            
            if lat and lon:
                return self.tf.timezone_at(lng=lon, lat=lat)
        except:
            pass
        return "Africa/Nairobi"  # Smart default

    def run(self, parameters: dict):
        text = parameters.get("user_input", "").lower()
        
        # 🌐 Global Query Logic
        if "in" in text:
            target = text.split("in")[-1].strip().replace("?", "").title()
            # Scan pytz for a matching city
            for zone in pytz.all_timezones:
                if target.replace(" ", "_") in zone:
                    tz = pytz.timezone(zone)
                    now = datetime.datetime.now(tz).strftime("%I:%M %p")
                    return f"In {target}, it is currently {now}."

        # 🏠 Local Awareness Logic
        tz = pytz.timezone(self.local_tz_name)
        now = datetime.datetime.now(tz).strftime("%I:%M %p")
        return f"It's {now} here in our current location."