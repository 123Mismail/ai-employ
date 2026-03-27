"""
LinkedIn Engagement Watcher — silver-linkedin-watcher
Perception layer: polls notifications (replies), feed (comments), people search (connects).
"""
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Root detection — insert BEFORE project imports
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PlatinumTier.scripts.linkedin_rate_limiter import RateLimiter, SessionLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("LinkedInEngagementWatcher")

VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
LINKEDIN_SESSION = REPO_ROOT / "linkedin_session"
POLL_INTERVAL = int(os.getenv("LINKEDIN_POLL_INTERVAL", "120"))
KEYWORDS = [k.strip() for k in os.getenv("LINKEDIN_KEYWORDS", "AI agents,LLM,autonomous").split(",") if k.strip()]
CONNECT_KEYWORDS = [k.strip() for k in os.getenv("LINKEDIN_CONNECT_KEYWORDS", "AI agent founder").split(",") if k.strip()]

PROCESSED_COMMENTS_FILE = REPO_ROOT / "processed_linkedin_comments.txt"
PROCESSED_POSTS_FILE = REPO_ROOT / "processed_linkedin_posts.txt"
PROCESSED_PROFILES_FILE = REPO_ROOT / "processed_linkedin_profiles.txt"


class LinkedInEngagementWatcher:

    def __init__(self):
        self.processed_comments = self._load_processed_ids(PROCESSED_COMMENTS_FILE)
        self.processed_posts = self._load_processed_ids(PROCESSED_POSTS_FILE)
        self.processed_profiles = self._load_processed_ids(PROCESSED_PROFILES_FILE)
        NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    def _load_processed_ids(self, filepath: Path) -> set:
        if filepath.exists():
            return set(filepath.read_text(encoding="utf-8").splitlines())
        return set()

    def _save_processed_id(self, filepath: Path, id_: str) -> None:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(id_ + "\n")

    def _check_security_challenge(self, page) -> None:
        url = page.url
        if any(kw in url for kw in ("checkpoint", "challenge", "authwall", "/login")):
            raise RuntimeError(f"LinkedIn security/login page detected: {url}")

    # ------------------------------------------------------------------
    # Phase 1 — Notification polling (reply tasks)
    # ------------------------------------------------------------------

    def _poll_notifications(self, page) -> list:
        logger.info("Polling LinkedIn notifications for new comments...")
        try:
            page.goto("https://www.linkedin.com/notifications/", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            self._check_security_challenge(page)
            time.sleep(3)

            notifications = page.evaluate("""
                () => {
                    const results = [];
                    let cards = document.querySelectorAll('[data-urn]');
                    cards.forEach(card => {
                        const text = card.innerText || '';
                        if (!text.toLowerCase().includes('commented')) return;
                        const urn = card.getAttribute('data-urn') || '';
                        const nameEl = card.querySelector('strong, [class*="actor"]');
                        const name = nameEl ? nameEl.innerText.trim() : '';
                        const snippetEl = card.querySelector('[class*="body"], [class*="comment"]');
                        const snippet = snippetEl ? snippetEl.innerText.trim().slice(0, 200) : text.slice(0, 200);
                        const linkEl = card.querySelector('a[href*="ugcPost"], a[href*="activity"]');
                        const postUrl = linkEl ? linkEl.href : '';
                        if (urn) results.push({notification_id: urn, commenter_name: name, comment_snippet: snippet, post_url: postUrl});
                    });
                    if (results.length > 0) return results;
                    let items = document.querySelectorAll('li[class*="notification"], [role="listitem"]');
                    items.forEach(item => {
                        const text = item.innerText || '';
                        if (!text.toLowerCase().includes('commented')) return;
                        const id = 'notif_' + Math.abs(text.split('').reduce((a,c) => (a<<5)-a+c.charCodeAt(0),0));
                        const linkEl = item.querySelector('a[href*="ugcPost"], a[href*="activity"], a[href*="feed"]');
                        results.push({notification_id: id, commenter_name: text.split('commented')[0].trim().slice(-50), comment_snippet: text.slice(0, 200), post_url: linkEl ? linkEl.href : ''});
                    });
                    return results;
                }
            """)
            logger.info("Found %d comment notification(s)", len(notifications))
            return notifications or []
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("Notification polling failed: %s", e)
            return []

    def _create_reply_task(self, notification: dict) -> None:
        nid = notification.get("notification_id", "")
        if not nid or nid in self.processed_comments:
            return
        commenter = notification.get("commenter_name", "Someone")
        snippet = notification.get("comment_snippet", "")
        post_url = notification.get("post_url", "")
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_nid = nid.replace(":", "_").replace("/", "_")[:40]
        filename = f"LINKEDIN_REPLY_{safe_nid}_{ts}.md"
        content = f"""---
type: linkedin_reply
source: linkedin_notifications
notification_id: "{nid}"
post_url: "{post_url}"
commenter_name: "{commenter}"
comment_snippet: "{snippet[:200]}"
timestamp: "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
status: pending
---

# New Comment on Your LinkedIn Post

- **From**: {commenter}
- **Comment**: {snippet[:200]}
- **Post**: {post_url}
"""
        (NEEDS_ACTION / filename).write_text(content, encoding="utf-8")
        self._save_processed_id(PROCESSED_COMMENTS_FILE, nid)
        self.processed_comments.add(nid)
        logger.info("Created reply task for comment by: %s", commenter)

    # ------------------------------------------------------------------
    # Phase 2 — Feed scanning (comment tasks)
    # ------------------------------------------------------------------

    def _scan_feed(self, page) -> list:
        logger.info("Scanning LinkedIn feed for AI posts (keywords: %s)...", KEYWORDS[:3])
        try:
            page.goto("https://www.linkedin.com/feed/", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            self._check_security_challenge(page)
            logger.info("Feed page loaded: %s", page.url)
            time.sleep(4)

            posts = page.evaluate("""
                (keywords) => {
                    const results = [];
                    const kw = keywords.map(k => k.toLowerCase());
                    const seen = new Set();

                    // LinkedIn hashes class names. Use activity/ugcPost links as anchors to find post cards.
                    const postLinks = Array.from(document.querySelectorAll(
                        'a[href*="ugcPost"], a[href*="/feed/update/"], a[href*="activity"]'
                    ));

                    postLinks.forEach(link => {
                        if (results.length >= 5) return;
                        const post_url = link.href.split('?')[0];
                        if (seen.has(post_url)) return;
                        seen.add(post_url);

                        // Walk up to find the post card
                        let card = link;
                        for (let i = 0; i < 10; i++) {
                            if (!card.parentElement) break;
                            card = card.parentElement;
                            const t = (card.innerText || '').trim();
                            // Post cards are sizeable (100-5000 chars) and contain the post text
                            if (t.length > 100 && t.length < 5000) break;
                        }

                        const text = (card.innerText || '').trim();
                        if (!text || text.length < 50) return;
                        if (!kw.some(k => text.toLowerCase().includes(k))) return;

                        // Author: first meaningful line, or span[aria-hidden] in a profile link
                        const authorLink = card.querySelector('a[href*="/in/"]');
                        const authorSpan = authorLink ? authorLink.querySelector('span[aria-hidden]') : null;
                        const post_author = authorSpan ? authorSpan.innerText.trim() :
                            (authorLink ? authorLink.innerText.trim().split('\\n')[0] : 'Unknown');

                        // Headline: second line in author section
                        const lines = text.split('\\n').map(l=>l.trim()).filter(l=>l.length>3);
                        const authorIdx = lines.findIndex(l => l === post_author);
                        const post_author_headline = authorIdx >= 0 ? (lines[authorIdx+1] || '') : '';

                        const post_snippet = text.slice(0, 300);
                        results.push({
                            post_url,
                            post_author,
                            post_author_headline,
                            post_snippet,
                            keywords_matched: kw.filter(k => post_snippet.toLowerCase().includes(k))
                        });
                    });
                    return results;
                }
            """, KEYWORDS)
            logger.info("Feed scan found %d relevant post(s)", len(posts))
            return posts or []
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("Feed scan failed: %s", e)
            return []

    def _create_comment_task(self, post: dict) -> None:
        post_url = post.get("post_url", "")
        if not post_url or post_url in self.processed_posts:
            return
        if not RateLimiter().can_execute("comment"):
            logger.info("Comment limit reached — skipping feed task creation")
            return
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_id = post_url.replace("https://", "").replace("/", "_")[-30:]
        matched = ", ".join(post.get("keywords_matched", []))
        content = f"""---
type: linkedin_comment
source: linkedin_feed
post_url: "{post_url}"
post_author: "{post.get('post_author', 'Unknown')}"
post_author_headline: "{post.get('post_author_headline', '')}"
post_snippet: "{post.get('post_snippet', '')[:300]}"
keywords_matched: [{matched}]
timestamp: "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
status: pending
---

# AI Post Detected — Comment Opportunity

- **Author**: {post.get('post_author', 'Unknown')} — {post.get('post_author_headline', '')}
- **Keywords matched**: {matched}

## Post Snippet
> {post.get('post_snippet', '')[:300]}
"""
        (NEEDS_ACTION / f"LINKEDIN_COMMENT_{safe_id}_{ts}.md").write_text(content, encoding="utf-8")
        self._save_processed_id(PROCESSED_POSTS_FILE, post_url)
        self.processed_posts.add(post_url)
        logger.info("Created comment task for post by: %s", post.get("post_author"))

    # ------------------------------------------------------------------
    # Phase 3 — People search (connect tasks)
    # ------------------------------------------------------------------

    def _search_people(self, page) -> list:
        from urllib.parse import quote
        query = " OR ".join(CONNECT_KEYWORDS[:3])
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(query)}&network=%5B%22S%22%5D"
        logger.info("Searching LinkedIn people: %s...", query[:50])
        try:
            page.goto(search_url, timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            self._check_security_challenge(page)
            logger.info("People search page loaded: %s", page.url)
            time.sleep(4)

            candidates = page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();

                    // Find all profile links — LinkedIn hashes class names so we cannot rely on them.
                    // Instead: anchor tag with /in/ path is always present for each result card.
                    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'));

                    profileLinks.forEach(link => {
                        if (results.length >= 3) return;

                        const profile_url = link.href.split('?')[0];
                        // Skip nav links, footer links, sidebar — they repeat
                        if (seen.has(profile_url)) return;
                        // Skip very short URLs like /in/ with no slug
                        if (profile_url.replace('https://www.linkedin.com/in/', '').length < 3) return;

                        seen.add(profile_url);

                        // Walk up to find the result card container (stop at 8 levels)
                        let card = link;
                        for (let i = 0; i < 8; i++) {
                            if (!card.parentElement) break;
                            card = card.parentElement;
                            const text = card.innerText || '';
                            // A real card has name + some headline text and is reasonably sized
                            if (text.length > 40 && text.length < 2000) break;
                        }

                        const cardText = (card.innerText || '').trim();
                        // Skip sidebar ads / promo cards
                        if (cardText.includes('Promoted') || cardText.includes('Sales Navigator')) return;

                        // Name: prefer span[aria-hidden] inside the link (LinkedIn puts the visible name there)
                        const nameSpan = link.querySelector('span[aria-hidden]');
                        const name = nameSpan ? nameSpan.innerText.trim() : link.innerText.trim().split('\\n')[0].trim();
                        if (!name || name.toLowerCase().includes('linkedin member') || name.length < 2) return;

                        // Headline + company: lines of text after the name in the card
                        const lines = cardText.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l !== name);
                        const headline = lines[0] || '';
                        const company = lines[1] || '';

                        results.push({candidate_name: name, candidate_headline: headline, candidate_company: company, profile_url});
                    });
                    return results;
                }
            """)
            logger.info("People search found %d candidate(s)", len(candidates))
            return candidates or []
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("People search failed: %s", e)
            return []

    def _create_connect_task(self, candidate: dict) -> None:
        profile_url = candidate.get("profile_url", "")
        if not profile_url or profile_url in self.processed_profiles:
            return
        if not RateLimiter().can_execute("connect"):
            logger.info("Connection limit reached — skipping connect task creation")
            return
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_id = profile_url.replace("https://www.linkedin.com/in/", "").replace("/", "")[:30]
        content = f"""---
