import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from PlatinumTier.scripts.exceptions import CrossDeviceMoveError

logger = logging.getLogger(__name__)

VAULT_FOLDERS = [
    "Needs_Action",
    "In_Progress/cloud",
    "In_Progress/local",
    "Plans",
    "Pending_Approval",
    "Approved",
    "Rejected",
    "Done",
    "Logs",
    "Briefings",
    "Inbox/drop_zone",
]


# ---------------------------------------------------------------------------
# Vault structure bootstrap
# ---------------------------------------------------------------------------

def ensure_vault_structure(vault_path: Path) -> None:
    for folder in VAULT_FOLDERS:
        target = vault_path / folder
        target.mkdir(parents=True, exist_ok=True)
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    logger.info("vault structure verified at %s", vault_path)


# ---------------------------------------------------------------------------
# YAML frontmatter helpers
# ---------------------------------------------------------------------------

def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split '---\\n...\\n---\\n body' into (frontmatter_dict, body)."""
    pattern = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)
    m = pattern.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return fm, body


def _join_frontmatter(fm: dict, body: str) -> str:
    return f"---\n{yaml.dump(fm, default_flow_style=False, allow_unicode=True)}---\n{body}"


def read_frontmatter(task_path: Path) -> dict:
    fm, _ = _split_frontmatter(task_path.read_text(encoding="utf-8"))
    return fm


def update_frontmatter(task_path: Path, updates: dict[str, Any]) -> None:
    text = task_path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    fm.update(updates)
    task_path.write_text(_join_frontmatter(fm, body), encoding="utf-8")


# ---------------------------------------------------------------------------
# Atomic claim-by-move
# ---------------------------------------------------------------------------

def claim_task(task_path: Path, agent_role: str, vault_path: Path) -> bool:
    """
    Atomically move task_path from Needs_Action/ to In_Progress/<agent_role>/.
    Returns True on success, False if the file was already claimed (race loss).
    Raises CrossDeviceMoveError if source and dest are on different filesystems.
    """
    dest_folder = vault_path / "In_Progress" / agent_role
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / task_path.name

    # Cross-device guard (R-002)
    try:
        src_dev = task_path.stat().st_dev
        dst_dev = dest_folder.stat().st_dev
    except FileNotFoundError:
        return False  # already claimed or deleted

    if src_dev != dst_dev:
        raise CrossDeviceMoveError(
            f"Cannot atomically move {task_path} → {dest_folder}: different filesystems"
        )

    # Windows PermissionError retry (R-002 edge case)
    import time
    for attempt in range(3):
        try:
            task_path.rename(dest_path)
            break
        except FileNotFoundError:
            return False  # another agent claimed it first
        except PermissionError:
            if attempt == 2:
                return False
            time.sleep(1)

    # Update frontmatter after successful claim
    try:
        update_frontmatter(dest_path, {
            "claimed_by": agent_role,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "status": "in_progress",
        })
    except Exception as e:
        logger.warning("claimed task but could not update frontmatter: %s", e)

    logger.info("claimed %s -> In_Progress/%s/", task_path.name, agent_role)
    return True


# ---------------------------------------------------------------------------
# General file movement
# ---------------------------------------------------------------------------

def move_task(task_path: Path, dest_folder: Path) -> Path:
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest = dest_folder / task_path.name
    task_path.rename(dest)
    logger.info("moved %s -> %s/", task_path.name, dest_folder.name)
    return dest


# ---------------------------------------------------------------------------
# Directory listing
# ---------------------------------------------------------------------------

def list_tasks(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix == ".md" and p.name != ".gitkeep")
