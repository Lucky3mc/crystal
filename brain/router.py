from typing import Dict, Any
from .intent_judge import classify_intent, IntentType

def route(user_input: str, skill_manager, memory) -> Dict[str, Any]:
    intent = classify_intent(user_input)

    # 🔒 ABSOLUTE RULE
    if intent != IntentType.COMMAND:
        return {"route": "conversation", "data": None}

    # Only now may skills be considered
    skill_name = skill_manager.match_skill(user_input)

    if skill_name:
        return {"route": "skill", "data": skill_name}

    return {"route": "conversation", "data": None}
