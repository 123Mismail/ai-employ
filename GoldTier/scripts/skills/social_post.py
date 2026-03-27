import os
import requests
import tweepy
import facebook
from pathlib import Path
from dotenv import load_dotenv

# Load credentials
REPO_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

INSTAGRAM_GRAPH_URL = "https://graph.facebook.com/v18.0"


class SocialManager:
    def __init__(self):
        # X / Twitter Config
        self.x_key = os.getenv("X_API_KEY")
        self.x_secret = os.getenv("X_API_SECRET")
        self.x_token = os.getenv("X_ACCESS_TOKEN")
        self.x_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        # Facebook Config
        self.fb_token = os.getenv("FB_ACCESS_TOKEN")

        # Instagram Config (requires Facebook Business Page linked to IG Business Account)
        self.ig_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.ig_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", self.fb_token)
        self.ig_image_url = os.getenv("INSTAGRAM_IMAGE_URL", "")

        self.is_mock = not any([self.x_key, self.fb_token])

    def post_to_x(self, content):
        """Post a tweet."""
        if DRY_RUN:
            print(f"[DRY_RUN] Would post to X/Twitter: {content[:60]}...")
            return True
        if self.is_mock:
            print(f"MOCK [X/Twitter]: Posting -> {content[:50]}...")
            return True
        
        try:
            client = tweepy.Client(
                consumer_key=self.x_key, consumer_secret=self.x_secret,
                access_token=self.x_token, access_token_secret=self.x_token_secret
            )
            response = client.create_tweet(text=content)
            print(f"✅ Posted to X: {response.data['id']}")
            return True
        except Exception as e:
            print(f"X Posting Error: {e}")
            return False

    def post_to_facebook(self, content):
        """Post to FB Page."""
        if DRY_RUN:
            print(f"[DRY_RUN] Would post to Facebook: {content[:60]}...")
            return True
        if self.is_mock:
            print(f"MOCK [Facebook]: Posting -> {content[:50]}...")
            return True
        
        try:
            graph = facebook.GraphAPI(access_token=self.fb_token)
            graph.put_object(parent_object='me', connection_name='feed', message=content)
            print("✅ Posted to Facebook")
            return True
        except Exception as e:
            print(f"Facebook Posting Error: {e}")
            return False

    def post_to_instagram(self, content):
        """Post a photo+caption to Instagram via Graph API.
        Requires INSTAGRAM_BUSINESS_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN,
        and INSTAGRAM_IMAGE_URL set in .env.
        """
        if DRY_RUN:
            print(f"[DRY_RUN] Would post to Instagram: {content[:60]}...")
            return True
        if not self.ig_account_id or not self.ig_token:
            print("SKIP [Instagram]: INSTAGRAM_BUSINESS_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN not set.")
            return False
        if not self.ig_image_url:
            print("SKIP [Instagram]: INSTAGRAM_IMAGE_URL not set (required for feed posts).")
            return False

        try:
            # Step 1: Create media container
            r = requests.post(
                f"{INSTAGRAM_GRAPH_URL}/{self.ig_account_id}/media",
                params={"access_token": self.ig_token},
                json={"caption": content, "image_url": self.ig_image_url},
                timeout=30,
            )
            r.raise_for_status()
            container_id = r.json().get("id")
            if not container_id:
                print(f"Instagram media container creation failed: {r.text}")
                return False

            # Step 2: Publish container
            r = requests.post(
                f"{INSTAGRAM_GRAPH_URL}/{self.ig_account_id}/media_publish",
                params={"access_token": self.ig_token},
                json={"creation_id": container_id},
                timeout=30,
            )
            r.raise_for_status()
            print(f"✅ Posted to Instagram (media_id={r.json().get('id')})")
            return True
        except Exception as e:
            print(f"Instagram Posting Error: {e}")
            return False

    def post_all(self, content):
        """Simultaneous multi-platform post."""
        print("📢 Publishing to all channels...")
        success_x = self.post_to_x(content)
        success_fb = self.post_to_facebook(content)
        success_ig = self.post_to_instagram(content)
        return success_x and success_fb and success_ig

if __name__ == "__main__":
    manager = SocialManager()
    manager.post_all("This is a test post from my new Autonomous Digital FTE! #AI #Hackathon")
