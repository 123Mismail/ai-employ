import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def execute(approval_path: Path, vault_path: Path) -> bool:
    try:
        fm = read_frontmatter(approval_path)
        recipient = fm.get("recipient", "")
        body = fm.get("message_body", "")

        if not recipient or not body:
            raise ValueError("approval missing 'recipient' or 'message_body'")

        if DRY_RUN:
            logger.info("[DRY_RUN] would send WhatsApp to %s: %s...", recipient, body[:60])
            success = True
        else:
            success = _send_whatsapp(recipient, body, vault_path)

        if success:
            update_frontmatter(approval_path, {
                "status": "approved",
                "approved_by": "human",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            })
            move_task(approval_path, vault_path / "Done")
            log_action(vault_path, "whatsapp_sent", "local", approval_path.name,
                       parameters={"recipient": recipient, "dry_run": DRY_RUN},
                       approval_status="approved", approved_by="human")
        else:
            log_action(vault_path, "whatsapp_send_failed", "local", approval_path.name,
                       result="error")

        return success

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_whatsapp_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "whatsapp_send_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _send_whatsapp(recipient: str, body: str, vault_path: Path) -> bool:
    """Write a send-request to WhatsApp_Outbox/ — the watcher's browser picks it up.
    Avoids launching a second browser against the same locked session directory."""
    import json
    from datetime import datetime as _dt

    outbox_dir = vault_path / "WhatsApp_Outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.now().strftime("%Y%m%d%H%M%S%f")
    outbox_file = outbox_dir / f"SEND_{ts}.json"
    payload = {"recipient": recipient, "body": body, "created_at": _dt.utcnow().isoformat()}
    outbox_file.write_text(json.dumps(payload), encoding="utf-8")
    logger.info("Queued WhatsApp send -> %s (watcher will deliver)", outbox_file.name)
    return True
