import time
import logging
import sys
import threading
import io
import shutil
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Force UTF-8 for Windows logging
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Modular Imports
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(REPO_ROOT))

# Skill Imports
from Core.scripts.skills.vault_processor import VaultProcessor
from SilverTier.scripts.skills.email_action import EmailSender
from GoldTier.scripts.skills.social_post import SocialManager
from GoldTier.scripts.skills.linkedin_post import LinkedInManager
from SilverTier.scripts.skills.whatsapp_reply import WhatsAppManager
from GoldTier.scripts.skills.odoo_skill import OdooSkill
from Core.scripts.utils.rate_limiter import RateLimiter

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MasterOrchestrator")

class VaultOrchestrator(FileSystemEventHandler):
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.done_path = self.vault_path / "Done"
        self.processor = VaultProcessor(str(vault_path))
        self.email_sender = EmailSender(vault_path)
        self.social_manager = SocialManager()
        self.linkedin_manager = LinkedInManager()
        self.whatsapp_manager = WhatsAppManager()
        self.odoo_skill = OdooSkill()
        self.rate_limiter = RateLimiter(self.vault_path / "Logs")
        self.check_existing_tasks()
        self.check_existing_approvals()

    def check_existing_tasks(self):
        logger.info(f"Checking for existing tasks in {self.needs_action_path}...")
        for file in self.needs_action_path.glob("*.md"):
            logger.info(f"Existing task found: {file.name}")
            self.processor.claim_task(file)

    def check_existing_approvals(self):
        approved_path = self.vault_path / "Approved"
        logger.info(f"Checking for existing approvals in {approved_path}...")
        for file in approved_path.glob("*.md"):
            logger.info(f"Existing approval found: {file.name}")
            # Simulate a move event to trigger processing
            class DummyEvent:
                src_path = str(file)
                dest_path = str(file)
                is_directory = False
            self.handle_event(DummyEvent(), moved=True)

    def on_created(self, event):
        self.handle_event(event)

    def on_moved(self, event):
        self.handle_event(event, moved=True)

    def handle_event(self, event, moved=False):
        if event.is_directory: return
        target_path = Path(event.dest_path) if moved else Path(event.src_path)
        
        # 0. PERCEPTION TRIGGER: New file in Needs_Action
        # Skip task types handled by platinum agents (email, whatsapp, odoo_invoice, linkedin)
        PLATINUM_TYPES = ("email", "whatsapp", "odoo_invoice", "linkedin", "social_post", "proactive_task")
        if "Needs_Action" in str(target_path) and target_path.suffix == ".md":
            try:
                content = target_path.read_text(encoding="utf-8")
                if any(f"type: {t}" in content for t in PLATINUM_TYPES):
                    logger.debug(f"Skipping platinum task: {target_path.name}")
                    return
            except Exception:
                pass
            logger.info(f"👁️ Perception Triggered: {target_path.name}")
            time.sleep(1)
            self.processor.claim_task(target_path)

        # 1. BRAIN TRIGGER: File moved to To_Draft
        if "To_Draft" in str(target_path) and target_path.suffix == ".md":
            logger.info(f"🧠 Brain Triggered (Selective Drafting): {target_path.name}")
            time.sleep(1)
            self.processor.claim_task(target_path)

        # 2. HANDS TRIGGER: Files in Approved
        if "Approved" in str(target_path) and target_path.suffix == ".md":
            logger.info(f"⚡ Hands Triggered: Processing Approval -> {target_path.name}")
            time.sleep(1)

            content = target_path.read_text(encoding='utf-8')

            # Check approval expiry
            for line in content.splitlines():
                if line.startswith("expires:"):
                    expires_str = line.split(":", 1)[1].strip()
                    try:
                        expires = datetime.fromisoformat(expires_str)
                        if datetime.now() > expires:
                            logger.warning(f"Approval expired: {target_path.name}. Moving to Rejected.")
                            shutil.move(str(target_path), str(self.vault_path / "Rejected" / target_path.name))
                            return
                    except ValueError:
                        pass
                    break

            # Action: Email
            if "type: email_approval" in content:
                if not self.rate_limiter.check_and_increment("email_send"):
                    return
                self.email_sender.send_approved_email(target_path)
                self.processor.log_action("email_send", {"file": target_path.name},
                                          target=target_path.name, result="success",
                                          approval_status="approved", approved_by="human")

            # Action: WhatsApp Reply
            elif "type: whatsapp_reply" in content or "whatsapp" in target_path.name.lower():
                if not self.rate_limiter.check_and_increment("whatsapp_send"):
                    return
                recipient = "Mine(You)"
                for line in content.splitlines():
                    if line.startswith("recipient:"):
                        recipient = line.split(":")[1].strip().strip('"')

                post_body = content
                if "# Smart AI Response" in content:
                    post_body = content.split("# Smart AI Response")[-1].split("## To Send")[0].strip()
                elif "---" in content:
                    post_body = content.split("---")[-1].strip()

                if self.whatsapp_manager.send_message(recipient, post_body):
                    shutil.move(str(target_path), str(self.done_path / target_path.name))
                    self.processor.log_action("whatsapp_send", {"file": target_path.name},
                                              target=recipient, result="success",
                                              approval_status="approved", approved_by="human")

            # Action: LinkedIn
            elif "type: linkedin_post" in content or "linkedin" in target_path.name.lower():
                if not self.rate_limiter.check_and_increment("linkedin_post"):
                    return
                post_body = content
                if "# Smart AI Post Draft" in content:
                    post_body = content.split("# Smart AI Post Draft")[-1].split("## To Post")[0].strip()
                elif "---" in content:
                    post_body = content.split("---")[-1].strip()

                if self.linkedin_manager.post_update(post_body):
                    shutil.move(str(target_path), str(self.done_path / target_path.name))
                    self.processor.log_action("linkedin_post", {"file": target_path.name},
                                              target="linkedin", result="success",
                                              approval_status="approved", approved_by="human")

            # Action: Social Media (X/FB/Instagram)
            elif "type: social_post" in content:
                if not self.rate_limiter.check_and_increment("social_post"):
                    return
                post_body = content.split("---", 2)[2].strip()
                if self.social_manager.post_all(post_body):
                    shutil.move(str(target_path), str(self.done_path / target_path.name))
                    self.processor.log_action("social_post", {"file": target_path.name},
                                              target="x,facebook,instagram", result="success",
                                              approval_status="approved", approved_by="human")

            # Action: Odoo
            elif "type: odoo_invoice" in content:
                if not self.rate_limiter.check_and_increment("odoo_action"):
                    return
                if self.odoo_skill.connect():
                    self.odoo_skill.create_draft_invoice(1, 100.0, "AI Generated Invoice")
                    shutil.move(str(target_path), str(self.done_path / target_path.name))
                    self.processor.log_action("odoo_invoice", {"file": target_path.name},
                                              target="odoo", result="success",
                                              approval_status="approved", approved_by="human")

def ralph_wiggum_loop(processor: VaultProcessor):
    logger.info("🔁 Ralph Wiggum Persistence Loop Active.")
    while True:
        try:
            plans = list(processor.plans_path.glob("PLAN_*.md"))
            for plan in plans:
                content = plan.read_text(encoding='utf-8')
                if "- [ ]" in content:
                    logger.info(f"🔁 Ralph Wiggum: Continuing work on {plan.name}")
                    processor.process_plan_step(plan)
                    time.sleep(2)
        except Exception as e:
            logger.error(f"Error in Ralph Wiggum loop: {e}")
        time.sleep(30)

def run_orchestrator(vault_path: str):
    logger.info(f"🚀 MASTER ORCHESTRATOR STARTING: Monitoring {vault_path}")
    processor = VaultProcessor(vault_path)
    event_handler = VaultOrchestrator(Path(vault_path))
    observer = Observer()
    observer.schedule(event_handler, vault_path, recursive=True)
    persistence_thread = threading.Thread(target=ralph_wiggum_loop, args=(processor,), daemon=True)
    persistence_thread.start()
    observer.start()
    try:
        while True: time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    VAULT = REPO_ROOT / "AI_Employee_Vault"
    run_orchestrator(str(VAULT))
