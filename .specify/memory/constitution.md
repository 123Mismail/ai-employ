# Personal AI Employee Constitution - Hackathon 0 Edition

## 1. Core Principles (The Digital FTE Mandate)

### Local-First, Agent-Driven, HITL
The system must be built for autonomy while keeping the human in control. Privacy is non-negotiable. Data stays local in the Obsidian Vault. Sensitive actions require Human-in-the-Loop (HITL) approval.

### Perception-Reasoning-Action Architecture
- **Perception**: Lightweight Python "Watchers" (Gmail, WhatsApp, Filesystem) drop .md files into `/Needs_Action/`.
- **Reasoning**: Claude Code (or Gemini) processes these files against the `Company_Handbook.md`.
- **Action**: MCP Servers execute external actions (Email, Browser, Banking).

### The "Monday Morning CEO Briefing"
The AI must be proactive, not just reactive. It must autonomously audit bank transactions, tasks, and business goals to generate weekly revenue and bottleneck reports.

## 2. Security & Privacy Architecture

### Credential Protection
- **Secrets**: Never store credentials in plain text or Obsidian. Use environment variables or local secret managers.
- **Isolaton**: Use a `.env` file (immediately added to `.gitignore`).
- **Cloud vs. Local**: Cloud agents only own triage/drafts. Local agents own payments, WhatsApp sessions, and final "send" actions.

### HITL Safety Gating
- **Sensitive Actions**: Payments, important emails, and social posts MUST create a file in `/Pending_Approval/`.
- **Explicit Approval**: No action is taken until the file is moved to `/Approved/`.

## 3. Operational Standards

### Persistence (Ralph Wiggum Loop)
Utilize a Stop hook pattern to keep agents iterating until a task is complete (moving the task file to `/Done/`).

### 24/7 Reliability
- **Watchers**: Use process managers (PM2) or watchdog scripts to ensure continuous operation.
- **Graceful Degradation**: If an API is down, queue the task; if a vault is locked, write to a temporary folder.

### Auditability
Every action must be logged in `/Vault/Logs/YYYY-MM-DD.json` with: timestamp, action_type, actor, target, approval_status, and result.

## 4. Achievement Tiers (Success Criteria)
All development must aim for:
- **Bronze**: Vault + Dashboard + 1 Watcher.
- **Silver**: 2+ Watchers + MCP Email + Cron Scheduling.
- **Gold**: Autonomous Accounting (Odoo) + Social Media Posting + Weekly Audit.
- **Platinum**: 24/7 Cloud/Local split + Syncing Vault.

**Version**: 1.1.0 | **Ratified**: 2026-03-16 | **Status**: ACTIVE
