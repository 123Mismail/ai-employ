import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from PlatinumTier.scripts.task_manager import list_tasks, move_task, read_frontmatter, update_frontmatter

logger = logging.getLogger(__name__)

MAX_STALE_FAILURES = 5


def _log_stale_recovery(vault_path: Path, task_name: str, agent: str, count: int) -> None:
    log_file = vault_path / "Logs" / f"{datetime.now(timezone.utc).date()}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": "stale_recovery",
        "actor": "reaper",
        "target": task_name,
        "parameters": {"recovered_from": f"In_Progress/{agent}", "stale_recovery_count": count},
        "approval_status": "auto",
        "approved_by": "system",
        "result": "returned_to_needs_action",
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.error("failed to write stale recovery log: %s", e)


def reap_stale(vault_path: Path, timeout_minutes: int = 30) -> int:
    recovered = 0
    now = datetime.now(timezone.utc)

    for agent in ("cloud", "local"):
        folder = vault_path / "In_Progress" / agent
        for task_path in list_tasks(folder):
            try:
                fm = read_frontmatter(task_path)
                claimed_at_raw = fm.get("claimed_at", "")
                if not claimed_at_raw:
                    continue

                claimed_at = datetime.fromisoformat(str(claimed_at_raw))
                if claimed_at.tzinfo is None:
                    claimed_at = claimed_at.replace(tzinfo=timezone.utc)

                elapsed_minutes = (now - claimed_at).total_seconds() / 60
                if elapsed_minutes <= timeout_minutes:
                    continue

                count = int(fm.get("stale_recovery_count", 0)) + 1

                # Permanently failed tasks go to Done/ with status=failed
                if count > MAX_STALE_FAILURES:
                    logger.warning("task %s exceeded max stale recoveries (%d), marking failed", task_path.name, MAX_STALE_FAILURES)
                    update_frontmatter(task_path, {"status": "failed", "stale_recovery_count": count})
                    move_task(task_path, vault_path / "Done")
                    _log_stale_recovery(vault_path, task_path.name, agent, count)
                    continue

                update_frontmatter(task_path, {
                    "status": "stale_recovered",
                    "claimed_by": "",
                    "claimed_at": "",
                    "stale_recovery_count": count,
                })
                move_task(task_path, vault_path / "Needs_Action")
                _log_stale_recovery(vault_path, task_path.name, agent, count)
                recovered += 1
                logger.info("stale task %s returned to Needs_Action/ (count=%d)", task_path.name, count)

            except Exception as e:
                logger.error("error processing stale task %s: %s", task_path.name, e)

    return recovered


def _reaper_loop(vault_path: Path, timeout_minutes: int) -> None:
    while True:
        time.sleep(300)  # 5 minutes
        try:
            n = reap_stale(vault_path, timeout_minutes)
            if n:
                logger.info("stale reaper: recovered %d task(s)", n)
        except Exception as e:
            logger.error("stale reaper error: %s", e)


def start_reaper_thread(vault_path: Path, timeout_minutes: int = 30) -> threading.Thread:
    t = threading.Thread(
        target=_reaper_loop,
        args=(vault_path, timeout_minutes),
        daemon=True,
    )
    t.start()
    return t
