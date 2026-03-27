import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("RateLimiter")

# Max actions allowed per hour per action type
HOURLY_LIMITS = {
    "email_send": 10,
    "whatsapp_send": 20,
    "linkedin_post": 5,
    "social_post": 10,
    "odoo_action": 20,
}


class RateLimiter:
    def __init__(self, logs_path: Path):
        self.state_file = logs_path / "rate_limit_state.json"
        self._state = self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self):
        self.state_file.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def check_and_increment(self, action_type: str) -> bool:
        """Returns True if action is allowed, False if rate limit is exceeded."""
        limit = HOURLY_LIMITS.get(action_type, 100)
        hour_key = datetime.now().strftime("%Y-%m-%dT%H")
        key = f"{action_type}:{hour_key}"

        count = self._state.get(key, 0)
        if count >= limit:
            logger.warning(f"Rate limit reached for '{action_type}': {count}/{limit} this hour.")
            return False

        self._state[key] = count + 1
        # Prune keys older than current hour
        self._state = {k: v for k, v in self._state.items() if k.split(":")[-1] >= hour_key}
        self._save()
        return True
