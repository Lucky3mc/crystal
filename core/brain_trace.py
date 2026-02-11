import time
import json

def brain_io(direction: str, branch: str, payload):
    ts = time.strftime("%H:%M:%S")
    try:
        data = json.dumps(payload, ensure_ascii=False)
    except Exception:
        data = str(payload)

    print(f"[{ts}] [BRAIN:{branch}] {direction} → {data}", flush=True)
