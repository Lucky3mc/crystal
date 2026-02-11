import sys
import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel

# --- STEP 1: JUMP OUT OF THE BRAIN FOLDER ---
# This tells Python to look one level up (crystal_ai) for SkillManager and other files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR) # Access to crystal_ai root
sys.path.insert(0, CURRENT_DIR) # Access to brain folder contents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Crystal_Web")

# --- STEP 2: IMPORTS ---
try:
    # Since we are inside the brain folder, we import brain.py directly
    from brain import CrystalBrain 
    from skill_manager import SkillManager
    logger.info("✅ CRYSTAL ONLINE: Logic modules linked from inside the brain folder.")
except Exception as e:
    logger.error("❌ BOOT ERROR: Pathing mismatch.")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- STEP 3: INITIALIZATION ---
app = FastAPI(title="Crystal AI Portal")
sm = SkillManager()
crystal = CrystalBrain(sm)

class ChatRequest(BaseModel):
    message: str
    user_id: str = "guest_user"

# --- STEP 4: ENDPOINTS ---
@app.get("/")
def home():
    return {"status": "Crystal is live", "mode": "Internal Gateway"}

@app.post("/ask")
async def ask_crystal(request: ChatRequest):
    logger.info(f"Incoming: {request.message}")
    try:
        response = crystal.process(request.message)
        return {"type": "speech", "text": response}
    except Exception as e:
        return {"type": "error", "text": str(e)}

# --- STEP 5: EXECUTION ---
if __name__ == "__main__":
    import uvicorn
    # Note: We use 'brain.web_gateway:app' if running from the root, 
    # but since you are running the file directly:
    uvicorn.run(app, host="0.0.0.0", port=8000)