import datetime
import pytz
from skill_manager import Skill

class GreetingSkill(Skill):
    name = "Greeter"
    description = "Welcomes the user based on the time of day."
    keywords = ["hello", "hi", "wake up"]
    supported_intents = ["greeting_skill"]
    
    def get_wish(self, timezone_name="Africa/Nairobi"):
        """Calculates the perfect greeting for the current hour."""
        tz = pytz.timezone(timezone_name)
        hour = datetime.datetime.now(tz).hour

        if 5 <= hour < 12:
            return "Good morning, Lucky! The system is green and ready."
        elif 12 <= hour < 18:
            return "Good afternoon! Core systems are stable."
        elif 18 <= hour < 22:
            return "Good evening, Lucky. Anything on the agenda for tonight?"
        else:
            return "Midnight shift, I see? I'm standing by."

    def run(self, parameters: dict):
        # This allows you to trigger a greeting manually by saying 'Hi'
        return self.get_wish()