import time
import logging
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))
ENV_PATH = REPO_ROOT / ".env"

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LinkedInPostSkill")

class LinkedInManager:
    def __init__(self):
        self.session_path = REPO_ROOT / "linkedin_session"
        # Ensure session directory exists
        if not self.session_path.exists():
            self.session_path.mkdir(parents=True, exist_ok=True)

    def post_update(self, content):
        """Automate creating a new post on LinkedIn feed."""
        logger.info("🚀 Attempting to post to LinkedIn...")
        
        try:
            with sync_playwright() as p:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=False, # Keep visible for now
                    user_agent=user_agent
                )
                page = browser.new_page()
                page.goto("https://www.linkedin.com/feed/")
                
                logger.info("⏳ Waiting for LinkedIn Feed to load (45s)...")
                # Wait for feed to actually settle
                time.sleep(45) 
                
                # 1. Trigger Post Modal via Shortcut
                logger.info("🔍 Triggering post modal via keyboard shortcut (c)...")
                page.keyboard.press("c") # LinkedIn shortcut for 'Start a post'
                time.sleep(5)
                
                # 2. Type content
                logger.info("✍️ Typing post content...")
                try:
                    # Focus is usually automatic on the modal
                    page.keyboard.type(content, delay=150) # Very human-like delay
                    logger.info("✅ Content typed.")
                except Exception as e:
                    logger.error(f"❌ Failed to type content: {e}")
                    page.screenshot(path="linkedin_error.png")
                    raise e
                
                time.sleep(5)
                
                # 3. Dispatched via Shortcut (Ctrl+Enter)
                logger.info("📤 Dispatching post via Ctrl+Enter...")
                page.keyboard.down("Control")
                page.keyboard.press("Enter")
                page.keyboard.up("Control")
                
                time.sleep(15) # Wait for processing
                logger.info("🎉 LinkedIn post successfully created!")
                browser.close()
                return True
        except Exception as e:
            logger.error(f"LinkedIn Posting Error: {e}")
            return False

if __name__ == "__main__":
    manager = LinkedInManager()
    manager.post_update("Modular system test: LinkedIn Skill active! 🤖🚀 #AIEmployee #Hackathon")
