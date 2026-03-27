import os
import sys
import base64
import shutil
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Root detection
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))

# Import shared Auth logic from SilverTier
from SilverTier.scripts.utils.google_auth import get_gmail_service

class EmailSender:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.approved_path = self.vault_path / "Approved"
        self.done_path = self.vault_path / "Done"
        self.service = get_gmail_service()

    def check_for_approved_emails(self):
        """Monitor the Approved folder for email drafts to send."""
        approved_files = list(self.approved_path.glob("APPROVE_REPLY_*.md"))
        
        if not approved_files:
            print(f"No approved emails found in {self.approved_path}")
            return

        for file in approved_files:
            print(f"Found approved email: {file.name}")
            self.send_approved_email(file)

    def send_approved_email(self, file: Path):
        """Parse the approval file and send via Gmail API."""
        if DRY_RUN:
            print(f"[DRY_RUN] Would send email from approval file: {file.name}")
            shutil.move(str(file), str(self.done_path / file.name))
            return
        try:
            content = file.read_text(encoding='utf-8')
            recipient = self.extract_meta(content, "recipient:")
            subject = self.extract_meta(content, "subject:")
            
            body_parts = content.split("---", 2)
            if len(body_parts) < 3:
                print(f"Error: Invalid file format for {file.name}")
                return
            
            body = body_parts[2].split("## To Send", 1)[0].strip()
            
            if "PLACEHOLDER" in recipient:
                print(f"Skipping placeholder recipient for {file.name}. Please edit the file first.")
                return

            message = EmailMessage()
            message.set_content(body)
            message["To"] = recipient
            message["From"] = "me"
            message["Subject"] = subject
            
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}
            
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            
            print(f"Email sent successfully! Message ID: {send_message['id']}")
            shutil.move(str(file), str(self.done_path / file.name))
            
        except Exception as e:
            print(f"Failed to send email {file.name}: {e}")

    def extract_meta(self, content, key):
        for line in content.splitlines():
            if line.startswith(key):
                return line.split(key)[1].strip().strip('"')
        return "Unknown"

if __name__ == "__main__":
    VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"
    sender = EmailSender(VAULT_PATH)
    print(f"Checking Approved folder: {sender.approved_path}")
    sender.check_for_approved_emails()
