"""
Platinum Tier — Cloud Agent
Runs 24/7 on the Cloud VM. Detects tasks, drafts replies/posts, writes approval files.
NEVER sends emails, posts to social media, or executes Odoo actions directly.
"""
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from PlatinumTier.scripts import health_writer, vault_sync
from PlatinumTier.scripts.audit_log import log_action
from PlatinumTier.scripts.handlers import (
    cloud_email_handler,
    cloud_linkedin_comment_handler,
    cloud_linkedin_connect_handler,
    cloud_linkedin_reply_handler,
    cloud_odoo_handler,
    cloud_social_handler,
    cloud_whatsapp_handler,
)
from PlatinumTier.scripts.stale_reaper import start_reaper_thread
from PlatinumTier.scripts.task_manager import (
    claim_task,
    ensure_vault_structure,
    list_tasks,
    read_frontmatter,
)

load_dotenv(os.getenv("ENV_FILE", ".env"))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [cloud] %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.environ["VAULT_PATH"])
AGENT_ROLE = "cloud"
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))
STALE_TIMEOUT = int(os.getenv("STALE_TASK_TIMEOUT_MINUTES", "30"))
SYNC_INTERVAL = int(os.getenv("VAULT_SYNC_INTERVAL", "60"))

# Cloud Agent MUST NOT have send credentials — enforce at import time
# (Gmail send, WhatsApp, LinkedIn publish, Odoo action_post are Local-only)


def _build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        if os.getenv("DRY_RUN", "false").lower() == "true":
            logger.info("[DRY_RUN] No OPENAI_API_KEY — using stub key (drafts will be mocked)")
            api_key = "sk-dry-run-stub"
        else:
            raise ValueError("OPENAI_API_KEY is required when DRY_RUN=false")
    return OpenAI(api_key=api_key)


def _dispatch(task_path: Path, vault_path: Path, openai_client: OpenAI) -> bool:
    fm = read_frontmatter(task_path)
    task_type = fm.get("type", "")

    if task_type == "email":
        return cloud_email_handler.handle(task_path, vault_path, openai_client)
    elif task_type == "whatsapp":
        return cloud_whatsapp_handler.handle(task_path, vault_path, openai_client)
    elif task_type in ("proactive_task", "social_post"):
        return cloud_social_handler.handle(task_path, vault_path, openai_client)
    elif task_type == "odoo_invoice":
        return cloud_odoo_handler.handle(task_path, vault_path)
    elif task_type == "linkedin_reply":
        return cloud_linkedin_reply_handler.handle(task_path, vault_path, openai_client)
    elif task_type == "linkedin_comment":
        return cloud_linkedin_comment_handler.handle(task_path, vault_path, openai_client)
    elif task_type == "linkedin_connect":
        return cloud_linkedin_connect_handler.handle(task_path, vault_path, openai_client)
    else:
        logger.warning("unknown task type '%s' in %s — skipping", task_type, task_path.name)
        return False


def run() -> None:
    logger.info("Cloud Agent starting — vault: %s", VAULT_PATH)

    # Startup sync
    try:
        vault_sync.pull_rebase(VAULT_PATH)
    except Exception as e:
        logger.warning("startup pull failed (continuing on local vault): %s", e)

    ensure_vault_structure(VAULT_PATH)
    vault_sync.ensure_hooks_active(VAULT_PATH)

    # Start background threads
    start_reaper_thread(VAULT_PATH, STALE_TIMEOUT)
    health_writer.start_health_thread(VAULT_PATH, AGENT_ROLE)
    vault_sync.start_sync_loop(VAULT_PATH, SYNC_INTERVAL)

    openai_client = _build_openai_client()
    health_writer.write_health(VAULT_PATH, AGENT_ROLE, status="running")
    logger.info("Cloud Agent ready — scanning every %ds", SCAN_INTERVAL)

    while True:
        tasks = list_tasks(VAULT_PATH / "Needs_Action")
        health_writer.write_health(VAULT_PATH, AGENT_ROLE, queue_depth=len(tasks))

        for task_path in tasks:
            claimed = claim_task(task_path, AGENT_ROLE, VAULT_PATH)
            if not claimed:
                logger.debug("could not claim %s (already taken)", task_path.name)
                continue

            logger.info("claimed %s", task_path.name)
            in_progress_path = VAULT_PATH / "In_Progress" / AGENT_ROLE / task_path.name
            success = _dispatch(in_progress_path, VAULT_PATH, openai_client)

            try:
                vault_sync.push(VAULT_PATH, f"cloud: processed {task_path.name}")
            except Exception as e:
                logger.error("vault push failed after processing %s: %s", task_path.name, e)

            health_writer.write_health(
                VAULT_PATH, AGENT_ROLE,
                last_task=task_path.name,
                status="running" if success else "degraded",
            )

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    run()
