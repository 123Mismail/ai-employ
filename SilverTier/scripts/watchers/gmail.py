import time
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Root detection — insert BEFORE project imports to avoid shadowing system modules
REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

# Import shared Auth logic from SilverTier
from SilverTier.scripts.utils.google_auth import get_gmail_service
from Core.scripts.utils.base_watcher import BaseWatcher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GmailWatcher")

DEFAULT_GMAIL_QUERY = "is:unread is:important"

class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: Path, check_interval: int = 300):
        super().__init__(str(vault_path), check_interval)
        self.service = get_gmail_service()
        self.processed_ids_file = REPO_ROOT / "processed_emails.txt"
        self.processed_ids = self.load_processed_ids()
        self.gmail_query = os.getenv("GMAIL_QUERY", DEFAULT_GMAIL_QUERY)

    def load_processed_ids(self):
        if self.processed_ids_file.exists():
            return set(self.processed_ids_file.read_text().splitlines())
        return set()

    def save_processed_id(self, msg_id):
        self.processed_ids.add(msg_id)
        with open(self.processed_ids_file, "a") as f:
            f.write(f"{msg_id}\n")

    def check_for_updates(self) -> list:
        """Poll Gmail for unread messages matching the configured query."""
        try:
            results = self.service.users().messages().list(
                userId='me', q=self.gmail_query
            ).execute()
            messages = results.get('messages', [])
            if not messages:
                logger.info("No new important emails found.")
                return []
            return [m for m in messages if m['id'] not in self.processed_ids]
        except Exception as e:
            logger.error(f"Error polling Gmail: {e}")
            return []

    def create_action_file(self, message: dict) -> Path:
        """Implements BaseWatcher: fetches email and writes task file."""
        return self.process_email(message['id'])

    def process_email(self, msg_id):
        """Fetch email details and create a task file in the vault."""
        msg = self.service.users().messages().get(userId='me', id=msg_id).execute()

        # Extract headers (Subject, From)
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', 'Unknown Sender')
        snippet = msg.get('snippet', '')

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        filename = f"EMAIL_{msg_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        filepath = self.needs_action / filename
        
        content = f"""---
type: email
source: Gmail
email_msg_id: {msg_id}
email_from: "{sender}"
email_subject: "{subject}"
timestamp: {timestamp}
status: pending
---

# New Important Email: {subject}

- **From**: {sender}
- **Subject**: {subject}
- **Received**: {timestamp}

## Content Snippet
> {snippet}
"""
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created task for Email: {subject}")
        self.save_processed_id(msg_id)

    def run(self):
        logger.info(f"Starting Gmail Watcher (polling every {self.check_interval}s)...")
        while True:
            items = self.check_for_updates()
            for item in items:
                self.create_action_file(item)
            time.sleep(self.check_interval)

if __name__ == "__main__":
    VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"
    watcher = GmailWatcher(VAULT_PATH)
    watcher.run()
