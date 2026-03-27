import re
import time
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure repo root is on sys.path BEFORE importing project modules
REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from Core.scripts.utils.base_watcher import BaseWatcher
ENV_PATH = REPO_ROOT / ".env"

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WhatsAppWatcher")

class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: Path):
        super().__init__(str(vault_path), check_interval=60)
        self.session_path = REPO_ROOT / "whatsapp_session"
        self.processed_chats_file = REPO_ROOT / "processed_chats.txt"
        self.processed_chats = self.load_processed_chats()
        
        # Load config
        config = {}
        if ENV_PATH.exists():
            config = dotenv_values(ENV_PATH)
        
        # Default to 'You' for self-chat, but allow override
        self.owner_name = config.get("WHATSAPP_OWNER_NAME", "You")
        self.owner_number = config.get("WHATSAPP_NUMBER", "+923483144231")
        self.clean_number = "".join(filter(str.isdigit, self.owner_number))
        
        # Ensure session directory exists
        if not self.session_path.exists():
            self.session_path.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self) -> list:
        # Playwright-driven: run() manages its own event loop
        return []

    def create_action_file(self, item) -> Path:
        return self.process_owner_message(item.get("name", ""), item.get("content", ""))

    def load_processed_chats(self):
        if self.processed_chats_file.exists():
            return set(self.processed_chats_file.read_text().splitlines())
        return set()

    def save_processed_chat(self, chat_id):
        self.processed_chats.add(chat_id)
        with open(self.processed_chats_file, "a") as f:
            f.write(f"{chat_id}\n")

    def run(self):
        logger.info(f"Starting Proactive WhatsApp Watcher (Target: {self.owner_number})...")
        while True:
            try:
                self._run_session()
            except Exception as e:
                logger.error(f"Browser session crashed, restarting in 15s: {e}")
                time.sleep(15)

    def _run_session(self):
        self_chat_url = f"https://web.whatsapp.com/send?phone={self.clean_number}"
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=False
            )
            try:
                page = browser.new_page()
                page.goto("https://web.whatsapp.com")
                logger.info("Waiting for WhatsApp Web to load...")
                time.sleep(30)

                # Open self-chat ONCE — navigate by URL, no keyboard needed
                logger.info(f"Opening self-chat: {self_chat_url}")
                page.goto(self_chat_url)
                time.sleep(8)

                # Handle "Continue to chat" popup that appears on send?phone= URL
                try:
                    page.locator("text=Continue to chat").click(timeout=5000)
                    logger.info("Clicked 'Continue to chat'")
                    time.sleep(5)
                except Exception:
                    pass  # not shown — already in chat

                # Wait for #main chat panel to confirm we're inside the chat
                try:
                    page.wait_for_selector("#main", timeout=15000)
                    logger.info("Self-chat panel ready.")
                except Exception:
                    logger.warning("Self-chat panel slow to load, continuing anyway")

                # Poll loop — WhatsApp Web is real-time (WebSocket), no reload needed
                while True:
                    # 1. Process any outgoing send requests from the local agent
                    self._process_outbox(page)

                    # 2. Check self-chat for new inbound messages
                    logger.info("Polling self-chat for new messages...")
                    content = self._read_last_message(page)
                    if content:
                        msg_id = f"{content[:20]}_{datetime.now().strftime('%Y%m%d%H')}"
                        if msg_id not in self.processed_chats:
                            logger.info(f"NEW SELF-MESSAGE FOUND: '{content[:50]}'")
                            self.process_owner_message(self.owner_name, content)
                            self.save_processed_chat(msg_id)
                        else:
                            logger.info("No new messages (already processed).")
                    else:
                        logger.info("No readable messages in self-chat yet.")
                    time.sleep(60)
            finally:
                browser.close()

    def _process_outbox(self, page):
        """Send any messages queued by the local agent in WhatsApp_Outbox/."""
        import json
        from urllib.parse import quote
        outbox_dir = Path(self.needs_action).parent / "WhatsApp_Outbox"
        if not outbox_dir.exists():
            return
        for outbox_file in sorted(outbox_dir.glob("SEND_*.json")):
            try:
                payload = json.loads(outbox_file.read_text(encoding="utf-8"))
                recipient = payload.get("recipient", "")
                body = payload.get("body", "")
                clean_recipient = "".join(filter(str.isdigit, recipient)) or self.clean_number
                send_url = f"https://web.whatsapp.com/send?phone={clean_recipient}&text={quote(body)}"
                logger.info(f"Outbox: sending to {clean_recipient} via {outbox_file.name}")
                page.goto(send_url)
                time.sleep(8)
                # Handle "Continue to chat" if it appears
                try:
                    page.locator("text=Continue to chat").click(timeout=4000)
                    time.sleep(4)
                except Exception:
                    pass
                # Click the input box first to ensure it has focus
                for input_sel in [
                    '[data-testid="conversation-compose-box-input"]',
                    'div[contenteditable="true"][data-tab="10"]',
                    'footer div[contenteditable="true"]',
                    'div[contenteditable="true"]',
                ]:
                    try:
                        el = page.wait_for_selector(input_sel, timeout=5000)
                        if el:
                            el.click()
                            time.sleep(1)
                            break
                    except Exception:
                        continue
                # Try send button selectors, then fall back to Enter
                sent = False
                for send_sel in [
                    '[data-testid="send"]',
                    'button[aria-label="Send"]',
                    'span[data-icon="send"]',
                    '[data-icon="send"]',
                ]:
                    try:
                        btn = page.wait_for_selector(send_sel, timeout=3000)
                        if btn:
                            btn.click()
                            sent = True
                            break
                    except Exception:
                        continue
                if not sent:
                    page.keyboard.press("Enter")
                time.sleep(3)
                logger.info(f"[OK] Sent WhatsApp message to {clean_recipient} (btn={sent})")
                outbox_file.unlink()
                # Mark sent body as processed so it won't trigger a new task when detected
                sent_id = f"{body[:20]}_{datetime.now().strftime('%Y%m%d%H')}"
                self.save_processed_chat(sent_id)
                # Navigate back to self-chat after sending
                page.goto(f"https://web.whatsapp.com/send?phone={self.clean_number}")
                time.sleep(6)
                try:
                    page.locator("text=Continue to chat").click(timeout=3000)
                    time.sleep(3)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Outbox send failed for {outbox_file.name}: {e}")

    # Patterns that indicate a WhatsApp UI element, not a real message
    _SKIP_PATTERNS = re.compile(
        r"^\d{1,2}:\d{2}\s*(AM|PM)?$"   # time separator: "5:42 PM", "17:42"
        r"|^(TODAY|YESTERDAY)$"           # date separators
        r"|^\w+ \d{1,2},?\s*\d{4}$"      # "March 25, 2026"
        r"|^Messages and calls are end-to-end encrypted",
        re.IGNORECASE,
    )

    def _read_last_message(self, page) -> str:
        """Read the last real message text from the open WhatsApp Web chat."""
        try:
            texts = page.evaluate("""
                () => {
                    const results = [];

                    // Strategy 1: copyable-text data-testid (most stable across versions)
                    let nodes = document.querySelectorAll('[data-testid="copyable-text"] span[dir]');
                    nodes.forEach(n => { const t = n.textContent.trim(); if (t) results.push(t); });
                    if (results.length > 0) return results;

                    // Strategy 2: selectable-text inside #main
                    nodes = document.querySelectorAll('#main span.selectable-text');
                    nodes.forEach(n => { const t = n.textContent.trim(); if (t) results.push(t); });
                    if (results.length > 0) return results;

                    // Strategy 3: message rows
                    nodes = document.querySelectorAll('#main [role="row"] span[dir="ltr"]');
                    nodes.forEach(n => { const t = n.textContent.trim(); if (t) results.push(t); });
                    return results;
                }
            """)
            if not texts:
                return ""
            # Walk from newest to oldest, skipping UI chrome (time separators etc.)
            for text in reversed(texts):
                text = text.strip()
                if text and not self._SKIP_PATTERNS.match(text):
                    return text
            return ""
        except Exception as e:
            logger.debug(f"_read_last_message JS error: {e}")
            return ""

    def process_owner_message(self, chat_name, content=""):
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        filename = f"WHATSAPP_OWNER_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        filepath = self.needs_action / filename
        
        content_block = f"\n## Message Content\n{content}" if content else ""
        
        file_content = f"""---
type: whatsapp
source: WhatsApp Web (Owner)
from: {chat_name}
timestamp: {timestamp}
status: pending
---
# New Message from Owner (Self)
A new message was detected in your personal chat.
{content_block}

## Action Required
1. Open WhatsApp Web to read your personal note/task.
2. AI Employee ready to process this command.
"""
        filepath.write_text(file_content, encoding='utf-8')
        logger.info(f"[OK] Created Owner-WhatsApp task: {filename}")

if __name__ == "__main__":
    VAULT = REPO_ROOT / "AI_Employee_Vault"
    watcher = WhatsAppWatcher(VAULT)
    watcher.run()
