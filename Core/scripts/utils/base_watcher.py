import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path


class BaseWatcher(ABC):
    """Base class for all Perception-layer watcher scripts."""

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Poll the external source and return a list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Write a .md task file into Needs_Action for the given item."""
        pass

    def run(self):
        """Default poll loop. Override for event-driven watchers (watchdog, Playwright)."""
        self.logger.info(f"Starting {self.__class__.__name__} (interval={self.check_interval}s)")
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f"Error in {self.__class__.__name__}: {e}")
            time.sleep(self.check_interval)
