import smtplib
import imaplib
import email
from email.message import EmailMessage
import os
import logging
from dotenv import load_dotenv
from skill_manager import Skill
import sys

# Adds the root directory (where llm.py lives) to the search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from brain.llm import run_llm  # If llm is in a folder named brain
except ImportError:
    import brain.llm                     # If llm.py is in the root folder

# Load the secret vault
load_dotenv()

class EmailSkill(Skill):
    name = "EmailSkill"
    description = "Manages email functions using LLM-powered natural language parsing."
    keywords = ["email", "inbox", "send", "mail", "check"]
    supported_intents = ["email"]
    def __init__(self):
        # 🔐 Pulling credentials from .env
        self.email_addr = os.getenv("EMAIL_ADDRESS")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        
        self.logger = logging.getLogger("Crystal.EmailSkill")

        if not self.email_addr or not self.password:
            print("⚠️ [EMAIL]: Credentials missing in .env! Email skill will fail.")

    def send_email(self, recipient, subject, body):
        try:
            msg = EmailMessage()
            msg["From"] = self.email_addr
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self.email_addr, self.password)
                smtp.send_message(msg)
            
            return f"✅ Email sent to {recipient} successfully."
        except Exception as e:
            return f"❌ Failed to send email: {e}"

    def read_emails(self, limit=3):
        try:
            with imaplib.IMAP4_SSL(self.imap_server) as mail:
                mail.login(self.email_addr, self.password)
                mail.select("inbox")
                _, data = mail.search(None, "ALL")
                ids = data[0].split()

                if not ids:
                    return "Your inbox is empty, Lucky."

                recent_ids = ids[-limit:]
                results = []
                for e_id in reversed(recent_ids):
                    _, msg_data = mail.fetch(e_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])
                    sender = msg.get("From")
                    subject = msg.get("Subject")
                    results.append(f"📩 FROM: {sender}\n   SUBJECT: {subject}")
                
                return "\n\n".join(results)
        except Exception as e:
            return f"❌ Error reading inbox: {e}"

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").lower()

        # 1. READ logic
        if any(word in user_input for word in ["read", "check", "inbox"]):
            return self.read_emails()

        # 2. SEND logic (Powered by LLM)
        if any(word in user_input for word in ["send", "write", "mail"]):
            prompt = [
                {"role": "system", "content": "Extract 'recipient' and 'message' from input. Return as: recipient | message. If missing, return ERROR."},
                {"role": "user", "content": user_input}
            ]
            
            extracted = run_llm(prompt)
            
            if "ERROR" in extracted or "|" not in extracted:
                return "Who should I email, and what should I say? (e.g., 'Email boss@work.com saying I am done.')"

            recipient, body = extracted.split("|", 1)
            return self.send_email(recipient.strip(), "Automated Message from Crystal", body.strip())

        return "I can read your inbox or send an email. Which would you like?"