import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    try:
        fm = read_frontmatter(task_path)
        nid = fm.get("notification_id", "")
        commenter = fm.get("commenter_name", "")
        snippet = fm.get("comment_snippet", "")
        post_url = fm.get("post_url", "")

        if not commenter or not post_url:
            raise ValueError("linkedin_reply task missing commenter_name or post_url")

        goals = _read_goals(vault_path)
        reply = _draft_reply(openai_client, commenter, snippet, goals)

        now = datetime.now()
        ts = now.strftime("%Y%m%d%H%M%S")
        ts_display = now.strftime("%Y-%m-%d %H:%M")
        expires_display = (now + timedelta(hours=APPROVAL_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M")
        safe_nid = (nid or ts).replace(":", "_").replace("/", "_")[:30]
        approval_name = f"APPROVE_REPLY_LINKEDIN_{safe_nid}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        content = f"""---
type: linkedin_reply_approval
status: pending_approval
created_at: "{ts_display}"
expires: "{expires_display}"
claimed_by: cloud
approved_by: ""
approved_at: ""
notification_id: "{nid}"
post_url: "{post_url}"
commenter_name: "{commenter}"
reply_body: "{reply.replace('"', "'")}"
---

# LinkedIn Reply — {ts_display}

## Action Required

Reply to **{commenter}**'s comment on your post.

**Expires**: {expires_display}

---

## Their Comment
> {snippet}

---

## Drafted Reply

{reply}

---

## How to Approve

Drag this file to `Approved/` in Obsidian to post the reply.
Drag to `Rejected/` to discard.
"""
        approval_path.write_text(content, encoding="utf-8")
        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")
        log_action(vault_path, "linkedin_reply_draft_created", "cloud", approval_name,
                   parameters={"commenter": commenter, "post_url": post_url})
        logger.info("Reply approval written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_linkedin_reply_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "linkedin_reply_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _draft_reply(openai_client, commenter: str, snippet: str, goals: str) -> str:
    if DRY_RUN:
        return f"[DRY_RUN] Thank you {commenter} — great point! {snippet[:30]}..."
    prompt = (
        f"You are building personal brand authority in AI agents, autonomous systems, and Digital FTEs.\n\n"
        f"Brand context:\n{goals[:500]}\n\n"
        f"Someone named {commenter} commented on your LinkedIn post:\n\"{snippet}\"\n\n"
        f"Write a genuine, specific reply (2-4 sentences). Reference their comment directly. "
        f"Be insightful, not generic. No emojis. No 'Great comment!' openers."
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _read_goals(vault_path: Path) -> str:
    goals_file = vault_path / "Business_Goals.md"
    if goals_file.exists():
        return goals_file.read_text(encoding="utf-8")[:800]
    return ""
