import requests
from skill_manager import Skill

class LocationSkill(Skill):
    name = "Location Sentinel"
    description = "Automatically detects the device's physical location."
    keywords = ["where am i", "current location", "update location"]
    supported_intents = ["location_skill"]
    
    def __init__(self):
        self.city = "Unknown"
        self.lat = 0.0
        self.lon = 0.0
        self.update_location() # Get location as soon as Crystal wakes up

    def update_location(self):
        """Pings free APIs to find the device's current city and coordinates."""
        try:
            # 1. Get Public IP
            ip_res = requests.get('https://api.ipify.org?format=json', timeout=5).json()
            ip = ip_res['ip']

            # 2. Get Geolocation from IP
            geo_res = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5).json()
            
            self.city = geo_res.get("city", "Unknown")
            self.lat = geo_res.get("latitude", 0.0)
            self.lon = geo_res.get("longitude", 0.0)
            
            print(f"📍 [LOCATION]: Home base established in {self.city} ({self.lat}, {self.lon})")
        except Exception as e:
            print(f"⚠️ [LOCATION ERROR]: Could not detect coordinates: {e}")

    def run(self, parameters: dict):
        self.update_location()
        return f"System check complete, Lucky. We are currently operating from {self.city}."