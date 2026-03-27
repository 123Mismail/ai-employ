"""
Drop a sample task into Needs_Action/ for local testing.

Usage:
    python -m PlatinumTier.tests.drop_task --type email
    python -m PlatinumTier.tests.drop_task --type social
    python -m PlatinumTier.tests.drop_task --type odoo
    python -m PlatinumTier.tests.drop_task --type whatsapp
    python -m PlatinumTier.tests.drop_task --type stale   (for stale recovery test)
    python -m PlatinumTier.tests.drop_task --type all     (drop all types)
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./test_vault")).resolve()
TS = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
NOW_ISO = datetime.now(timezone.utc).isoformat()


def _write_task(name: str, frontmatter: dict, body: str) -> Path:
    folder = VAULT_PATH / "Needs_Action"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    header = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    path.write_text(f"---\n{header}---\n\n{body}\n", encoding="utf-8")
    print(f"  Dropped: {path}")
    return path


def drop_email():
    msg_id = f"test{TS[:8]}"
    return _write_task(
        f"EMAIL_{msg_id}_{TS}.md",
        {
            "type": "email",
            "source": "Gmail",
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "agent_version": "1.0.0",
            "timestamp": NOW_ISO,
            "stale_recovery_count": 0,
            "email_msg_id": msg_id,
            "email_from": "client@example.com",
            "email_subject": "Invoice Question",
        },
        "Hi, I wanted to follow up on the invoice we discussed last week. "
        "Could you please confirm the total amount and payment terms? Thanks!",
    )


def drop_social():
    return _write_task(
        f"TASK_AUTO_POST_LINKEDIN_{TS}.md",
        {
            "type": "proactive_task",
            "source": "Proactive",
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "agent_version": "1.0.0",
            "timestamp": NOW_ISO,
            "stale_recovery_count": 0,
            "social_target": "linkedin",
        },
        "Context: Share a weekly update about the AI Employee product progress.",
    )


def drop_odoo():
    return _write_task(
        f"ODOO_INVOICE_TEST001_{TS}.md",
        {
            "type": "odoo_invoice",
            "source": "Proactive",
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "agent_version": "1.0.0",
            "timestamp": NOW_ISO,
            "stale_recovery_count": 0,
            "odoo_partner_id": 1,
            "odoo_partner_name": "Test Client",
            "odoo_amount": 1500.0,
            "odoo_description": "AI Employee Setup Fee",
            "odoo_ref": "TEST001",
        },
        "Invoice for AI Employee setup services delivered in March 2026.",
    )


def drop_whatsapp():
    return _write_task(
        f"WHATSAPP_OWNER_{TS}.md",
        {
            "type": "whatsapp",
            "source": "WhatsApp",
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "agent_version": "1.0.0",
            "timestamp": NOW_ISO,
            "stale_recovery_count": 0,
            "whatsapp_from": "+1234567890",
            "whatsapp_contact": "Test Contact",
        },
        "Hey, are you available for a quick call tomorrow at 3pm?",
    )


def drop_stale():
    """Drop a task with claimed_at 35 minutes ago to trigger stale recovery."""
    from datetime import timedelta
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=35)).isoformat()
    folder = VAULT_PATH / "In_Progress" / "cloud"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"EMAIL_stale_{TS}.md"
    fm = {
        "type": "email",
        "source": "Gmail",
        "status": "in_progress",
        "claimed_by": "cloud",
        "claimed_at": old_ts,
        "agent_version": "1.0.0",
        "timestamp": old_ts,
        "stale_recovery_count": 0,
        "email_msg_id": "stale001",
        "email_from": "stale@example.com",
        "email_subject": "Stale Test",
    }
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    path.write_text(f"---\n{header}---\n\nThis task was intentionally left stale.\n", encoding="utf-8")
    print(f"  Dropped stale task: {path}")
    print(f"  claimed_at set to 35 min ago — reaper should recover within 5 min")
    return path


DROPPERS = {
    "email": drop_email,
    "social": drop_social,
    "odoo": drop_odoo,
    "whatsapp": drop_whatsapp,
    "stale": drop_stale,
}


def main():
    parser = argparse.ArgumentParser(description="Drop test tasks into the vault")
    parser.add_argument(
        "--type",
        choices=[*DROPPERS.keys(), "all"],
        default="email",
        help="Type of task to drop",
    )
    args = parser.parse_args()

    print(f"\nDropping task(s) into: {VAULT_PATH / 'Needs_Action'}\n")

    if args.type == "all":
        for name, fn in DROPPERS.items():
            if name != "stale":
                fn()
    else:
        DROPPERS[args.type]()

    print("\nDone. Watch the agent logs to see processing.")
    print("To approve: move APPROVE_*.md from Pending_Approval/ → Approved/")


if __name__ == "__main__":
    main()
