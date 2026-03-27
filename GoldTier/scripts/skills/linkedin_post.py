import time
import logging
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
ENV_PATH = REPO_ROOT / ".env"

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LinkedInSkill")

class LinkedInManager:
    def __init__(self):
        self.session_path = REPO_ROOT / "linkedin_session"
        config = {}
        if ENV_PATH.exists():
            config = dotenv_values(ENV_PATH)
        self.is_mock = config.get("LINKEDIN_MOCK", "true").lower() == "true"
        if not self.session_path.exists():
            self.session_path.mkdir(parents=True, exist_ok=True)

    def post_update(self, content):
        """Ultra-robust LinkedIn post automation."""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would post to LinkedIn: {content[:60]}...")
            return True
        if self.is_mock:
            logger.info(f"MOCK [LinkedIn]: Posting -> {content[:50]}...")
            return True

        logger.info(" Starting LinkedIn Post Automation...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=False,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = browser.new_page()
                page.goto("https://www.linkedin.com/feed/")
                
                # Extreme wait for slow connections
                page.wait_for_load_state("networkidle")
                time.sleep(10)
                
                 
                found = False
                
                possible_selectors = [
                    "button.share-mb-launcher",
                    "button:has-text('Start a post')",
                    "div.share-box-feed-entry__trigger",
                    "span:has-text('Start a post')"
                ]
                
                for sel in possible_selectors:
                    if page.is_visible(sel):
                        logger.info(f"Found trigger via: {sel}")
                        page.click(sel)
                        found = True
                        break
                
                if not found:
                    # Fallback: Try to find by role and name
                    try:
                        page.get_by_role("button", name="Start a post").click()
                        found = True
                    except: pass

                if not found:
                    logger.error(" Final attempt failed: Could not find 'Start a post' trigger.")
                    browser.close()
                    return False

                # Post content
                time.sleep(5)
                page.keyboard.type(content) # More reliable than fill for some editors
                logger.info("Typed post content.")
                time.sleep(2)
                
                # Final Post Button
                # Usually: .share-actions__primary-action or button with text "Post"
                try:
                    page.get_by_role("button", name="Post").click()
                    logger.info("Clicked the final Post button.")
                except:
                    page.click("button.share-actions__primary-action")
                
                time.sleep(5)
                logger.info(" LinkedIn post published successfully!")
                browser.close()
                return True
        except Exception as e:
            logger.error(f"LinkedIn Error: {e}")
            return False

if __name__ == "__main__":
    manager = LinkedInManager()
    manager.post_update("Final test of the robust LinkedIn loop!")
