import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Root detection — insert BEFORE project imports
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from Core.scripts.utils.base_watcher import BaseWatcher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PerceptionWatcher")

class PerceptionHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path, watch_path: Path):
        self.vault_path = vault_path
        self.watch_path = watch_path
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.check_existing_files()

    def check_existing_files(self):
        logger.info(f"Checking for existing files in {self.watch_path}...")
        for file in self.watch_path.glob("*"):
            if file.is_file():
                logger.info(f"Existing task found: {file.name}")
                self.process_file(file)

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def process_file(self, source_path: Path):
        logger.info(f"Processing task: {source_path.name}")
        # Wait for file stability
        time.sleep(1)
        
        try:
            self.create_metadata_file(source_path)
            logger.info(f"Task queued in Needs_Action.")
            # Move the original file to a 'Processed' or delete it to avoid re-processing?
            # The spec doesn't explicitly say, but usually watchers move the source.
            # For now, let's just create metadata. The Orchestrator will claim the METADATA.
        except Exception as e:
            logger.error(f"Error processing file {source_path.name}: {e}")

    def create_metadata_file(self, source_path: Path) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        metadata_filename = f"FILE_{source_path.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        metadata_path = self.needs_action_path / metadata_filename
        
        content = f"""---
type: file_drop
source: {source_path.name}
timestamp: {timestamp}
status: pending
---
# New Task: {source_path.name}
Detected at {timestamp}.

## Instructions
This task is waiting for triage. The Master Orchestrator will automatically create a plan.
"""
        metadata_path.write_text(content, encoding='utf-8')
        return metadata_path

class FilesystemWatcher(BaseWatcher):
    """Watchdog-based watcher; overrides run() — poll pattern not applicable."""

    def __init__(self, vault_path: str, watch_path: str):
        super().__init__(vault_path, check_interval=0)
        self.watch_path = Path(watch_path)

    def check_for_updates(self) -> list:
        # Handled by watchdog Observer in run()
        return []

    def create_action_file(self, item) -> Path:
        # Handled internally by PerceptionHandler
        return Path()

    def run(self):
        if not self.watch_path.exists():
            self.watch_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting PERCEPTION Watcher on: {self.watch_path}")
        event_handler = PerceptionHandler(self.vault_path, self.watch_path)
        observer = Observer()
        observer.schedule(event_handler, str(self.watch_path), recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def run_watcher(path_to_watch: str, vault_path: str):
    FilesystemWatcher(vault_path, path_to_watch).run()


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).parent.parent.parent.parent
    WATCH_PATH = REPO_ROOT / "AI_Employee_Vault" / "Inbox" / "drop_zone"
    VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"

    run_watcher(str(WATCH_PATH), str(VAULT_PATH))
