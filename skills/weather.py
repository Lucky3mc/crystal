import os
import requests
import time
from dotenv import load_dotenv
from skill_manager import Skill

# 🔐 Load the secret vault
load_dotenv()

class WeatherSentinel(Skill):
    name = "Weather Sentinel"
    description = "Monitors local weather based on device location."
    keywords = ["weather", "forecast", "where am i", "sky check"]
    supported_intents = ["weather"]
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_KEY")
        self.city = "Detecting..."
        self.lat = None
        self.lon = None
        self.last_check_time = 0
        self.check_interval = 1800  # 30 minutes
        self.last_condition = None

        if not self.api_key:
            print("⚠️ [WEATHER]: No API key found in .env!")
        
        # 📍 Initial Location Sync
        self._update_location()

    def _update_location(self):
        """Finds where the device is currently hosted."""
        try:
            # Using ipapi for a quick, keyless location grab
            geo_res = requests.get('https://ipapi.co/json/', timeout=5).json()
            self.city = geo_res.get("city", "Nairobi") # Fallback to Nairobi if fails
            self.lat = geo_res.get("latitude")
            self.lon = geo_res.get("longitude")
            print(f"📍 [LOCATION]: Crystal has localized to {self.city}.")
        except:
            print("⚠️ [LOCATION]: Could not detect movement, staying at last known city.")

    def weather_monitor(self):
        """Background loop called by CrystalBrain."""
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return

        try:
            # Use Lat/Lon if available for pinpoint accuracy, else use City name
            if self.lat and self.lon:
                url = f"http://api.openweathermap.org/data/2.5/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
            else:
                url = f"http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&units=metric"
            
            response = requests.get(url, timeout=10)
            data = response.json()

            if response.status_code == 200:
                condition = data['weather'][0]['main']
                temp = data['main']['temp']

                if self.last_condition and condition != self.last_condition:
                    if condition in ["Rain", "Thunderstorm", "Snow"]:
                        print(f"\n⛈️ [WEATHER ALERT]: Sky change in {self.city}: {condition}. Temp: {temp}°C.")
                
                self.last_condition = condition
                self.last_check_time = current_time
                print(f"🌤️ [SENTINEL]: Localized check complete for {self.city}.")
        except Exception as e:
            print(f"⚠️ [WEATHER ERROR]: {e}")

    def run(self, parameters: dict):
        """Manual check logic."""
        text = parameters.get("user_input", "").lower()
        
        if "where" in text or "location" in text:
            self._update_location()
            return f"My sensors indicate we are currently in {self.city}, Lucky."

        if not self.last_condition:
            return f"I'm still calibrating for {self.city}. Try again in a moment."
            
        return f"Current status in {self.city}: {self.last_condition}. My sentinel is watching for changes."