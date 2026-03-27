"""
LinkedIn Rate Limiter & Session Lock
Shared utility for all LinkedIn engagement handlers and watchers.

RateLimiter  — enforces daily comment/connection limits, account pause gate
SessionLock  — file-based mutex preventing concurrent Playwright sessions
"""
import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"
RATE_STATE_PATH = VAULT_PATH / "Logs" / "linkedin_rate_state.json"
LOCK_FILE_PATH = REPO_ROOT / "linkedin_session" / "browser.lock"

_DEFAULT_STATE = {
    "date": "",
    "comments_today": 0,
    "connections_today": 0,
    "comment_limit": int(os.getenv("LINKEDIN_COMMENT_LIMIT", "10")),
    "connection_limit": int(os.getenv("LINKEDIN_CONNECTION_LIMIT", "5")),
    "account_paused": False,
    "pause_reason": "",
    "last_action_at": "",
}


def get_vault_path() -> Path:
    """Return vault path without circular imports."""
    return VAULT_PATH


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self):
        self._state = self._load()

    def _load(self) -> dict:
        try:
            if RATE_STATE_PATH.exists():
                data = json.loads(RATE_STATE_PATH.read_text(encoding="utf-8"))
                # Fill missing keys with defaults
                for k, v in _DEFAULT_STATE.items():
                    data.setdefault(k, v)
                return data
        except Exception as e:
            logger.warning("Could not read rate state, using defaults: %s", e)
        return dict(_DEFAULT_STATE)

    def _save(self) -> None:
        """Atomic write via .tmp rename to avoid corruption."""
        tmp = RATE_STATE_PATH.with_suffix(".tmp")
        try:
            RATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
            tmp.replace(RATE_STATE_PATH)
        except Exception as e:
            logger.error("Failed to save rate state: %s", e)

    def _reset_if_new_day(self) -> None:
        today = date.today().isoformat()
        if self._state.get("date") != today:
            self._state["date"] = today
            self._state["comments_today"] = 0
            self._state["connections_today"] = 0
            logger.info("Daily LinkedIn counters reset for %s", today)
            self._save()

    def is_paused(self) -> bool:
        return bool(self._state.get("account_paused", False))

    def can_execute(self, action_type: str) -> bool:
        """
        Returns True if the action can proceed.
        action_type: "comment" | "connect"  (replies are unlimited)
        """
        self._reset_if_new_day()
        if self.is_paused():
            logger.warning("LinkedIn account is paused: %s", self._state.get("pause_reason"))
            return False
        if action_type == "comment":
            limit = self._state.get("comment_limit", 10)
            used = self._state.get("comments_today", 0)
            if used >= limit:
                logger.warning("Daily comment limit reached (%d/%d)", used, limit)
                return False
        elif action_type == "connect":
            limit = self._state.get("connection_limit", 5)
            used = self._state.get("connections_today", 0)
            if used >= limit:
                logger.warning("Daily connection limit reached (%d/%d)", used, limit)
                return False
        return True

    def record_action(self, action_type: str) -> None:
        """Increment the counter for the given action type and persist."""
        self._reset_if_new_day()
        if action_type == "comment":
            self._state["comments_today"] = self._state.get("comments_today", 0) + 1
        elif action_type == "connect":
            self._state["connections_today"] = self._state.get("connections_today", 0) + 1
        self._state["last_action_at"] = datetime.now().isoformat()
        self._save()
        logger.info(
            "Recorded LinkedIn action '%s' — comments: %d, connections: %d",
            action_type,
            self._state.get("comments_today", 0),
            self._state.get("connections_today", 0),
        )

    def pause_account(self, reason: str) -> None:
        """Set account_paused=True. Only a human can clear this."""
        self._state["account_paused"] = True
        self._state["pause_reason"] = reason
        self._save()
        logger.critical(
            "LinkedIn account PAUSED — reason: %s. "
            "Manually set account_paused=false in %s to resume.",
            reason,
            RATE_STATE_PATH,
        )


# ---------------------------------------------------------------------------
# SessionLock
# ---------------------------------------------------------------------------

class SessionLock:
    """
    File-based mutex for the LinkedIn Playwright browser session.
    Prevents concurrent launch_persistent_context on the same user_data_dir.

    Usage:
        lock = SessionLock(holder="my-process")
        with lock:
            # browser actions here
    """

    def __init__(self, holder: str = "unknown", timeout: int = 60):
        self._holder = holder
        self._timeout = timeout
        self._lock_path = LOCK_FILE_PATH

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _read_lock(self) -> dict | None:
        try:
            if self._lock_path.exists():
                return json.loads(self._lock_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

    def _write_lock(self) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path.write_text(
            json.dumps({
                "pid": os.getpid(),
                "holder": self._holder,
                "acquired_at": datetime.now().isoformat(),
            }),
            encoding="utf-8",
        )

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout
        while True:
            existing = self._read_lock()
            if existing is None:
                # No lock — acquire
                self._write_lock()
                logger.debug("Session lock acquired by %s (pid %d)", self._holder, os.getpid())
                return
            existing_pid = existing.get("pid", 0)
            if not self._pid_alive(existing_pid):
                # Stale lock from dead process — force acquire
                logger.warning(
                    "Stale session lock from pid %d (%s) — force acquiring",
                    existing_pid,
                    existing.get("holder"),
                )
                self._write_lock()
                return
            if time.monotonic() >= deadline:
                logger.warning(
                    "Session lock timeout after %ds — force acquiring from %s",
                    self._timeout,
                    existing.get("holder"),
                )
                self._write_lock()
                return
            logger.debug(
                "Session lock held by %s (pid %d) — waiting...",
                existing.get("holder"),
                existing_pid,
            )
            time.sleep(5)

    def release(self) -> None:
        try:
            if self._lock_path.exists():
                self._lock_path.unlink()
                logger.debug("Session lock released by %s", self._holder)
        except Exception as e:
            logger.warning("Failed to release session lock: %s", e)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()
