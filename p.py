import json
import os

SKILLS_JSON = "skills_metadata.json"
OUTPUT_NLU = "nlu.yml"
OUTPUT_ACTIONS = "actions.py"

INTENT_PREFIX = "skill_"

def generate_nlu_and_actions():
    if not os.path.exists(SKILLS_JSON):
        print(f"❌ {SKILLS_JSON} not found. Run the skill extractor first.")
        return

    with open(SKILLS_JSON, "r", encoding="utf-8") as f:
        skills = json.load(f)

    # ─── Generate nlu.yml ───
    nlu_lines = ["version: '3.0'", "nlu:"]
    for skill in skills:
        intent_name = INTENT_PREFIX + skill["name"].lower()
        nlu_lines.append(f"- intent: {intent_name}")
        nlu_lines.append("  examples: |")
        for kw in skill.get("keywords", []):
            nlu_lines.append(f"    - {kw}")
            nlu_lines.append(f"    - please {kw}")
            nlu_lines.append(f"    - could you {kw}")
        nlu_lines.append("")

    with open(OUTPUT_NLU, "w", encoding="utf-8") as f:
        f.write("\n".join(nlu_lines))
    print(f"✅ Generated NLU: {OUTPUT_NLU}")

    # ─── Generate actions.py ───
    action_lines = [
        "from typing import Any, Text, Dict, List",
        "from rasa_sdk import Action, Tracker",
        "from rasa_sdk.executor import CollectingDispatcher",
        "",
        "# Auto-generated action skeletons from skills"
    ]

    for skill in skills:
        class_name = f"Action{skill['name']}"
        intent_name = INTENT_PREFIX + skill["name"].lower()
        action_lines.append(f"\nclass {class_name}(Action):")
        action_lines.append(f"    def name(self) -> Text:")
        action_lines.append(f"        return '{intent_name}'\n")
        action_lines.append(f"    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:")
        action_lines.append(f"        # TODO: call your skill.run() here")
        action_lines.append(f"        dispatcher.utter_message(text='[Executed {skill['name']}]')")
        action_lines.append(f"        return []")

    with open(OUTPUT_ACTIONS, "w", encoding="utf-8") as f:
        f.write("\n".join(action_lines))
    print(f"✅ Generated Actions: {OUTPUT_ACTIONS}")

if __name__ == "__main__":
    generate_nlu_and_actions()
