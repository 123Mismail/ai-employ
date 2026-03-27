import os
import re
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BusinessAuditor")

class BusinessAuditor:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.done_path = self.vault_path / "Done"
        self.briefings_path = self.vault_path / "Briefings"
        self.goals_path = self.vault_path / "Business_Goals.md"

    def run_weekly_audit(self):
        """Perform full audit, generate briefing, and create proactive tasks."""
        print("🔍 Starting Business Audit & Strategy Layer...")
        self.check_proactive_tasks()
        
        # 1. Gather data from Done folder (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        completed_tasks = []
        revenue_detected = 0.0
        
        if self.done_path.exists():
            for file in self.done_path.glob("*.md"):
                # Get file stats
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime > week_ago:
                    content = file.read_text(encoding='utf-8')
                    completed_tasks.append(file.name)
                    
                    # Simple regex to find currency values if they exist
                    prices = re.findall(r"\$(\d+(?:\.\d{2})?)", content)
                    for price in prices:
                        revenue_detected += float(price)

        # 2. Read current goals
        goals_content = ""
        if self.goals_path.exists():
            goals_content = self.goals_path.read_text(encoding='utf-8')

        # 3. Generate Briefing
        timestamp = datetime.now().strftime("%Y-%m-%d")
        briefing_filename = f"{timestamp}_Monday_Briefing.md"
        briefing_file = self.briefings_path / briefing_filename
        
        briefing_body = f"""# Monday Morning CEO Briefing: {timestamp}

## 📊 Executive Summary
This week, the AI Employee completed **{len(completed_tasks)}** tasks. 
Total revenue detected from processed items: **${revenue_detected:,.2f}**.

## ✅ Achievements (Last 7 Days)
{self._format_task_list(completed_tasks)}

## 🎯 Progress Against Goals
{self._extract_goals_section(goals_content)}

## 🚀 Proactive Suggestions
- **Revenue**: You are at {(revenue_detected/10000)*100 if 10000 > 0 else 0}% of your $10,000 monthly goal.
- **Efficiency**: {self._generate_tip(len(completed_tasks))}

---
*Generated autonomously by Gold-Tier Auditor Skill*
"""
        briefing_file.write_text(briefing_body, encoding='utf-8')
        print(f"✅ Briefing generated: {briefing_file.name}")
        return briefing_file

    def _format_task_list(self, tasks):
        if not tasks: return "*No tasks completed this week.*"
        return "\n".join([f"- {t}" for t in tasks])

    def _extract_goals_section(self, content):
        if "## Key Metrics" in content:
            return "##" + content.split("## Key Metrics")[1].split("##")[0]
        return "*Goal metrics not found in Business_Goals.md*"

    def _generate_tip(self, count):
        if count > 10: return "High productivity week! Consider delegating more drafting to me."
        if count < 3: return "Quiet week. Should I check LinkedIn for new lead generation opportunities?"
        return "Steady progress maintained."

    def check_proactive_tasks(self):
        """Check goals and create tasks in Needs_Action if missing."""
        print("🧠 Checking for proactive business tasks...")
        
        # 1. LinkedIn Daily Post Goal
        today_str = datetime.now().strftime("%Y%m%d")
        posted_today = False
        
        # Check Done folder for any LinkedIn action today
        if self.done_path.exists():
            for file in self.done_path.glob("*LINKEDIN*"):
                if today_str in file.name:
                    posted_today = True
                    break
        
        if not posted_today:
            needs_action_path = self.vault_path / "Needs_Action"
            task_file = needs_action_path / f"TASK_AUTO_POST_LINKEDIN_{today_str}.md"
            if not task_file.exists():
                content = f"""---
type: proactive_task
target: linkedin
priority: medium
timestamp: {datetime.now().isoformat()}
---
# Proactive Task: Daily LinkedIn Post
Business goals require 1 LinkedIn post daily. No post detected for today.

## Instruction
1. Smart Agent should draft a relevant AI/Business update.
2. Move to Pending_Approval for CEO review.
"""
                task_file.write_text(content, encoding='utf-8')
                print(f"🚀 Proactive task created: {task_file.name}")
            else:
                print("ℹ️ LinkedIn task already queued.")
        else:
            print("✅ LinkedIn post already completed for today.")

def run_scheduled(vault_path: Path):
    """Run the audit daily and sleep until the next midnight."""
    auditor = BusinessAuditor(vault_path)
    while True:
        try:
            logger.info("Running scheduled business audit...")
            auditor.run_weekly_audit()
        except Exception as e:
            logger.error(f"Audit failed: {e}")

        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(f"Next audit scheduled in {sleep_seconds / 3600:.1f} hours.")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).parent.parent.parent.parent
    run_scheduled(REPO_ROOT / "AI_Employee_Vault")
