import time
import logging
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LinkedInLoginAssist")

def manual_login():
    session_path = REPO_ROOT / "linkedin_session"
    if not session_path.exists():
        session_path.mkdir(parents=True, exist_ok=True)

    logger.info("🛠️ Starting Manual Login Assistant...")
    logger.info("👉 This will open a browser for you to log in manually.")
    logger.info("👉 Once logged in and you see your feed, simply CLOSE THE BROWSER.")
    
    with sync_playwright() as p:
        # Use a very realistic user agent to avoid Google bot detection
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=False,
            user_agent=user_agent,
            slow_mo=50 # Slower interactions to seem more human
        )
        
        page = browser.new_page()
        page.goto("https://www.linkedin.com/login")
        
        logger.info("⏳ Waiting for you to log in... (Window will stay open)")
        
        # Keep the browser open until the user manually closes it or 10 minutes pass
        try:
            # Wait for the feed to be visible as a sign of success
            page.wait_for_selector(".share-box-feed-entry__trigger", timeout=600000) 
            logger.info("✅ Login detected! Session saved. You can close the browser now.")
            time.sleep(5) 
        except Exception:
            logger.info("ℹ️ Timeout or browser closed. Checking if session was saved...")
        
        browser.close()
        logger.info("🎉 Done. You can now run the automated posting skill.")

if __name__ == "__main__":
    manual_login()
