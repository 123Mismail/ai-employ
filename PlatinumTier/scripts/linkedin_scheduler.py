"""
LinkedIn Daily Post Scheduler
Runs on Cloud VM as a PM2 process.

Logic:
- Checks every 30 minutes if today's LinkedIn post has been done
- If not done AND current time is within the posting window → generate + write approval file
- If FTE was offline during scheduled time → catches up on next run
- Never posts twice in the same day
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(os.getenv("ENV_FILE", str(REPO_ROOT / ".env")))

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.task_manager import ensure_vault_structure
from PlatinumTier.scripts import vault_sync, health_writer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [linkedin-scheduler] %(levelname)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.environ["VAULT_PATH"])
POST_HOUR = int(os.getenv("LINKEDIN_POST_HOUR", "9"))        # 9 AM default
POST_MINUTE = int(os.getenv("LINKEDIN_POST_MINUTE", "0"))    # :00 default
CHECK_INTERVAL = int(os.getenv("LINKEDIN_CHECK_INTERVAL", "1800"))  # 30 min
APPROVAL_EXPIRY_HOURS = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))


def _already_posted_today(vault_path: Path) -> bool:
    """Check Done/ and Pending_Approval/ to see if today's post exists."""
    today = datetime.now().strftime("%Y%m%d")

    # Check Done/ for completed posts
    done_dir = vault_path / "Done"
    if done_dir.exists():
        for f in done_dir.glob("APPROVE_POST_LINKEDIN_*.md"):
            if today in f.name:
                logger.info("Today's post already in Done/: %s", f.name)
                return True

    # Check Pending_Approval/ for posts awaiting approval
    pending_dir = vault_path / "Pending_Approval"
    if pending_dir.exists():
        for f in pending_dir.glob("APPROVE_POST_LINKEDIN_*.md"):
            if today in f.name:
                logger.info("Today's post already in Pending_Approval/: %s", f.name)
                return True

    # Check Approved/ for posts about to be executed
    approved_dir = vault_path / "Approved"
    if approved_dir.exists():
        for f in approved_dir.glob("APPROVE_POST_LINKEDIN_*.md"):
            if today in f.name:
                logger.info("Today's post already in Approved/: %s", f.name)
                return True

    return False


def _should_post_today() -> bool:
    """Returns True if we are past today's scheduled posting time."""
    now = datetime.now()
    scheduled = now.replace(hour=POST_HOUR, minute=POST_MINUTE, second=0, microsecond=0)
    return now >= scheduled


def _generate_post(openai_client: OpenAI) -> str:
    """Generate a LinkedIn post using OpenAI based on Business_Goals.md."""
    goals_path = VAULT_PATH / "Business_Goals.md"
    goals_context = goals_path.read_text(encoding="utf-8") if goals_path.exists() else ""

    today_str = datetime.now().strftime("%A, %B %d, %Y")

    prompt = (
        f"You are a LinkedIn content writer for an AI engineer building autonomous Digital FTEs.\n\n"
        f"Today is {today_str}.\n\n"
        f"Business context:\n{goals_context}\n\n"
        f"Write ONE engaging LinkedIn post (150-300 words) about one of these topics:\n"
        f"1. Behind-the-scenes of building AI employees\n"
        f"2. Lessons learned from autonomous agent development\n"
        f"3. How Digital FTEs save time vs human labor\n"
        f"4. Future of work with AI agents running 24/7\n\n"
        f"Rules:\n"
        f"- Start with a hook (question or bold statement)\n"
        f"- Include 1-2 concrete examples or numbers\n"
        f"- End with a call to action or question\n"
        f"- Add 5-7 relevant hashtags at the end\n"
        f"- Tone: insightful, practical, NOT hype\n"
        f"- Write only the post text, nothing else"
    )

    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


def _write_approval_file(vault_path: Path, post_content: str) -> Path:
    """Write approval file to Pending_Approval/."""
    import yaml
    from datetime import timedelta

    now = datetime.now()
    now_utc = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M%S")
    approval_name = f"APPROVE_POST_LINKEDIN_{ts}.md"
    approval_path = vault_path / "Pending_Approval" / approval_name

    fm = {
        "type": "linkedin_post",
        "target": "linkedin",
        "status": "pending_approval",
        "created_at": now_utc.isoformat(),
        "expires": (now_utc + timedelta(hours=APPROVAL_EXPIRY_HOURS)).isoformat(),
        "claimed_by": "linkedin-scheduler",
        "approved_by": "",
        "approved_at": "",
        "post_content": post_content,
        "scheduled_for": now.strftime("%Y-%m-%d %H:%M"),
    }

    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    content = (
        f"---\n{header}---\n\n"
        f"# LinkedIn Post — {now.strftime('%Y-%m-%d')}\n\n"
        f"**Scheduled for:** {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"---\n\n"
        f"## Post Content\n\n"
        f"{post_content}\n\n"
        f"---\n\n"
        f"**Approve:** drag to `Approved/`  |  **Reject:** drag to `Rejected/`\n"
    )

    approval_path.write_text(content, encoding="utf-8")
    logger.info("Approval file written: %s", approval_name)
    return approval_path


def run() -> None:
    logger.info("LinkedIn Scheduler starting — post time: %02d:%02d, check every %ds",
                POST_HOUR, POST_MINUTE, CHECK_INTERVAL)

    ensure_vault_structure(VAULT_PATH)

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    while True:
        try:
            vault_sync.pull_rebase(VAULT_PATH)
        except Exception as e:
            logger.warning("vault pull failed: %s", e)

        if _should_post_today():
            if _already_posted_today(VAULT_PATH):
                logger.info("Today's LinkedIn post already done — skipping")
            else:
                logger.info("No post yet today — generating...")
                try:
                    post_content = _generate_post(openai_client)
                    approval_path = _write_approval_file(VAULT_PATH, post_content)

                    try:
                        vault_sync.push(VAULT_PATH, f"scheduler: LinkedIn post draft {datetime.now().strftime('%Y-%m-%d')}")
                    except Exception as e:
                        logger.warning("vault push failed: %s", e)

                    log_action(VAULT_PATH, "linkedin_post_draft_created", "scheduler",
                               approval_path.name,
                               parameters={"scheduled_for": datetime.now().strftime("%Y-%m-%d %H:%M")})
                    logger.info("LinkedIn post draft created and pushed to vault")

                except Exception as e:
                    logger.error("Failed to generate LinkedIn post: %s", e)
        else:
            logger.info("Before scheduled post time (%02d:%02d) — waiting", POST_HOUR, POST_MINUTE)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
