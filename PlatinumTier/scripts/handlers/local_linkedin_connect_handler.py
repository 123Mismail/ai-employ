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
MIN_CONNECT_DELAY = 30  # seconds — LinkedIn minimum wait before connect action


def execute(approval_path: Path, vault_path: Path) -> bool:
    try:
        fm = read_frontmatter(approval_path)
        profile_url = fm.get("profile_url", "")
        candidate_name = fm.get("candidate_name", "")
        connection_note = fm.get("connection_note", "")

        if not profile_url or not connection_note:
            raise ValueError("approval missing profile_url or connection_note")

        rl = RateLimiter()
        if not rl.can_execute("connect"):
            logger.info("Daily connection limit reached — leaving in Approved/ for tomorrow")
            return False  # Leave in Approved/ — auto-executes next day

        # Claim before execute
        in_progress_dir = vault_path / "In_Progress" / "local"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        claimed_path = in_progress_dir / approval_path.name
        move_task(approval_path, in_progress_dir)

        if DRY_RUN:
            logger.info("[DRY_RUN] would connect with %s at %s", candidate_name, profile_url)
            success = True
        else:
            success = _execute_connect(profile_url, candidate_name, connection_note)

        if success:
            rl.record_action("connect")
            update_frontmatter(claimed_path, {
                "status": "approved", "approved_by": "human",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            })
            move_task(claimed_path, vault_path / "Done")
            log_action(vault_path, "linkedin_connect_sent", "local", approval_path.name,
                       parameters={"candidate": candidate_name, "profile_url": profile_url, "dry_run": DRY_RUN},
                       approval_status="approved", approved_by="human")
            logger.info("Connection request sent to %s (dry_run=%s)", candidate_name, DRY_RUN)
        else:
            move_task(claimed_path, vault_path / "Rejected")
            log_action(vault_path, "linkedin_connect_failed", "local", approval_path.name,
                       result="error", parameters={"candidate": candidate_name})
        return success

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_linkedin_connect_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "linkedin_connect_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _execute_connect(profile_url: str, candidate_name: str, connection_note: str) -> bool:
    from playwright.sync_api import sync_playwright
    from pathlib import Path as _Path
    REPO_ROOT = _Path(__file__).resolve().parents[4]
    session_path = REPO_ROOT / "linkedin_session"

    with SessionLock(holder="local-linkedin-connect"):
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            try:
                page = browser.new_page()
                page.goto(profile_url, timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)

                if any(kw in page.url for kw in ("checkpoint", "challenge", "authwall", "/login")):
                    logger.error("LinkedIn security challenge — aborting connect")
                    return False

                # Mandatory minimum wait before connecting (spec FR-005)
                logger.info("Waiting %ds before connect action...", MIN_CONNECT_DELAY)
                time.sleep(MIN_CONNECT_DELAY + random.uniform(0, 10))

                # Click Connect button
                connected = False
                for sel in ['button[aria-label*="Connect"]', 'button:has-text("Connect")',
                            '[data-control-name="connect"]']:
                    try:
                        btn = page.wait_for_selector(sel, timeout=5000)
                        if btn:
                            btn.scroll_into_view_if_needed()
                            btn.click()
                            connected = True
                            break
                    except Exception:
                        continue

                if not connected:
                    logger.warning("Could not find Connect button on profile: %s", profile_url)
                    return False

                time.sleep(random.uniform(2, 4))

                # Click "Add a note"
                for sel in ['button[aria-label*="Add a note"]', 'button:has-text("Add a note")']:
                    try:
                        btn = page.wait_for_selector(sel, timeout=5000)
                        if btn:
                            btn.click()
                            break
                    except Exception:
                        continue

                time.sleep(random.uniform(1, 3))

                # Type the personalised note
                for sel in ['textarea[name="message"]', 'textarea[id*="custom-message"]',
                            'textarea[placeholder*="personalize"]', 'textarea']:
                    try:
                        el = page.wait_for_selector(sel, timeout=5000)
                        if el:
                            el.click()
                            time.sleep(1)
                            page.keyboard.type(connection_note, delay=40)
                            break
                    except Exception:
                        continue

                time.sleep(random.uniform(1, 2))

                # Send the request
                for sel in ['button[aria-label*="Send"]', 'button:has-text("Send")',
                            'button[aria-label*="Send invitation"]']:
                    try:
                        btn = page.wait_for_selector(sel, timeout=5000)
                        if btn:
                            btn.click()
                            break
                    except Exception:
                        continue

                time.sleep(2)
                logger.info("Connection request sent to: %s", candidate_name)
                return True
            except Exception as e:
                logger.error("Connect execution error: %s", e)
                return False
            finally:
                browser.close()
