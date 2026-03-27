import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)

APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    """
    Draft a WhatsApp reply using OpenAI and write an approval file to Pending_Approval/.
    Cloud Agent NEVER sends WhatsApp messages — Local Agent owns the session (FR-009).
    """
    try:
        fm = read_frontmatter(task_path)
        body = _read_body(task_path)

        recipient = fm.get("whatsapp_from", fm.get("from", ""))
        contact_name = fm.get("whatsapp_contact", fm.get("from", "Unknown"))

        draft = _draft_reply(openai_client, contact_name, body)

        now_local = datetime.now()
        now_utc = datetime.now(timezone.utc)
        expires = now_utc + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        ts_file = now_local.strftime("%Y-%m-%d_%H-%M")   # readable: 2026-03-25_19-52
        ts_display = now_local.strftime("%Y-%m-%d %H:%M")  # display: 2026-03-25 19:52
        approval_name = f"APPROVE_REPLY_WHATSAPP_{ts_file}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        approval_fm = {
            "type": "whatsapp_reply",
            "status": "pending_approval",
            "created_at": ts_display,
            "expires": (datetime.now() + timedelta(hours=APPROVAL_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M"),
            "claimed_by": "cloud",
            "approved_by": "",
            "approved_at": "",
            "recipient": recipient,
            "message_body": draft,
        }
        approval_content = _build_approval_md(approval_fm, contact_name, body, draft, ts_display)
        approval_path.write_text(approval_content, encoding="utf-8")

        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")

        log_action(vault_path, "whatsapp_draft_created", "cloud", approval_name,
                   parameters={"recipient": recipient, "contact": contact_name})
        logger.info("WhatsApp approval written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_whatsapp_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "whatsapp_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _draft_reply(openai_client, contact_name: str, message: str) -> str:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        return f"[DRY_RUN DRAFT] Hi {contact_name}, thanks for your message! I'll get back to you shortly."

    prompt = (
        f"You are a professional assistant. Draft a brief, friendly WhatsApp reply "
        f"to the following message from {contact_name}.\n\n"
        f"Message: {message}\n\n"
        f"Write only the reply text. Keep it short (1-3 sentences), conversational, no emojis."
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def _read_body(task_path: Path) -> str:
    text = task_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else text
    return text


def _build_approval_md(fm: dict, contact: str, original: str, draft: str, ts_display: str) -> str:
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    expires_display = fm["expires"]
    return (
        f"---\n{header}---\n\n"
        f"# WhatsApp Reply — {ts_display}\n\n"
        f"**To:** {contact}  |  **Received:** {ts_display}  |  **Expires:** {expires_display}\n\n"
        f"---\n\n"
        f"## Original Message\n\n"
        f"> {original}\n\n"
        f"---\n\n"
        f"## Draft Reply\n\n"
        f"{draft}\n\n"
        f"---\n\n"
        f"**Approve:** drag to `Approved/`  |  **Reject:** drag to `Rejected/`\n"
    )
