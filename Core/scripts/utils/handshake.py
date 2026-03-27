import time
import logging
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HandshakeTool")

def perform_handshake(platform):
    if platform == "linkedin":
        url = "https://www.linkedin.com/login"
        session_path = REPO_ROOT / "linkedin_session"
    else:
        url = "https://web.whatsapp.com"
        session_path = REPO_ROOT / "whatsapp_session"

    if not session_path.exists():
        session_path.mkdir(parents=True, exist_ok=True)

    print(f"\n--- {platform.upper()} HANDSHAKE ---")
    print(f"1. A browser will open to {platform}.")
    print("2. LOG IN MANUALLY and solve any captchas.")
    print("3. Once you see your feed/chats, stay active for 15 seconds.")
    print("4. Close the browser window to save the session.")
    
    with sync_playwright() as p:
        # Use a high-quality user agent to avoid bot detection
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=False,
            user_agent=user_agent,
            viewport={'width': 1280, 'height': 720}
        )
        page = browser.new_page()
        page.goto(url)
        
        try:
            # Wait up to 10 minutes for the user to finish
            print("\nWaiting for you... (Close the browser when finished)")
            while len(browser.pages) > 0:
                time.sleep(1)
        except Exception:
            pass
        
        browser.close()
    print(f"✅ {platform.upper()} session saved!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python handshake.py [linkedin|whatsapp]")
    else:
        perform_handshake(sys.argv[1])
