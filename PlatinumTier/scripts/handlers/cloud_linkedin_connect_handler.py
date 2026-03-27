import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MAX_NOTE_CHARS = 300  # LinkedIn hard limit


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    try:
        fm = read_frontmatter(task_path)
        profile_url = fm.get("profile_url", "")
        candidate_name = fm.get("candidate_name", "")
        candidate_headline = fm.get("candidate_headline", "")
        candidate_company = fm.get("candidate_company", "")

        if not profile_url or not candidate_name:
            raise ValueError("linkedin_connect task missing profile_url or candidate_name")

        goals = _read_goals(vault_path)
        note = _draft_note(openai_client, candidate_name, candidate_headline, candidate_company, goals)
        # Enforce LinkedIn 300-char hard limit — truncate at last sentence boundary
        if len(note) > MAX_NOTE_CHARS:
            note = note[:MAX_NOTE_CHARS].rsplit(".", 1)[0] + "."

        now = datetime.now()
        ts = now.strftime("%Y%m%d%H%M%S")
        ts_display = now.strftime("%Y-%m-%d %H:%M")
        expires_display = (now + timedelta(hours=APPROVAL_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M")
        safe_id = profile_url.replace("https://www.linkedin.com/in/", "").replace("/", "")[:25]
        approval_name = f"APPROVE_CONNECT_LINKEDIN_{safe_id}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        content = f"""---
type: linkedin_connect_approval
status: pending_approval
created_at: "{ts_display}"
expires: "{expires_display}"
claimed_by: cloud
approved_by: ""
approved_at: ""
profile_url: "{profile_url}"
candidate_name: "{candidate_name}"
candidate_headline: "{candidate_headline}"
candidate_company: "{candidate_company}"
connection_note: "{note.replace('"', "'")}"
---

# LinkedIn Connection Request — {ts_display}

## Action Required

Send a connection request to **{candidate_name}**.

**Expires**: {expires_display}

---

## Candidate

- **Name**: {candidate_name}
- **Headline**: {candidate_headline}
- **Company**: {candidate_company}
- **Profile**: {profile_url}

---

## Connection Note ({len(note)}/300 chars)

{note}

---

## How to Approve

Drag this file to `Approved/` in Obsidian to send the connection request.
Drag to `Rejected/` to discard.
"""
        approval_path.write_text(content, encoding="utf-8")
        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")
        log_action(vault_path, "linkedin_connect_draft_created", "cloud", approval_name,
                   parameters={"candidate": candidate_name, "profile_url": profile_url})
        logger.info("Connect approval written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_linkedin_connect_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "linkedin_connect_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _draft_note(openai_client, name: str, headline: str, company: str, goals: str) -> str:
    if DRY_RUN:
        return f"[DRY_RUN] Hi {name} — your work at {company} on {headline[:30]} caught my attention."
    prompt = (
        f"Write a LinkedIn connection request note to {name}, who works as {headline} at {company}.\n\n"
        f"My brand context:\n{goals[:400]}\n\n"
        f"Rules:\n"
        f"- Reference their specific role or company — no generic messages\n"
        f"- Max 280 characters (strict — LinkedIn limit)\n"
        f"- Friendly, professional, genuine\n"
        f"- No 'I'd like to add you to my network' clichés\n"
        f"- Write only the note text, nothing else"
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


def _read_goals(vault_path: Path) -> str:
    goals_file = vault_path / "Business_Goals.md"
    if goals_file.exists():
        return goals_file.read_text(encoding="utf-8")[:800]
    return ""
