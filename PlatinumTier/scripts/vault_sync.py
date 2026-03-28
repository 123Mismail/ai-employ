import logging
import subprocess
import threading
import time
from pathlib import Path

from PlatinumTier.scripts.exceptions import VaultSyncError

logger = logging.getLogger(__name__)

_last_push: str = ""
_last_pull: str = ""


def _run_git(args: list[str], vault_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(vault_path),
        capture_output=True,
        text=True,
        check=True,
    )


def pull_rebase(vault_path: Path, max_retries: int = 3) -> None:
    global _last_pull
    # Commit any local changes first to avoid "unstaged changes" error
    _commit_local_changes(vault_path)
    # Abort any stuck rebase
    try:
        _run_git(["rebase", "--abort"], vault_path)
    except subprocess.CalledProcessError:
        pass
    # Remove stuck rebase-merge dir if present
    rebase_dir = vault_path / ".git" / "rebase-merge"
    if rebase_dir.exists():
        import shutil
        shutil.rmtree(str(rebase_dir))
    delay = 2
    for attempt in range(max_retries):
        try:
            _run_git(["pull", "--no-rebase", "origin", "main"], vault_path)
            _last_pull = _now_iso()
            logger.info("vault pull OK")
            return
        except subprocess.CalledProcessError as e:
            logger.warning("pull --rebase failed (attempt %d): %s", attempt + 1, e.stderr.strip())
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    raise VaultSyncError(f"git pull --rebase failed after {max_retries} attempts")


def push(vault_path: Path, commit_msg: str = "vault: auto-sync", max_retries: int = 3) -> None:
    global _last_push
    try:
        _run_git(["add", "--", "."], vault_path)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(vault_path),
            capture_output=True,
        )
        if result.returncode == 0:
            logger.debug("nothing to commit, skipping push")
            return
        _run_git(["commit", "-m", commit_msg], vault_path)
    except subprocess.CalledProcessError as e:
        raise VaultSyncError(f"git add/commit failed: {e.stderr.strip()}")

    delay = 2
    for attempt in range(max_retries):
        try:
            _run_git(["push"], vault_path)
            _last_push = _now_iso()
            logger.info("vault push OK")
            return
        except subprocess.CalledProcessError as e:
            logger.warning("push failed (attempt %d): %s", attempt + 1, e.stderr.strip())
            if attempt < max_retries - 1:
                try:
                    pull_rebase(vault_path)
                except VaultSyncError:
                    pass
                time.sleep(delay)
                delay *= 2
    raise VaultSyncError(f"git push failed after {max_retries} attempts")


def ensure_hooks_active(vault_path: Path) -> None:
    hooks_path = vault_path / ".githooks"
    if not hooks_path.exists():
        logger.warning(".githooks/ not found in vault — pre-push hook inactive")
        return
    try:
        _run_git(["config", "core.hooksPath", ".githooks"], vault_path)
    except subprocess.CalledProcessError as e:
        logger.warning("could not set core.hooksPath: %s", e.stderr.strip())


def _commit_local_changes(vault_path: Path) -> None:
    """Stage and commit any local vault changes (health, workspace, logs) before pulling."""
    try:
        _run_git(["add", "--", "."], vault_path)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(vault_path),
            capture_output=True,
        )
        if result.returncode != 0:
            _run_git(["commit", "-m", "vault: auto-commit local changes"], vault_path)
            logger.debug("committed local vault changes before pull")
    except subprocess.CalledProcessError as e:
        logger.debug("pre-pull commit skipped: %s", e.stderr.strip())


def sync_loop(vault_path: Path, interval: int = 60) -> None:
    while True:
        time.sleep(interval)
        try:
            _commit_local_changes(vault_path)
            pull_rebase(vault_path)
        except VaultSyncError as e:
            logger.error("periodic pull failed: %s", e)


def start_sync_loop(vault_path: Path, interval: int = 60) -> threading.Thread:
    t = threading.Thread(target=sync_loop, args=(vault_path, interval), daemon=True)
    t.start()
    return t


def last_push_time() -> str:
    return _last_push


def last_pull_time() -> str:
    return _last_pull


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
