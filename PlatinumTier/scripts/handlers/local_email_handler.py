import base64
import logging
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError
from PlatinumTier.scripts.task_manager import list_tasks, move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def execute(approval_path: Path, vault_path: Path, gmail_service) -> bool:
    """
    Send the drafted email reply after human approval.
    Moves approval to Done/ on success.
    Returns True on success, False on failure.
    """
    try:
        fm = read_frontmatter(approval_path)

        # Expiry check (FR-011)
        expires_raw = fm.get("expires", "")
        if expires_raw:
            expires = datetime.fromisoformat(str(expires_raw))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                logger.warning("approval expired: %s", approval_path.name)
                update_frontmatter(approval_path, {"status": "rejected", "approved_by": "system"})
                move_task(approval_path, vault_path / "Rejected")
                log_action(vault_path, "email_approval_expired", "local", approval_path.name,
                           result="rejected", approval_status="expired")
                raise ApprovalExpiredError(f"{approval_path.name} expired at {expires_raw}")

        recipient = fm.get("recipient", "")
        subject = fm.get("subject", "")
        body = fm.get("message_body", "")

        if not recipient:
            raise ValueError("approval file missing 'recipient' field")

        # Claim the file immediately — moves out of Approved/ so it won't retry on failure
        in_progress_dir = vault_path / "In_Progress" / "local"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        claimed_path = in_progress_dir / approval_path.name
        move_task(approval_path, in_progress_dir)

        if DRY_RUN or gmail_service is None:
            logger.info("[DRY_RUN] would send email to %s — subject: %s", recipient, subject)
        else:
            _send_gmail(gmail_service, recipient, subject, body)

        # Move approval to Done/
        update_frontmatter(claimed_path, {
            "status": "approved",
            "approved_by": "human",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        })
        move_task(claimed_path, vault_path / "Done")

        # Move linked task from Plans/ to Done/
        _close_linked_task(claimed_path.name, vault_path)

        log_action(
            vault_path,
            action_type="email_sent",
            actor="local",
            target=approval_path.name,
            parameters={"recipient": recipient, "subject": subject, "dry_run": DRY_RUN},
            approval_status="approved",
            approved_by="human",
        )
        logger.info("email sent to %s (dry_run=%s)", recipient, DRY_RUN)
        return True

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_email_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "email_send_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _send_gmail(gmail_service, to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()


def _close_linked_task(approval_name: str, vault_path: Path) -> None:
    # Extract msg_id fragment from approval filename and find matching task in Plans/
    # APPROVE_REPLY_EMAIL_<short_id>_<ts>.md → look for EMAIL_<...>_*.md in Plans/
    try:
        parts = approval_name.replace(".md", "").split("_")
        # parts: ['APPROVE', 'REPLY', 'EMAIL', short_id, ts]
        if len(parts) >= 4:
            short_id = parts[3]
            for task_path in list_tasks(vault_path / "Plans"):
                if short_id in task_path.name:
                    update_frontmatter(task_path, {"status": "done"})
                    move_task(task_path, vault_path / "Done")
                    logger.info("closed linked task: %s", task_path.name)
                    return
    except Exception as e:
        logger.warning("could not close linked task: %s", e)
