import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)

APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))
PLATFORMS = ("linkedin", "x", "facebook")


def handle(task_path: Path, vault_path: Path, openai_client) -> bool:
    """
    Draft a social post using OpenAI and write an approval file to Pending_Approval/.
    Reads Business_Goals.md for context.
    """
    try:
        fm = read_frontmatter(task_path)
        goals = _read_business_goals(vault_path)
        task_body = _read_body(task_path)

        # Determine target platform(s) from task frontmatter
        target = fm.get("social_target", "linkedin")
        draft = _draft_post(openai_client, target, goals, task_body)

        expires = datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        approval_name = f"APPROVE_POST_{target.upper()}_{date_str}_{ts}.md"
        approval_path = vault_path / "Pending_Approval" / approval_name

        approval_fm = {
            "type": f"{target}_post",
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires": expires.isoformat(),
            "claimed_by": "cloud",
            "approved_by": "",
            "approved_at": "",
            "target": target,
            "post_content": draft,
            "image_url": fm.get("image_url", ""),
        }
        approval_content = _build_approval_md(approval_fm, target, draft, expires)
        approval_path.write_text(approval_content, encoding="utf-8")

        update_frontmatter(task_path, {"status": "pending_approval"})
        move_task(task_path, vault_path / "Plans")

        log_action(vault_path, "social_draft_created", "cloud", approval_name,
                   parameters={"target": target})
        logger.info("social approval written: %s", approval_name)
        return True

    except Exception as e:
        logger.error("cloud_social_handler failed for %s: %s", task_path.name, e)
        log_action(vault_path, "social_draft_failed", "cloud", task_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _draft_post(openai_client, platform: str, goals: str, context: str) -> str:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        return (
            f"[DRY_RUN DRAFT] A Digital FTE works 8,760 hours/year vs a human's 2,000. "
            f"That's the power of AI agents running 24/7. #AIAgents #DigitalFTE #AgenticAI"
        )
    platform_guidance = {
        "linkedin": (
            "professional yet conversational, 150-250 words, "
            "open with a bold hook or thought-provoking question, "
            "share one specific insight or lesson about AI agents or digital employees, "
            "end with a call-to-action or question to drive comments, "
            "close with 6-8 hashtags from the brand hashtag list"
        ),
        "x": "punchy under 280 chars, strong hook in first 5 words, 2-3 sharp hashtags",
        "facebook": "conversational, 100-150 words, end with a question to spark comments, 3-4 hashtags",
    }
    guidance = platform_guidance.get(platform, "professional and concise")
    prompt = (
        f"You are a thought leader building personal brand authority in AI agents, "
        f"autonomous systems, and Digital FTEs (AI Full-Time Employees).\n\n"
        f"Draft a {platform} post that educates and grows followers in this niche.\n\n"
        f"Brand context and goals:\n{goals}\n\n"
        f"Topic hint or context:\n{context}\n\n"
        f"Style requirements: {guidance}\n\n"
        f"Rules:\n"
        f"- Write only the post text, no labels or preamble\n"
        f"- Never use clichés like 'excited to share' or 'thrilled to announce'\n"
        f"- Be specific, insightful, and original — share real lessons or observations\n"
        f"- Always end with relevant hashtags from the brand hashtag list in the goals"
    )
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.75,
    )
    return response.choices[0].message.content.strip()


def _read_business_goals(vault_path: Path) -> str:
    goals_file = vault_path / "Business_Goals.md"
    if goals_file.exists():
        return goals_file.read_text(encoding="utf-8")[:2000]
    return "No business goals file found."


def _read_body(task_path: Path) -> str:
    text = task_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else ""
    return text


def _build_approval_md(fm: dict, target: str, draft: str, expires: datetime) -> str:
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    return (
        f"---\n{header}---\n\n"
        f"## Action Required\n\n"
        f"Publish the drafted post to **{target.capitalize()}**\n\n"
        f"**Expires**: by {expires.isoformat()}\n\n"
        f"---\n\n"
        f"## Draft Post\n\n"
        f"{draft}\n\n"
        f"---\n\n"
        f"## How to Approve\n\n"
        f"Drag this file to `Approved/` in Obsidian to publish.\n"
        f"Drag to `Rejected/` to discard.\n"
    )
