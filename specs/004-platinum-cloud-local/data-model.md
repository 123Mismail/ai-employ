# Data Model: Platinum Tier — Cloud + Local AI Employee

**Feature**: `004-platinum-cloud-local`
**Date**: 2026-03-25

---

## Entity Overview

```
VaultTask ──────────────► ApprovalFile
   │                            │
   │ moves through              │ created by CloudAgent
   ▼                            ▼
FolderState              AgentHealthFile
   │
   ├── Needs_Action/
   ├── In_Progress/cloud/
   ├── In_Progress/local/
   ├── Plans/
   ├── Pending_Approval/
   ├── Approved/
   ├── Rejected/
   └── Done/
```

---

## 1. VaultTask

A `.md` file representing a single unit of work flowing through the vault.

### YAML Frontmatter Schema

```yaml
---
type: email | whatsapp | file_drop | proactive_task | odoo_invoice | social_post
source: Gmail | WhatsApp | Filesystem | Proactive
status: pending | in_progress | pending_approval | approved | rejected | done | stale_recovered
claimed_by: cloud | local | ""
claimed_at: "2026-03-25T10:30:00"   # ISO 8601, set on claim-by-move
stale_recovery_count: 0              # incremented on each stale recovery
agent_version: "1.0.0"
timestamp: "2026-03-25T10:25:00"    # created at
---
```

### State Machine

```
                    ┌─────────────────────────────────────────────────────┐
                    │                                                     │
[File Drop/Watcher] │                                                     │
        ↓           │                   stale timeout                    │
  Needs_Action/ ────┼──────────────────────────────────────────────────┐ │
        │           │                                                   │ │
  (claim-by-move)   │                                                   │ │
        ↓           │                                                   │ │
 In_Progress/       │                                                   │ │
  cloud/ or         │                                                   │ │
  local/            │                                                   │ │
        │           │                                                   │ │
  (AI reasoning)    │                                                   │ │
        ↓           │                                                   │ │
    Plans/          │                                                   │ │
        │           │                                                   │ │
  (draft created)   │                                                   │ │
        ↓           │                                                   │ │
 Pending_Approval/  │                                                   │ │
        │           │                                                   │ │
   (human drag)─────┼──────────────────────────────────────────────────┘ │
        ↓           │                                                     │
    Approved/ ──────┼──► Done/  (after Local executes action)            │
    Rejected/ ──────┼──► Done/  (after logging rejection)                │
                    │                                                     │
                    └─────────────────────────────────────────────────────┘
```

### Naming Convention

| Source | Pattern | Example |
|--------|---------|---------|
| Gmail | `EMAIL_<msg_id>_<timestamp>.md` | `EMAIL_19d2404c_20260325130615.md` |
| WhatsApp | `WHATSAPP_OWNER_<timestamp>.md` | `WHATSAPP_OWNER_20260325131000.md` |
| File drop | `FILE_<filename>_<timestamp>.md` | `FILE_invoice.pdf_20260325131200.md` |
| Proactive | `TASK_<type>_<date>.md` | `TASK_AUTO_POST_LINKEDIN_20260325.md` |
| Odoo invoice | `ODOO_INVOICE_<ref>_<timestamp>.md` | `ODOO_INVOICE_INV001_20260325.md` |

---

## 2. ApprovalFile

A `APPROVE_*.md` file written by the Cloud Agent into `Pending_Approval/`. The owner approves by moving it to `Approved/` in Obsidian.

### YAML Frontmatter Schema

```yaml
---
type: email_approval | whatsapp_reply | linkedin_post | social_post | odoo_invoice
status: pending_approval | approved | rejected
recipient: "user@example.com"          # for email/whatsapp types
subject: "RE: Invoice #123"            # for email type
target: linkedin | x | facebook | odoo # for social/odoo types
created_at: "2026-03-25T10:30:00"
expires: "2026-03-26T10:30:00"         # 24h default; enforced by Local Agent
claimed_by: cloud
approved_by: human | ""
approved_at: "" | "ISO8601"
---
```

### Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Email reply | `APPROVE_REPLY_EMAIL_<msg_id>_<ts>.md` | `APPROVE_REPLY_EMAIL_19d2_20260325.md` |
| WhatsApp reply | `APPROVE_REPLY_WHATSAPP_<ts>.md` | `APPROVE_REPLY_WHATSAPP_20260325.md` |
| LinkedIn post | `APPROVE_POST_LINKEDIN_<date>.md` | `APPROVE_POST_LINKEDIN_20260325.md` |
| Social post | `APPROVE_POST_SOCIAL_<ts>.md` | `APPROVE_POST_SOCIAL_20260325.md` |
| Odoo invoice | `APPROVE_POST_INVOICE_<ref>_<ts>.md` | `APPROVE_POST_INVOICE_INV001.md` |

---

## 3. AgentHealthFile

A JSON file written every 60 seconds by each agent to signal it is alive.

### Schema

```json
{
  "agent": "cloud | local",
  "timestamp": "2026-03-25T10:30:00",
  "pid": 12345,
  "status": "running | degraded | error",
  "last_task": "FILE_invoice.pdf_20260325.md",
  "queue_depth": 3,
  "last_sync_push": "2026-03-25T10:29:45",
  "last_sync_pull": "2026-03-25T10:29:50",
  "vault_path": "/home/user/AI_Employee_Vault"
}
```

### Location

- Cloud Agent: `Logs/health_cloud.json`
- Local Agent: `Logs/health_local.json`

Staleness threshold: if `timestamp` is older than 3 minutes, the process is considered crashed.

---

## 4. VaultSync (Git Repository State)

The vault's Git repository is a separate repo from the code repo, containing only Markdown state.

### `.gitattributes`

```
*.md merge=union
*.json merge=ours
```

- `*.md merge=union`: Concatenates divergent hunks; avoids conflict markers in Obsidian
- `*.json merge=ours`: Log files are agent-local; keep local version on conflict (no cross-agent log merging)

### `.githooks/pre-push`

Blocks push if any of these patterns are detected in staged files:
- `.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`
- `processed_emails.txt`, `processed_chats.txt`, `rate_limit_state.json`

### Sync Cadence

| Event | Cloud Agent | Local Agent |
|-------|-------------|-------------|
| After writing any file | `git add -A && git commit && git push` | `git add -A && git commit && git push` |
| On startup | `git pull --rebase` | `git pull --rebase` |
| Periodic pull | Every 60s | Every 60s |
| On conflict | Retry pull → rebase → push (max 3) | Same |

---

## 5. OdooRecord (ERP state, not in vault)

Odoo records are managed in the Odoo database on the Cloud VM. The vault contains only task files that reference Odoo record IDs.

### Invoice Task Frontmatter (reference only)

```yaml
---
type: odoo_invoice
odoo_invoice_id: 9999          # set after draft created
odoo_partner_id: 1
odoo_amount: 100.0
odoo_status: draft | posted
---
```

---

## 6. Vault Folder Structure (Platinum additions)

```
AI_Employee_Vault/
├── .gitattributes                # *.md merge=union, *.json merge=ours
├── .githooks/
│   └── pre-push                  # Secret file blocker
├── Dashboard.md                  # Single-writer: Local Agent only
├── Company_Handbook.md
├── Business_Goals.md
├── Needs_Action/                 # Both agents scan; first mover claims
├── In_Progress/                  # NEW: Platinum addition
│   ├── cloud/                    # Cloud-claimed tasks
│   └── local/                    # Local-claimed tasks
├── Plans/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Done/
├── Logs/
│   ├── YYYY-MM-DD.json           # Audit log (both agents append)
│   ├── health_cloud.json         # Cloud health heartbeat
│   ├── health_local.json         # Local health heartbeat
│   └── rate_limit_state.json     # Rate limiter state (Local only)
├── Briefings/
└── Inbox/
    └── drop_zone/                # File drop target (Local/Cloud)
```
