import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts import vault_sync

logger = logging.getLogger(__name__)


def write_health(
    vault_path: Path,
    agent_role: str,
    status: str = "running",
    last_task: str = "",
    queue_depth: int = 0,
) -> None:
    health = {
        "agent": agent_role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "status": status,
        "last_task": last_task,
        "queue_depth": queue_depth,
        "last_sync_push": vault_sync.last_push_time(),
        "last_sync_pull": vault_sync.last_pull_time(),
        "vault_path": str(vault_path),
    }
    health_file = vault_path / "Logs" / f"health_{agent_role}.json"
    health_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        health_file.write_text(json.dumps(health, indent=2))
    except OSError as e:
        logger.error("failed to write health file: %s", e)


def _health_loop(vault_path: Path, agent_role: str, interval: int) -> None:
    while True:
        write_health(vault_path, agent_role)
        time.sleep(interval)


def start_health_thread(vault_path: Path, agent_role: str, interval: int = 60) -> threading.Thread:
    t = threading.Thread(
        target=_health_loop,
        args=(vault_path, agent_role, interval),
        daemon=True,
    )
    t.start()
    return t
