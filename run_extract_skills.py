import os
import importlib.util
import inspect
import json
from skill_manager import Skill  # base Skill class

SKILLS_FOLDER = "skills"
OUTPUT_JSON = "skills_metadata.json"

skills_metadata = []

for filename in os.listdir(SKILLS_FOLDER):
    if filename.endswith(".py") and not filename.startswith("__"):
        path = os.path.join(SKILLS_FOLDER, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Skill) and obj is not Skill:
                instance = obj()
                skills_metadata.append({
                    "name": getattr(obj, "name", obj.__name__),
                    "description": getattr(obj, "description", ""),
                    "keywords": getattr(obj, "keywords", [])
                })

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(skills_metadata, f, indent=4)

print(f"✅ Generated {OUTPUT_JSON} with {len(skills_metadata)} skills")
