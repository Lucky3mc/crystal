import cv2
import time
import os
from skill_manager import Skill

class CameraSkill(Skill):
    name = "CameraSkill"
    keywords = ["camera", "take a picture", "take pictures", "snapshot", "capture"]
    supported_intents = ["camera"]
    def __init__(self):
        self.save_path = "captures/photos"
        os.makedirs(self.save_path, exist_ok=True)

    def take_photos(self, count=1, delay=1):
        """Connects to the webcam and takes a specific number of photos."""
        # 0 is usually the default built-in camera
        cam = cv2.VideoCapture(0)
        
        if not cam.is_isOpened():
            return "I can't access your camera. Is it plugged in or being used by another app?"

        results = []
        try:
            for i in range(count):
                # 'Warm up' the camera sensor (prevents dark first frames)
                for _ in range(5):
                    cam.read()
                
                ret, frame = cam.read()
                if ret:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"{self.save_path}/photo_{timestamp}_{i+1}.jpg"
                    cv2.imwrite(filename, frame)
                    results.append(filename)
                    time.sleep(delay) # Wait between shots
            
            return f"Done! I've taken {len(results)} pictures and saved them to your captures folder."
        
        finally:
            cam.release() # CRITICAL: Always release the camera so other apps can use it

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").lower()
        
        # Simple extraction logic (could be upgraded with LLM)
        if "3" in user_input or "three" in user_input:
            num = 3
        else:
            num = 1
            
        return self.take_photos(count=num)