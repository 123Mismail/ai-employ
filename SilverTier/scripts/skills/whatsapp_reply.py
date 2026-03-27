import time
import logging
import sys
import os
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))
ENV_PATH = REPO_ROOT / ".env"

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WhatsAppReplySkill")

class WhatsAppManager:
    def __init__(self):
        self.session_path = REPO_ROOT / "whatsapp_session"
        config = {}
        if ENV_PATH.exists():
            config = dotenv_values(ENV_PATH)
        
        # Use phone number if available, fallback to name
        self.target_id = config.get("WHATSAPP_NUMBER", config.get("WHATSAPP_OWNER_NAME", "Mine(You)"))
        logger.info(f"Initialized WhatsApp Manager with target: {self.target_id}")

    def send_message(self, recipient, content):
        """Ultra-Reliable WhatsApp send: Use direct send URL."""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would send WhatsApp to {recipient}: {content[:60]}...")
            return True
        target = recipient if recipient != "Mine(You)" else self.target_id
        # Clean target number (remove + and spaces)
        clean_target = "".join(filter(str.isdigit, target))
        
        logger.info(f"🚀 Attempting to send WhatsApp to {clean_target}...")
        
        try:
            with sync_playwright() as p:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=False,
                    user_agent=user_agent
                )
                page = browser.new_page()
                
                # Direct URL approach
                encoded_content = quote(content)
                send_url = f"https://web.whatsapp.com/send?phone={clean_target}&text={encoded_content}"
                logger.info(f"🔗 Navigating to: {send_url}")
                page.goto(send_url)
                
                logger.info("⏳ Waiting for WhatsApp Web to load and message to be ready (45s)...")
                # Wait longer for the 'send' button to become visible/active
                time.sleep(45) 
                
                # Press Enter to actually SEND the message
                logger.info("📤 Triggering SEND (Enter)...")
                page.keyboard.press("Enter")
                
                time.sleep(5) # Wait for message to fly out
                logger.info("✅ WhatsApp message sent successfully via direct URL!")
                browser.close()
                return True
        except Exception as e:
            logger.error(f"WhatsApp Direct-Send Error: {e}")
            return False

if __name__ == "__main__":
    manager = WhatsAppManager()
    manager.send_message("Mine(You)", "Modular system test: Secure Search-by-Number active! 🤖✅")
