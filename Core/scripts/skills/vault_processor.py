import os
import json
import shutil
import re
import sys
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values

# Root detection for modular imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))
ENV_PATH = REPO_ROOT / ".env"

from Core.scripts.skills.smart_agent import SmartAgent

class VaultProcessor:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.plans_path = self.vault_path / "Plans"
        self.done_path = self.vault_path / "Done"
        self.logs_path = self.vault_path / "Logs"
        self.pending_approval_path = self.vault_path / "Pending_Approval"
        self.dashboard_path = self.vault_path / "Dashboard.md"
         
        self.agent = SmartAgent(self.vault_path / "Company_Handbook.md")

    def list_new_tasks(self):
        return list(self.needs_action_path.glob("*.md"))

    def extract_meta(self, content, key):
        match = re.search(f"^{key}\\s*:\\s*[\"']?(.*?)[\"']?\\s*$", content, re.MULTILINE)
        return match.group(1) if match else "Unknown"

    def claim_task(self, task_file: Path):
        if not task_file.exists(): return None
        content = task_file.read_text(encoding='utf-8')
        is_email = "type: email" in content
        is_whatsapp = "type: whatsapp" in content
        plan_target = self.plans_path / task_file.name
        shutil.move(str(task_file), str(plan_target))
        
        if is_email:
            sender = self.extract_meta(content, "email_from") or self.extract_meta(content, "from")
            subject = self.extract_meta(content, "email_subject") or self.extract_meta(content, "subject")
            snippet = ""
            if "## Content Snippet" in content:
                snippet = content.split("## Content Snippet")[1].split("##")[0].strip()
            
            print(f"🧠 Smart Agent drafting email reply for {sender}...")
            ai_draft = self.agent.analyze_and_draft(snippet, {"source": "Gmail", "from": sender, "subject": subject})
            self.create_email_approval_file(task_file, sender, subject, ai_draft)
            self.update_dashboard(f"Smart Drafted email reply for: {sender}")
            
        elif is_whatsapp:
            sender = self.extract_meta(content, "from")
            # BUDGET SAFETY: Only draft if it's from the owner (self-chat)
            owner_name = os.getenv("WHATSAPP_OWNER_NAME", "Mine(You)").strip('"')
            
            if sender == owner_name or sender == "Mine(You)":
                print(f"🧠 Smart Agent drafting WhatsApp reply for {sender}...")
                ai_draft = self.agent.analyze_and_draft("New message from owner.", {"source": "WhatsApp", "from": sender})
                self.create_whatsapp_approval_file(task_file, sender, ai_draft)
                self.update_dashboard(f"Smart Drafted WhatsApp reply for: {sender}")
            else:
                print(f"⏭️ Skipping drafting for non-owner WhatsApp message: {sender}")
                self.create_multi_step_plan(task_file) # Just create a generic plan, no AI draft
        elif "type: proactive_task" in content:
            target = self.extract_meta(content, "target")
            if target == "linkedin":
                print("🧠 Smart Agent drafting PROACTIVE LinkedIn post...")
                ai_draft = self.agent.analyze_and_draft("Draft a timely update about AI agents or MCP for my LinkedIn feed.", {"source": "ProactiveGoal", "target": "LinkedIn"})
                self.create_linkedin_approval_file(task_file, ai_draft)
                self.update_dashboard("Smart Drafted Proactive LinkedIn Post")
        else:
            self.create_multi_step_plan(task_file)
            self.update_dashboard(f"Created multi-step plan: {task_file.name}")
        
        self.log_action(
            "claim_task",
            {"task": task_file.name, "is_email": is_email, "is_whatsapp": is_whatsapp},
            target=task_file.name,
            result="success",
            approval_status="auto",
            approved_by="system",
        )
        return plan_target

    def create_linkedin_approval_file(self, task_file: Path, draft_content: str):
        approval_filename = f"APPROVE_POST_{task_file.name}"
        approval_path = self.pending_approval_path / approval_filename
        content = f"---\ntype: linkedin_post\nstatus: pending_approval\n---\n# Smart AI Post Draft\n{draft_content}\n\n## To Post\nMove this file to Approved folder."
        approval_path.write_text(content, encoding='utf-8')

    def create_whatsapp_approval_file(self, task_file: Path, sender: str, draft_content: str):
        approval_filename = f"APPROVE_REPLY_{task_file.name}"
        approval_path = self.pending_approval_path / approval_filename
        content = f"---\ntype: whatsapp_reply\nrecipient: \"{sender}\"\nstatus: pending_approval\n---\n# Smart AI Response\n{draft_content}\n\n## To Send\nMove this file to Approved folder."
        approval_path.write_text(content, encoding='utf-8')

    def create_multi_step_plan(self, task_file: Path):
        plan_filename = f"PLAN_{task_file.stem}.md"
        plan_path = self.plans_path / plan_filename
        content = f"# Multi-Step Plan: {task_file.name}\n\n## Steps\n- [ ] T001 Analyze file content.\n- [ ] T002 Execute action.\n- [ ] T003 Log completion."
        plan_path.write_text(content, encoding='utf-8')

    def process_plan_step(self, plan_file: Path):
        content = plan_file.read_text(encoding='utf-8')
        steps = re.findall(r"- \[ \] (.*)", content)
        if not steps: return
        next_step = steps[0]
        updated_content = content.replace(f"- [ ] {next_step}", f"- [x] {next_step}", 1)
        plan_file.write_text(updated_content, encoding='utf-8')
        if "- [ ]" not in updated_content:
            self.update_dashboard(f"Completed all steps for: {plan_file.name}")
            shutil.move(str(plan_file), str(self.done_path / plan_file.name))
            orig_name = plan_file.name.replace("PLAN_", "")
            orig_path = self.plans_path / orig_name
            if orig_path.exists(): shutil.move(str(orig_path), str(self.done_path / orig_name))

    def create_email_approval_file(self, task_file: Path, sender: str, subject: str, draft_content: str):
        approval_filename = f"APPROVE_REPLY_{task_file.name}"
        approval_path = self.pending_approval_path / approval_filename
        content = f"---\ntype: email_approval\nrecipient: \"{sender}\"\nsubject: \"RE: {subject}\"\nstatus: pending_approval\n---\n# Smart AI Response\n{draft_content}\n\n## To Send\nMove this file to Approved folder."
        approval_path.write_text(content, encoding='utf-8')

    def update_dashboard(self, activity: str):
        if not self.dashboard_path.exists(): return
        content = self.dashboard_path.read_text(encoding='utf-8')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"- [{timestamp}] {activity}\n"
        if "## Recent Activity" in content:
            parts = content.split("## Recent Activity", 1)
            updated_content = parts[0] + "## Recent Activity\n" + new_entry + parts[1]
            self.dashboard_path.write_text(updated_content, encoding='utf-8')

    def log_action(self, action_type: str, details: dict, target: str = "",
                   result: str = "success", approval_status: str = "auto",
                   approved_by: str = "system"):
        log_file = self.logs_path / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": "ai_employee",
            "target": target,
            "parameters": details,
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result,
        }
        logs = []
        if log_file.exists():
            try:
                with open(log_file, "r", encoding='utf-8') as f: logs = json.load(f)
            except: logs = []
        logs.append(log_entry)
        with open(log_file, "w", encoding='utf-8') as f: json.dump(logs, f, indent=4)

if __name__ == "__main__":
    VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"
    processor = VaultProcessor(str(VAULT_PATH))
    tasks = processor.list_new_tasks()
    for task in tasks: processor.claim_task(task)
