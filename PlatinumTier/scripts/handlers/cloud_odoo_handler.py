import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import OdooConnectionError
from PlatinumTier.scripts.odoo_client import connect
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)

APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))


def handle(task_path: Path, vault_path: Path) -> bool:
    """
    Create a draft Odoo invoice and write an approval file to Pending_Approval/.
    Cloud Agent NEVER posts/confirms invoices — that is Local-only (FR-004).
    """
    try:
        models, uid, db, password = connect()
    except OdooConnectionError as e:
        logger.error("Odoo unreachable — keeping task in Needs_Action/: %s", e)
        log_action(vault_path, "odoo_connect_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        # Move back to Needs_Action/ so it will be retried
        move_task(task_path, vault_path / "Needs_Action")
        return False

    try:
        fm = read_frontmatter(task_path)
        partner_id = int(fm.get("odoo_partner_id", 1))
        amount = float(fm.get("odoo_amount", 0.0))
        ref = fm.get("odoo_ref", task_path.stem)

        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "ref": ref,
            "invoice_line_ids": [(0, 0, {
                "name": fm.get("odoo_description", "Service"),
                "quantity": 1,
                "price_unit": amount,
            })],
        }
        invoice_id = models.execute_kw(
            db, uid, password,
            "account.move", "create", [invoice_vals]
        )
        logger.info("Odoo draft invoice created: id=%d", invoice_id)

        # Update task frontmatter with Odoo record ID
        update_frontmatter(task_path, {
            "odoo_invoice_id": invoice_id,
            "odoo_status": "draft",
            "status": "pending_approval",
        })

        # Write approval file
        expires = datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        approval_name = f"APPROVE_POST_INVOICE_{ref}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        approval_fm = {
            "type": "odoo_invoice",
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires": expires.isoformat(),
            "claimed_by": "cloud",
            "approved_by": "",
            "approved_at": "",
            "odoo_task_file": task_path.name,
            "odoo_invoice_id": invoice_id,
            "odoo_partner_name": fm.get("odoo_partner_name", str(partner_id)),
            "odoo_amount": amount,
        }
        approval_content = _build_approval_md(approval_fm, ref, amount, expires)
        approval_path.write_text(approval_content, encoding="utf-8")

        move_task(task_path, vault_path / "Plans")

        log_action(vault_path, "odoo_draft_created", "cloud", approval_name,
                   parameters={"invoice_id": invoice_id, "amount": amount, "ref": ref})
        return True

    except Exception as e:
        logger.error("cloud_odoo_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "odoo_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _build_approval_md(fm: dict, ref: str, amount: float, expires: datetime) -> str:
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    return (
        f"---\n{header}---\n\n"
        f"## Action Required\n\n"
        f"Post/confirm Odoo invoice **{ref}** for **{fm['odoo_partner_name']}** — amount: **{amount}**\n\n"
        f"**Expires**: by {expires.isoformat()}\n\n"
        f"---\n\n"
        f"## Invoice Details\n\n"
        f"- Invoice ID: {fm['odoo_invoice_id']}\n"
        f"- Partner: {fm['odoo_partner_name']}\n"
        f"- Amount: {amount}\n"
        f"- Reference: {ref}\n\n"
        f"---\n\n"
        f"## How to Approve\n\n"
        f"Drag this file to `Approved/` to confirm the invoice in Odoo.\n"
        f"Drag to `Rejected/` to leave as draft.\n"
    )
