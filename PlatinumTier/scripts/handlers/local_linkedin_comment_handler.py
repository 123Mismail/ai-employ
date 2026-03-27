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
        post_author = fm.get("post_author", "")
        comment_body = fm.get("comment_body", "")

        if not post_url or not comment_body:
            raise ValueError("approval missing post_url or comment_body")

        rl = RateLimiter()
        if not rl.can_execute("comment"):
            logger.info("Daily comment limit reached — leaving in Approved/ for tomorrow")
            return False  # Leave in Approved/ — auto-executes next day when counter resets

        # Claim before execute
        in_progress_dir = vault_path / "In_Progress" / "local"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        claimed_path = in_progress_dir / approval_path.name
        move_task(approval_path, in_progress_dir)

        if DRY_RUN:
            logger.info("[DRY_RUN] would comment on %s's post: %s", post_author, post_url)
            success = True
        else:
            success = _execute_comment(post_url, comment_body)

        if success:
            rl.record_action("comment")
            update_frontmatter(claimed_path, {
                "status": "approved", "approved_by": "human",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            })
            move_task(claimed_path, vault_path / "Done")
            log_action(vault_path, "linkedin_comment_posted", "local", approval_path.name,
                       parameters={"post_author": post_author, "post_url": post_url, "dry_run": DRY_RUN},
                       approval_status="approved", approved_by="human")
            logger.info("Comment posted on %s's post (dry_run=%s)", post_author, DRY_RUN)
        else:
            move_task(claimed_path, vault_path / "Rejected")
            log_action(vault_path, "linkedin_comment_failed", "local", approval_path.name,
                       result="error", parameters={"post_url": post_url})
        return success

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_linkedin_comment_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "linkedin_comment_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _execute_comment(post_url: str, comment_body: str) -> bool:
    from playwright.sync_api import sync_playwright
    from pathlib import Path as _Path
    REPO_ROOT = _Path(__file__).resolve().parents[4]
    session_path = REPO_ROOT / "linkedin_session"

    with SessionLock(holder="local-linkedin-comment"):
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

                if any(kw in page.url for kw in ("checkpoint", "challenge", "authwall", "/login")):
                    logger.error("LinkedIn security challenge — aborting comment")
                    return False

                time.sleep(random.uniform(3, 8))

                # Click comment input
                for sel in ['[class*="comments-comment-box"] [role="textbox"]',
                            '.comments-comment-texteditor .ql-editor',
                            '[placeholder*="comment"], [aria-label*="comment"]',
                            '[contenteditable="true"]']:
                    try:
                        el = page.wait_for_selector(sel, timeout=5000)
                        if el:
                            el.scroll_into_view_if_needed()
                            el.click()
                            time.sleep(random.uniform(1, 2))
                            page.keyboard.type(comment_body, delay=40)
                            break
                    except Exception:
                        continue

                time.sleep(random.uniform(1, 2))

                # Submit
                submitted = False
                for sel in ['button[class*="submit"]', 'button[aria-label*="Post comment"]',
                            'button[class*="comments-comment-box__submit"]']:
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
                logger.info("Comment submitted successfully")
                return True
            except Exception as e:
                logger.error("Comment execution error: %s", e)
                return False
            finally:
                browser.close()