type: linkedin_connect
source: linkedin_people_search
profile_url: "{profile_url}"
candidate_name: "{candidate.get('candidate_name', '')}"
candidate_headline: "{candidate.get('candidate_headline', '')}"
candidate_company: "{candidate.get('candidate_company', '')}"
search_keywords: "{', '.join(CONNECT_KEYWORDS)}"
timestamp: "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
status: pending
---

# Connection Opportunity — AI Niche

- **Name**: {candidate.get('candidate_name', '')}
- **Headline**: {candidate.get('candidate_headline', '')}
- **Company**: {candidate.get('candidate_company', '')}
- **Profile**: {profile_url}
"""
        (NEEDS_ACTION / f"LINKEDIN_CONNECT_{safe_id}_{ts}.md").write_text(content, encoding="utf-8")
        self._save_processed_id(PROCESSED_PROFILES_FILE, profile_url)
        self.processed_profiles.add(profile_url)
        logger.info("Created connect task for: %s", candidate.get("candidate_name"))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        logger.info("Starting LinkedIn Engagement Watcher (poll every %ds)...", POLL_INTERVAL)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LINKEDIN_SESSION),
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = browser.new_page()

            while True:
                if RateLimiter().is_paused():
                    logger.warning("Account paused — skipping poll. Fix account_paused in linkedin_rate_state.json")
                    time.sleep(POLL_INTERVAL)
                    continue

                lock = SessionLock(holder="silver-linkedin-watcher")
                try:
                    lock.acquire()
                    for n in self._poll_notifications(page):
                        self._create_reply_task(n)
                    for post in self._scan_feed(page):
                        self._create_comment_task(post)
                    for candidate in self._search_people(page):
                        self._create_connect_task(candidate)
                except RuntimeError as e:
                    RateLimiter().pause_account(str(e))
                except Exception as e:
                    logger.error("Poll cycle error: %s", e)
                finally:
                    lock.release()

                time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    LinkedInEngagementWatcher().run()
