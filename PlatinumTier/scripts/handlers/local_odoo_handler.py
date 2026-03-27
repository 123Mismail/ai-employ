import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError, OdooConnectionError
from PlatinumTier.scripts.odoo_client import connect
from PlatinumTier.scripts.task_manager import list_tasks, move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def execute(approval_path: Path, vault_path: Path) -> bool:
    try:
        fm = read_frontmatter(approval_path)
        invoice_id = fm.get("odoo_invoice_id")
        if not invoice_id:
            raise ValueError("approval missing 'odoo_invoice_id'")

        if DRY_RUN:
            logger.info("[DRY_RUN] would post Odoo invoice id=%s", invoice_id)
        else:
            models, uid, db, password = connect()
            models.execute_kw(
                db, uid, password,
                "account.move", "action_post", [[int(invoice_id)]]
            )
            logger.info("Odoo invoice %s posted", invoice_id)

        # Update approval
        update_frontmatter(approval_path, {
            "status": "approved",
            "approved_by": "human",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        })
        move_task(approval_path, vault_path / "Done")

        # Update linked task
        task_file = fm.get("odoo_task_file", "")
        _close_linked_task(task_file, vault_path, invoice_id)

        log_action(vault_path, "odoo_invoice_posted", "local", approval_path.name,
                   parameters={"invoice_id": invoice_id, "dry_run": DRY_RUN},
                   approval_status="approved", approved_by="human")
        return True

    except (ApprovalExpiredError, OdooConnectionError):
        raise
    except Exception as e:
        logger.error("local_odoo_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "odoo_invoice_post_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _close_linked_task(task_file: str, vault_path: Path, invoice_id) -> None:
    if not task_file:
        return
    for folder in (vault_path / "Plans", vault_path / "In_Progress" / "cloud"):
        candidate = folder / task_file
        if candidate.exists():
            update_frontmatter(candidate, {"odoo_status": "posted", "status": "done"})
            move_task(candidate, vault_path / "Done")
            logger.info("closed linked Odoo task: %s", task_file)
            return
