import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError
from PlatinumTier.scripts.linkedin_rate_limiter import RateLimiter, SessionLock
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def execute(approval_path: Path, vault_path: Path) -> bool:
    try:
        fm = read_frontmatter(approval_path)
        post_url = fm.get("post_url", "")
        commenter = fm.get("commenter_name", "")
        reply_body = fm.get("reply_body", "")

        if not post_url or not reply_body:
            raise ValueError("approval missing post_url or reply_body")

        rl = RateLimiter()
        if rl.is_paused():
            logger.warning("LinkedIn account paused — skipping reply execution")
            return False

        # Claim before execute
        in_progress_dir = vault_path / "In_Progress" / "local"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        claimed_path = in_progress_dir / approval_path.name
        move_task(approval_path, in_progress_dir)

        if DRY_RUN:
            logger.info("[DRY_RUN] would reply to %s on post: %s", commenter, post_url)
            success = True
        else:
            success = _execute_reply(post_url, commenter, reply_body)

        if success:
            update_frontmatter(claimed_path, {
                "status": "approved", "approved_by": "human",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            })
            move_task(claimed_path, vault_path / "Done")
            log_action(vault_path, "linkedin_reply_sent", "local", approval_path.name,
                       parameters={"commenter": commenter, "post_url": post_url, "dry_run": DRY_RUN},
                       approval_status="approved", approved_by="human")
            logger.info("Reply posted to %s's comment (dry_run=%s)", commenter, DRY_RUN)
        else:
            move_task(claimed_path, vault_path / "Rejected")
            log_action(vault_path, "linkedin_reply_failed", "local", approval_path.name,
                       result="error", parameters={"commenter": commenter})
        return success

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_linkedin_reply_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "linkedin_reply_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _execute_reply(post_url: str, commenter: str, reply_body: str) -> bool:
    from playwright.sync_api import sync_playwright
    from pathlib import Path as _Path
    REPO_ROOT = _Path(__file__).resolve().parents[4]
    session_path = REPO_ROOT / "linkedin_session"

    with SessionLock(holder="local-linkedin-reply"):
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            try:
                page = browser.new_page()
                page.goto(post_url, timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)

                # Security check
                if any(kw in page.url for kw in ("checkpoint", "challenge", "authwall", "/login")):
                    logger.error("LinkedIn security challenge — aborting reply")
                    return False

                time.sleep(random.uniform(3, 8))

                # Find and click Reply on the comment
                replied = page.evaluate("""
                    (commenter) => {
                        const comments = document.querySelectorAll('[class*="comment"] [class*="actor-name"], .comments-comment-item .comments-post-meta__name-text');
                        for (const el of comments) {
                            if (el.innerText.includes(commenter)) {
                                const item = el.closest('[class*="comment-item"], .comments-comment-item');
                                if (!item) continue;
                                const replyBtn = item.querySelector('[class*="reply-button"], button[aria-label*="Reply"]');
                                if (replyBtn) { replyBtn.click(); return true; }
                            }
                        }
                        return false;
                    }
                """, commenter)

                if not replied:
                    logger.warning("Could not find reply button for commenter: %s", commenter)

                time.sleep(random.uniform(3, 6))

                # Type reply in the active comment input
                for sel in ['[class*="comments-comment-box"] [role="textbox"]',
                            '.ql-editor', '[contenteditable="true"]']:
                    try:
                        el = page.wait_for_selector(sel, timeout=5000)
                        if el:
                            el.click()
                            time.sleep(1)
                            page.keyboard.type(reply_body, delay=40)
                            break
                    except Exception:
                        continue

                time.sleep(random.uniform(1, 2))

                # Submit
                submitted = False
                for sel in ['button[class*="submit"], button[aria-label*="Post"], '
                            'button[class*="comments-comment-box__submit-button"]']:
                    try:
                        btn = page.wait_for_selector(sel, timeout=3000)
                        if btn:
                            btn.click()
                            submitted = True
                            break
                    except Exception:
                        continue
                if not submitted:
                    page.keyboard.press("Control+Return")

                time.sleep(2)
                logger.info("Reply submitted successfully")
                return True
            except Exception as e:
                logger.error("Reply execution error: %s", e)
                return False
            finally:
                browser.close()
