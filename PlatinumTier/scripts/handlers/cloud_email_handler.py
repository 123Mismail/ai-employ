import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)

APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    """
    Draft an email reply using OpenAI and write an approval file to Pending_Approval/.
    Moves task to Plans/ on success.
    Returns True on success, False on failure.
    """
    try:
        fm = read_frontmatter(task_path)
        body = _read_body(task_path)

        # Extract email metadata from frontmatter
        msg_id = fm.get("email_msg_id", "unknown")
        recipient = fm.get("email_from", "")
        subject = fm.get("email_subject", "")
        reply_to = f"RE: {subject}" if not subject.startswith("RE:") else subject

        # Draft reply with OpenAI
        draft = _draft_reply(openai_client, subject, body)

        # Detect invoice request and create odoo_invoice task
        invoice_data = _detect_invoice_request(openai_client, subject, body)
        if invoice_data:
            _create_invoice_task(vault_path, invoice_data, recipient)
            logger.info("invoice task created for email from %s", recipient)

        # Write approval file
        expires = datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        short_id = str(msg_id)[:8]
        approval_name = f"APPROVE_REPLY_EMAIL_{short_id}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        approval_fm = {
            "type": "email_approval",
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires": expires.isoformat(),
            "claimed_by": "cloud",
            "approved_by": "",
            "approved_at": "",
            "recipient": recipient,
            "subject": reply_to,
            "message_body": draft,
        }
        approval_content = _build_approval_md(approval_fm, subject, draft)
        approval_path.write_text(approval_content, encoding="utf-8")

        # Move task to Plans/
        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")

        log_action(
            vault_path,
            action_type="email_draft_created",
            actor="cloud",
            target=approval_name,
            parameters={"msg_id": msg_id, "recipient": recipient},
        )
        logger.info("approval file written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_email_handler failed for %s: %s", task_path.name, e)
        log_action(
            vault_path,
            action_type="email_draft_failed",
            actor="cloud",
            target=task_path.name,
            result="error",
            parameters={"error": str(e)},
        )
        return False


def _draft_reply(openai_client, subject: str, body: str) -> str:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        return (
            f"[DRY_RUN DRAFT] Thank you for your email regarding '{subject}'. "
            "I have received your message and will follow up shortly.\n\n"
            "Best regards"
        )
    prompt = (
        f"You are a professional email assistant. Draft a concise, polite reply "
        f"to the following email.\n\nSubject: {subject}\n\nEmail body:\n{body}\n\n"
        f"Write only the reply body text, no subject line, no greeting prefix."
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


def _detect_invoice_request(openai_client, subject: str, body: str) -> dict | None:
    """Use OpenAI to detect if email is requesting an invoice. Returns invoice data or None."""
    if os.getenv("DRY_RUN", "false").lower() == "true":
        return None
    prompt = (
        "Analyze this email and determine if the sender is requesting an invoice to be created.\n"
        f"Subject: {subject}\nBody: {body}\n\n"
        "If it IS an invoice request, reply with JSON only:\n"
        '{"is_invoice": true, "client_name": "...", "amount": 0.0, "description": "..."}\n'
        "If it is NOT an invoice request, reply with JSON only:\n"
        '{"is_invoice": false}'
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.1,
    )
    import json
    try:
        data = json.loads(response.choices[0].message.content.strip())
        return data if data.get("is_invoice") else None
    except Exception:
        return None


def _create_invoice_task(vault_path: Path, invoice_data: dict, sender_email: str) -> None:
    """Write an odoo_invoice task file to Needs_Action/."""
    import yaml
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"INVOICE_REQUEST_{ts}.md"
    fm = {
        "type": "odoo_invoice",
        "status": "pending",
        "odoo_partner_name": invoice_data.get("client_name", sender_email),
        "odoo_amount": float(invoice_data.get("amount", 0.0)),
        "odoo_description": invoice_data.get("description", "Service"),
        "odoo_ref": f"INV-{ts}",
        "source_email": sender_email,
    }
    content = f"---\n{yaml.dump(fm, default_flow_style=False, allow_unicode=True)}---\n\n{invoice_data.get('description', 'Invoice request from email')}\n"
    (vault_path / "Needs_Action" / filename).write_text(content, encoding="utf-8")


def _read_body(task_path: Path) -> str:
    text = task_path.read_text(encoding="utf-8")
    # Strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else text
    return text


def _build_approval_md(fm: dict, original_subject: str, draft: str) -> str:
    import yaml
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    expires_human = fm.get("expires", "")
    return (
        f"---\n{header}---\n\n"
        f"## Action Required\n\n"
        f"Send the drafted reply to **{fm['recipient']}** re: _{original_subject}_\n\n"
        f"**Expires**: by {expires_human}\n\n"
        f"---\n\n"
        f"## Draft Reply\n\n"
        f"{draft}\n\n"
        f"---\n\n"
        f"## How to Approve\n\n"
        f"Drag this file to `Approved/` in Obsidian to send the reply.\n"
        f"Drag to `Rejected/` to discard.\n"
    )
