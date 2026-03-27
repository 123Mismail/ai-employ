"""
Platinum Tier — Local Agent
Runs on the owner's machine. Processes approvals, executes all send/post/pay actions.
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from PlatinumTier.scripts import health_writer, vault_sync
from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError
from PlatinumTier.scripts.handlers import (
    local_email_handler,
    local_linkedin_comment_handler,
    local_linkedin_connect_handler,
    local_linkedin_reply_handler,
    local_odoo_handler,
    local_social_handler,
    local_whatsapp_handler,
)
from PlatinumTier.scripts.stale_reaper import start_reaper_thread
from PlatinumTier.scripts.task_manager import (
    ensure_vault_structure,
    list_tasks,
    move_task,
    read_frontmatter,
    update_frontmatter,
)

load_dotenv(os.getenv("ENV_FILE", ".env"))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [local] %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.environ["VAULT_PATH"])
AGENT_ROLE = "local"
APPROVAL_POLL_INTERVAL = int(os.getenv("APPROVAL_POLL_INTERVAL", "10"))
STALE_TIMEOUT = int(os.getenv("STALE_TASK_TIMEOUT_MINUTES", "30"))
SYNC_INTERVAL = int(os.getenv("VAULT_SYNC_INTERVAL", "60"))


def _build_gmail_service():
    """Returns None in DRY_RUN mode — email handler checks before calling send."""
    if os.getenv("DRY_RUN", "false").lower() == "true":
        logger.info("[DRY_RUN] Gmail service skipped — using mock")
        return None
    token_path = os.getenv("GMAIL_TOKEN_PATH", "")
    if not token_path or not Path(token_path).exists():
        logger.warning("GMAIL_TOKEN_PATH not set or missing — email send will fail")
        return None
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(token_path)
    return build("gmail", "v1", credentials=creds)


def _check_expiry(approval_path: Path) -> None:
    fm = read_frontmatter(approval_path)
    expires_raw = fm.get("expires", "")
    if not expires_raw:
        return
    expires = datetime.fromisoformat(str(expires_raw))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        update_frontmatter(approval_path, {"status": "rejected", "approved_by": "system"})
        move_task(approval_path, VAULT_PATH / "Rejected")
        log_action(VAULT_PATH, "approval_expired", "local", approval_path.name,
                   result="rejected", approval_status="expired")
        raise ApprovalExpiredError(f"{approval_path.name} expired")


def _dispatch_approval(approval_path: Path, gmail_service) -> bool:
    fm = read_frontmatter(approval_path)
    approval_type = fm.get("type", "")

    if approval_type == "email_approval":
        return local_email_handler.execute(approval_path, VAULT_PATH, gmail_service)
    elif approval_type in ("linkedin_post", "x_post", "facebook_post", "social_post"):
        return local_social_handler.execute(approval_path, VAULT_PATH)
    elif approval_type == "whatsapp_reply":
        return local_whatsapp_handler.execute(approval_path, VAULT_PATH)
    elif approval_type == "odoo_invoice":
        return local_odoo_handler.execute(approval_path, VAULT_PATH)
    elif approval_type == "linkedin_reply_approval":
        return local_linkedin_reply_handler.execute(approval_path, VAULT_PATH)
    elif approval_type == "linkedin_comment_approval":
        return local_linkedin_comment_handler.execute(approval_path, VAULT_PATH)
    elif approval_type == "linkedin_connect_approval":
        return local_linkedin_connect_handler.execute(approval_path, VAULT_PATH)
    else:
        logger.warning("unknown approval type '%s' in %s", approval_type, approval_path.name)
        return False


def run() -> None:
    logger.info("Local Agent starting — vault: %s", VAULT_PATH)

    try:
        vault_sync.pull_rebase(VAULT_PATH)
    except Exception as e:
        logger.warning("startup pull failed (continuing on local vault): %s", e)

    ensure_vault_structure(VAULT_PATH)
    vault_sync.ensure_hooks_active(VAULT_PATH)

    # Log counts of any in-progress tasks from before restart (do not reap — reaper handles it)
    cloud_in_progress = list_tasks(VAULT_PATH / "In_Progress" / "cloud")
    local_in_progress = list_tasks(VAULT_PATH / "In_Progress" / "local")
    if cloud_in_progress or local_in_progress:
        logger.info(
            "startup: found %d cloud + %d local in-progress tasks (reaper will recover stale ones)",
            len(cloud_in_progress), len(local_in_progress),
        )

    start_reaper_thread(VAULT_PATH, STALE_TIMEOUT)
    health_writer.start_health_thread(VAULT_PATH, AGENT_ROLE)
    vault_sync.start_sync_loop(VAULT_PATH, SYNC_INTERVAL)

    gmail_service = _build_gmail_service()
    health_writer.write_health(VAULT_PATH, AGENT_ROLE, status="running")
    logger.info("Local Agent ready — polling Approved/ every %ds", APPROVAL_POLL_INTERVAL)

    while True:
        approvals = list_tasks(VAULT_PATH / "Approved")

        for approval_path in approvals:
            if not approval_path.exists():
                logger.warning("approval file vanished, skipping: %s", approval_path.name)
                continue
            try:
                _check_expiry(approval_path)
            except ApprovalExpiredError:
                logger.warning("skipping expired approval: %s", approval_path.name)
                try:
                    vault_sync.push(VAULT_PATH, f"local: expired {approval_path.name}")
                except Exception:
                    pass
                continue
            except Exception as e:
                logger.warning("could not read approval %s: %s — skipping", approval_path.name, e)
                continue

            success = _dispatch_approval(approval_path, gmail_service)

            try:
                vault_sync.push(VAULT_PATH, f"local: executed {approval_path.name}")
            except Exception as e:
                logger.error("vault push failed after executing %s: %s", approval_path.name, e)

            health_writer.write_health(
                VAULT_PATH, AGENT_ROLE,
                last_task=approval_path.name,
                status="running" if success else "degraded",
            )

        time.sleep(APPROVAL_POLL_INTERVAL)


if __name__ == "__main__":
    run()
