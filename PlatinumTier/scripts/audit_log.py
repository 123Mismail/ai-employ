import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def log_action(
    vault_path: Path,
    action_type: str,
    actor: str,
    target: str,
    parameters: dict = None,
    result: str = "success",
    approval_status: str = "auto",
    approved_by: str = "system",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "parameters": parameters or {},
        "approval_status": approval_status,
        "approved_by": approved_by,
        "result": result,
    }
    log_file = vault_path / "Logs" / f"{datetime.now(timezone.utc).date()}.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.error("audit log write failed: %s", e)
