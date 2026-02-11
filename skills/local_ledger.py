import csv
import os
import datetime
from skill_manager import Skill
import sys

# Adds the root directory (where llm.py lives) to the search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from brain.llm import run_llm  # If llm is in a folder named brain
except ImportError:
    import brain.llm                     # If llm.py is in the root folder

class LocalLedgerSkill(Skill):
    name = "Local Ledger"
    keywords = ["money", "balance", "spent", "received", "add", "pay"]
    file_path = "ledger.csv"
    supported_intents = ["local_ledger"]
    def __init__(self):
        # Create the file with headers if it doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Amount", "Description"])

    def get_balance(self):
        total = 0.0
        with open(self.file_path, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += float(row["Amount"])
        return total

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").lower()

        # 1. Classify Action via Brain
        action_prompt = [
            {"role": "system", "content": "Analyze input. Return ONLY: ADD, SPEND, or BALANCE."},
            {"role": "user", "content": user_input}
        ]
        action = run_llm(action_prompt).strip().upper()

        if "BALANCE" in action:
            return f"Lucky, your local balance is {self.get_balance()} shillings."

        # 2. Extract Data via Brain
        data_prompt = [
            {"role": "system", "content": "Extract Amount and Item. Return as: Amount | Item. Example: 500 | Coffee"},
            {"role": "user", "content": user_input}
        ]
        extracted = run_llm(data_prompt).split("|")
        
        try:
            amount = float(extracted[0].strip())
            description = extracted[1].strip()
            
            # Spend = Negative, Add = Positive
            final_amount = -amount if "SPEND" in action else amount
            
            # 3. Save to Local CSV
            with open(self.file_path, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.date.today(), final_amount, description])
            
            verb = "spent" if final_amount < 0 else "added"
            return f"Logged {amount} for {description}. Your new balance is {self.get_balance()}."
            
        except:
            return "I understood the request but the numbers got messy. Could you repeat that?"