import re
from typing import Dict, List, Optional

class SkillBridge:
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.skill_keywords = {}  # skill_name -> list of keywords
        self._load_skill_keywords()
    
    def _load_skill_keywords(self):
        """Extracts and caches keywords from all loaded skills in the manager."""
        skills_ref = self.skill_manager.skills
        
        # SkillManager.skills is a list of dicts based on our root manager
        for skill_data in skills_ref:
            instance = skill_data.get("instance")
            skill_name = skill_data.get("name")
            
            if not instance or not skill_name:
                continue
            
            keywords = getattr(instance, 'keywords', [])
            if keywords:
                self.skill_keywords[skill_name] = [k.lower() for k in keywords]
                print(f"🔧 [SKILL BRIDGE]: Indexed {len(keywords)} keywords for '{skill_name}'")
    
    def _find_skill_by_keywords(self, user_input: str) -> Optional[str]:
        """
        Calculates a confidence score based on keyword frequency and exact matching.
        """
        user_input_lower = user_input.lower()
        best_score = 0
        best_skill = None
        
        for skill_name, keywords in self.skill_keywords.items():
            score = 0
            for keyword in keywords:
                # Substring match (e.g., 'news' in 'kenyanews')
                if keyword in user_input_lower:
                    score += 1
                    # Exact word match (e.g., ' news ' in ' latest news today ')
                    if f" {keyword} " in f" {user_input_lower} ":
                        score += 2
            
            if score > best_score:
                best_score = score
                best_skill = skill_name
        
        # Logic Gate: Threshold for automatic triggering
        if best_score >= 2:
            return best_skill
        
        # Check for 'Strong' high-priority keywords even with low score
        if best_score == 1:
            strong_triggers = ['weather', 'news', 'email', 'reminder', 'osint', 'search']
            for skill_name, keywords in self.skill_keywords.items():
                if any(k in strong_triggers and k in user_input_lower for k in keywords):
                    return skill_name
        
        return None
    
    def try_run(self, user_input: str):
        """
        The bridge between raw text and SkillManager execution.
        """
        print(f"🔧 [SKILL BRIDGE]: Analyzing: '{user_input}'")
        
        skill_name = self._find_skill_by_keywords(user_input)
        
        if skill_name:
            print(f"⚡ [SKILL BRIDGE]: Best Match found -> '{skill_name}'")
            try:
                # We call SkillManager's unified execution logic
                # Pass the original user_input so the manager can perform its own final checks
                return self.skill_manager.run_skill(user_input)
            except Exception as e:
                print(f"❌ [SKILL BRIDGE]: Execution error: {e}")
                return None
        
        return None