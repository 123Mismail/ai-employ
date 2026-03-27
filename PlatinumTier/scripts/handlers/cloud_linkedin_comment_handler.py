import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

_BANNED_PHRASES = ["Great post!", "So true!", "Love this!", "Amazing!", "Totally agree!", "Couldn't agree more!"]


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    try:
        fm = read_frontmatter(task_path)
        post_url = fm.get("post_url", "")
        post_author = fm.get("post_author", "")
        post_snippet = fm.get("post_snippet", "")

        if not post_url or not post_snippet:
            raise ValueError("linkedin_comment task missing post_url or post_snippet")

        goals = _read_goals(vault_path)
        comment = _draft_comment(openai_client, post_author, post_snippet, goals)

        now = datetime.now()
        ts = now.strftime("%Y%m%d%H%M%S")
        ts_display = now.strftime("%Y-%m-%d %H:%M")
        expires_display = (now + timedelta(hours=APPROVAL_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M")
        safe_id = post_url.replace("https://", "").replace("/", "_").replace(":", "_")[-25:]
        approval_name = f"APPROVE_COMMENT_LINKEDIN_{safe_id}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        content = f"""---
type: linkedin_comment_approval
status: pending_approval
created_at: "{ts_display}"
expires: "{expires_display}"
claimed_by: cloud
approved_by: ""
approved_at: ""
post_url: "{post_url}"
post_author: "{post_author}"
comment_body: "{comment.replace('"', "'")}"
---

# LinkedIn Comment — {ts_display}

## Action Required

Post a comment on **{post_author}**'s LinkedIn post.

**Expires**: {expires_display}

---

## Their Post
> {post_snippet[:300]}

---

## Drafted Comment

{comment}

---

## How to Approve

Drag this file to `Approved/` in Obsidian to post the comment.
Drag to `Rejected/` to discard.
"""
        approval_path.write_text(content, encoding="utf-8")
        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")
        log_action(vault_path, "linkedin_comment_draft_created", "cloud", approval_name,
                   parameters={"post_author": post_author, "post_url": post_url})
        logger.info("Comment approval written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_linkedin_comment_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "linkedin_comment_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _draft_comment(openai_client, post_author: str, post_snippet: str, goals: str) -> str:
    if DRY_RUN:
        return f"[DRY_RUN] Interesting perspective on {post_snippet[:40]}..."
    banned = ", ".join(f'"{p}"' for p in _BANNED_PHRASES)
    prompt = (
        f"You are building personal brand authority in AI agents, autonomous systems, and Digital FTEs.\n\n"
        f"Brand context:\n{goals[:500]}\n\n"
        f"Write a LinkedIn comment on this post by {post_author}:\n\"{post_snippet}\"\n\n"
        f"Rules:\n"
        f"- Be specific to the post content — reference actual ideas from it\n"
        f"- Add your own insight or a relevant perspective from AI agents/Digital FTE space\n"
        f"- 2-4 sentences max\n"
        f"- Never use these banned phrases: {banned}\n"
        f"- No emojis\n"
        f"- Write only the comment text, no labels"
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.75,
    )
    return response.choices[0].message.content.strip()


def _read_goals(vault_path: Path) -> str:
    goals_file = vault_path / "Business_Goals.md"
    if goals_file.exists():
        return goals_file.read_text(encoding="utf-8")[:800]
    return ""
