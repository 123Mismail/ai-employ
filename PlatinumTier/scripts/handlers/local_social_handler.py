import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.exceptions import ApprovalExpiredError
from PlatinumTier.scripts.task_manager import move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Add GoldTier to path for reuse of existing social skills
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))


def execute(approval_path: Path, vault_path: Path) -> bool:
    try:
        fm = read_frontmatter(approval_path)
        target = fm.get("target", "")
        content = fm.get("post_content", "")
        image_url = fm.get("image_url", "")

        if not target or not content:
            raise ValueError("approval missing 'target' or 'post_content'")

        # Claim the file immediately — moves out of Approved/ so it won't be retried on next poll
        in_progress_dir = vault_path / "In_Progress" / "local"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        claimed_path = in_progress_dir / approval_path.name
        move_task(approval_path, in_progress_dir)

        if DRY_RUN:
            logger.info("[DRY_RUN] would post to %s: %s...", target, content[:60])
            success = True
        else:
            success = _publish(target, content, image_url)

        if success:
            update_frontmatter(claimed_path, {
                "status": "approved",
                "approved_by": "human",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            })
            move_task(claimed_path, vault_path / "Done")
            log_action(vault_path, "social_post_published", "local", approval_path.name,
                       parameters={"target": target, "dry_run": DRY_RUN},
                       approval_status="approved", approved_by="human")
            logger.info("published to %s (dry_run=%s)", target, DRY_RUN)
        else:
            move_task(claimed_path, vault_path / "Rejected")
            log_action(vault_path, "social_post_failed", "local", approval_path.name,
                       result="error", parameters={"target": target})

        return success

    except ApprovalExpiredError:
        raise
    except Exception as e:
        logger.error("local_social_handler failed for %s: %s", approval_path.name, e)
        log_action(vault_path, "social_post_failed", "local", approval_path.name,
                   result="error", parameters={"error": str(e)})
        return False


def _publish(target: str, content: str, image_url: str) -> bool:
    try:
        from GoldTier.scripts.skills.social_post import SocialManager
        poster = SocialManager()
        if target == "linkedin":
            from GoldTier.scripts.skills.linkedin_post import LinkedInManager
            lp = LinkedInManager()
            return lp.post_update(content)
        elif target in ("x", "twitter"):
            return poster.post_to_x(content)
        elif target == "facebook":
            return poster.post_to_facebook(content)
        else:
            logger.warning("unknown social target: %s", target)
            return False
    except ImportError as e:
        logger.error("social skill import failed: %s", e)
        return False
