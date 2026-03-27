# Implementation Plan: Platinum Tier — Cloud + Local AI Employee

**Feature**: `004-platinum-cloud-local`
**Branch**: `004-platinum-cloud-local`
**Date**: 2026-03-25
**Status**: Ready for tasks

---

## Technical Context

### Stack

| Layer | Technology | Decision Source |
|-------|-----------|-----------------|
| Cloud VM | Oracle Always Free Ampere A1 (4 OCPU / 24 GB) | R-006 |
| Process manager | PM2 (fork mode, full venv path, PYTHONUNBUFFERED=1) | R-010 |
| Vault sync | Git — `pull --rebase` + `*.md merge=union` | R-001 |
| Atomic task claim | `pathlib.Path.rename()` — same-filesystem validated | R-002 |
| Stale recovery | YAML `claimed_at` + 5-min reaper thread | R-003 |
| Secret blocking | `.githooks/pre-push` + `git diff --cached` scan | R-004 |
| Health check | File-based `Logs/health_<agent>.json` every 60s | R-005 |
| Odoo deployment | Docker Compose (Odoo 17 + PostgreSQL 15 + Caddy) | R-007 |
| HTTPS | Caddy automatic Let's Encrypt | R-008 |
| DB backup | `pg_dump` custom format + tar, daily at 2 AM, 7-day rotation | R-009 |

### Architecture

```
┌─────────────────────────────────────┐      Git remote (GitHub)
│         CLOUD VM (Oracle ARM)        │ ◄──────────────────────► ┌──────────────────────────┐
│                                      │                           │    LOCAL MACHINE          │
│  ┌────────────┐   ┌────────────────┐ │      push/pull            │                           │
│  │ Gmail      │   │  Cloud Agent   │ │                           │  ┌───────────────────────┐│
│  │ Watcher    │──►│  Orchestrator  │─┼──── vault sync ──────────►│  │  Local Agent          ││
│  └────────────┘   └────────────────┘ │                           │  │  Orchestrator         ││
│                         │             │                           │  └───────────┬───────────┘│
│                   ┌─────▼──────────┐  │                           │              │             │
│                   │ Vault (local)  │  │                           │  ┌───────────▼───────────┐│
│                   │ Needs_Action/  │  │                           │  │  Vault (local)        ││
│                   │ In_Progress/   │  │                           │  │  Pending_Approval/    ││
│                   │   cloud/       │  │                           │  │  Approved/            ││
│                   │ Plans/         │  │                           │  │  In_Progress/local/   ││
│                   │ Pending_Appr./ │  │                           │  └───────────────────────┘│
│                   └────────────────┘  │                           │              │             │
│                                       │                           │  ┌───────────▼───────────┐│
│  ┌────────────────────────────────┐   │                           │  │  Action Executors     ││
│  │  Odoo Community + PostgreSQL   │   │                           │  │  Gmail send           ││
│  │  + Caddy (HTTPS)               │   │                           │  │  WhatsApp send        ││
│  └────────────────────────────────┘   │                           │  │  LinkedIn post        ││
└───────────────────────────────────────┘                           │  │  Odoo invoice post    ││
                                                                    │  └───────────────────────┘│
                                                                    │                           │
                                                                    │  Obsidian (owner UI)      │
                                                                    └──────────────────────────┘
```

---

## Constitution Check

Checked against `.specify/memory/constitution.md`:

| Principle | Status | Notes |
|-----------|--------|-------|
| HITL for sensitive actions | PASS | All Cloud actions write to Pending_Approval/; no direct send/post/pay |
| Secrets never in vault | PASS | .gitignore + pre-push hook blocks all credential files |
| Audit logging | PASS | FR-016 requires full schema logging to Logs/YYYY-MM-DD.json |
| Atomic concurrency | PASS | claim-by-move via `pathlib.Path.rename()` validated same-filesystem |
| Idempotent stale recovery | PASS | stale_recovery_count tracked; reaper thread every 5 min |
| Exponential backoff | PASS | FR-017 max 3 attempts for all network operations |
| DRY_RUN guard | PASS | All action scripts must respect DRY_RUN=true env var |

---

## Implementation Phases

### Phase 1 — Vault Infrastructure

**Goal**: Both agents can sync the vault via Git, create and move task files atomically, and recover stale tasks.

**Deliverables**:

1. **`PlatinumTier/scripts/vault_sync.py`** — Git sync utility
   - `pull_rebase()`: `git pull --rebase`; retry up to 3 times on conflict
   - `push()`: `git add -A && git commit -m <msg> && git push`
   - `sync_loop(interval=60)`: background thread calling pull every 60s
   - Uses `subprocess.run()` with `check=True`; raises `VaultSyncError` on failure

2. **`PlatinumTier/scripts/task_manager.py`** — Atomic file operations
   - `claim_task(task_path, agent_role) -> bool`: validates same-filesystem, calls `Path.rename()`, updates YAML frontmatter (`claimed_by`, `claimed_at`, `status=in_progress`), returns True on success / False if already claimed (FileNotFoundError)
   - `move_task(task_path, dest_folder) -> Path`: rename to destination folder
   - `update_frontmatter(task_path, updates: dict)`: read-modify-write YAML frontmatter
   - `list_tasks(folder) -> list[Path]`: returns sorted `.md` files in folder

3. **`PlatinumTier/scripts/stale_reaper.py`** — Stale task recovery
   - `reap_stale(vault_path, timeout_minutes=30)`: scans `In_Progress/cloud/` and `In_Progress/local/`; for each file where `now() - claimed_at > timeout`, moves back to `Needs_Action/`, increments `stale_recovery_count`, logs `action_type=stale_recovery`
   - `start_reaper_thread(vault_path)`: starts daemon thread calling `reap_stale()` every 5 minutes

4. **Vault folder structure bootstrap**
   - Both agents call `ensure_vault_structure(vault_path)` on startup: creates all required folders if missing
   - Writes `.gitkeep` files so empty folders are tracked

---

### Phase 2 — Cloud Agent

**Goal**: Cloud Agent runs 24/7 on the VM, processes Gmail, drafts replies/posts, creates approval files, syncs vault.

**Deliverables**:

5. **`PlatinumTier/scripts/cloud_agent.py`** — Main cloud process
   - Startup sequence: `git pull --rebase`, `ensure_vault_structure()`, start `sync_loop()`, start `reaper_thread()`, start `health_writer_thread()`, enter main watch loop
   - Main loop: scan `Needs_Action/` every 30s; for each `.md` file, attempt `claim_task()` → `process_task()` → `push()`
   - `process_task(task)`: dispatches to handler by `task.type` field

6. **`PlatinumTier/scripts/handlers/cloud_email_handler.py`** — Cloud email processing
   - `handle(task)`: read email body from task file, call Claude API for draft reply, write `APPROVE_REPLY_EMAIL_*.md` to `Pending_Approval/`, move task to `Plans/`
   - Writes full YAML frontmatter including `expires = now + APPROVAL_EXPIRY_HOURS`

7. **`PlatinumTier/scripts/handlers/cloud_social_handler.py`** — Cloud social post drafting
   - `handle(task)`: reads `Business_Goals.md`, calls Claude API for post draft, writes `APPROVE_POST_LINKEDIN/X/FACEBOOK_*.md` to `Pending_Approval/`

8. **`PlatinumTier/scripts/handlers/cloud_odoo_handler.py`** — Cloud Odoo draft-only
   - `handle(task)`: calls Odoo XML-RPC to create draft invoice (`state=draft`), writes `APPROVE_POST_INVOICE_*.md` to `Pending_Approval/` with `odoo_invoice_id`
   - On Odoo unreachable: log error, keep task in `Needs_Action/`, do not create approval file

9. **`PlatinumTier/scripts/health_writer.py`** — Health heartbeat
   - `write_health(vault_path, agent_role, status, last_task, queue_depth)`: writes `Logs/health_<agent>.json` every 60s
   - Schema matches `AgentHealthFile` contract in `data-model.md`

---

### Phase 3 — Local Agent

**Goal**: Local Agent polls vault, processes approvals after human sign-off, executes send/post/pay actions, writes health file.

**Deliverables**:

10. **`PlatinumTier/scripts/local_agent.py`** — Main local process
    - Startup: `git pull --rebase`, `ensure_vault_structure()`, start `sync_loop()`, start `reaper_thread()`, start `health_writer_thread()`, enter approval watch loop
    - Approval loop: scan `Approved/` every 10s; for each `APPROVE_*.md`, validate `expires`, call `execute_approval(approval_file)`, move to `Done/`, log action
    - Stale loop: also claim tasks from `Needs_Action/` for task types that require local execution (e.g. WhatsApp)

11. **`PlatinumTier/scripts/handlers/local_email_handler.py`** — Local email send
    - `execute(approval)`: parse `recipient`, `subject`, `message_body` from approval frontmatter; call Gmail API `send()`; respect `DRY_RUN`
    - On success: move approval to `Done/`, find linked task file, move to `Done/`

12. **`PlatinumTier/scripts/handlers/local_whatsapp_handler.py`** — Local WhatsApp send
    - `execute(approval)`: call existing `WhatsAppReply.send_message()`; respect `DRY_RUN`

13. **`PlatinumTier/scripts/handlers/local_social_handler.py`** — Local social publish
    - `execute(approval)`: dispatch to LinkedIn/X/Facebook/Instagram by `target` field; call existing social_post skills; respect `DRY_RUN`

14. **`PlatinumTier/scripts/handlers/local_odoo_handler.py`** — Local Odoo invoice post
    - `execute(approval)`: call Odoo XML-RPC `account.move.action_post()` on `odoo_invoice_id`; respect `DRY_RUN`
    - On success: update linked task frontmatter `odoo_status=posted`

---

### Phase 4 — Cloud VM Deployment

**Goal**: Cloud VM is fully provisioned with Odoo, Caddy HTTPS, PM2, daily backups.

**Deliverables**:

15. **`PlatinumTier/deploy/docker-compose.yml`** — Odoo + PostgreSQL + Caddy stack
    - Services: `db` (postgres:15), `odoo` (odoo:17), `caddy` (caddy:2)
    - Named volumes for persistence
    - Environment variables from `.env`

16. **`PlatinumTier/deploy/Caddyfile`** — Reverse proxy config
    - Single domain block: `ai.yourdomain.com { reverse_proxy odoo:8069 }`

17. **`PlatinumTier/deploy/backup.sh`** — Daily backup script
    - Stops Odoo briefly, runs `pg_dump`, tars filestore, starts Odoo, prunes 7-day-old backups
    - Cron: `0 2 * * * /home/ubuntu/odoo-deploy/backup.sh`

18. **`PlatinumTier/deploy/ecosystem.cloud.config.js`** — PM2 process definition
    - Cloud Agent process with full venv Python path and `ENV_FILE` env var

19. **`PlatinumTier/deploy/ecosystem.local.config.js`** — PM2 process definition for Local
    - Local Agent process with full venv Python path

---

### Phase 5 — Security Hardening

**Goal**: Pre-push hook, `.gitignore`, and `.gitattributes` correctly installed in the vault repo.

**Deliverables**:

20. **`PlatinumTier/deploy/vault-init.sh`** — Idempotent vault bootstrap script
    - Creates all required folders, `.gitattributes`, `.gitignore`, `.githooks/pre-push`
    - Runs `git config core.hooksPath .githooks`
    - Safe to run multiple times

---

## Key Invariants

These rules must hold in all code paths:

1. **Cloud Agent MUST NOT call**: `gmail.send()`, `whatsapp.send()`, `linkedin.post()`, `odoo.action_post()`, or any equivalent send/execute action.
2. **`Path.rename()` MUST be validated** same-filesystem before calling. If `source.stat().st_dev != dest_parent.stat().st_dev`: raise `CrossDeviceMoveError`.
3. **`expires:` MUST be checked** by Local Agent before executing any approval — even if the file is in `Approved/`. Expired = move to `Rejected/`, no execution.
4. **Every agent write to vault MUST be followed by** `git add -A && git commit && git push`.
5. **Health file MUST be written every 60s**. If writing fails, log to stderr but do not crash the agent.
6. **`DRY_RUN=true` MUST skip all external sends** in all action handlers; log what would have happened.
7. **Stale reaper MUST run every 5 minutes** as a daemon thread independent of the main processing loop.

---

## File Map

```
PlatinumTier/
├── scripts/
│   ├── cloud_agent.py              # Phase 2 — main cloud process
│   ├── local_agent.py              # Phase 3 — main local process
│   ├── vault_sync.py               # Phase 1 — git pull/push utilities
│   ├── task_manager.py             # Phase 1 — atomic file ops
│   ├── stale_reaper.py             # Phase 1 — stale task recovery
│   ├── health_writer.py            # Phase 2/3 — health heartbeat
│   └── handlers/
│       ├── cloud_email_handler.py  # Phase 2
│       ├── cloud_social_handler.py # Phase 2
│       ├── cloud_odoo_handler.py   # Phase 2
│       ├── local_email_handler.py  # Phase 3
│       ├── local_whatsapp_handler.py # Phase 3
│       ├── local_social_handler.py # Phase 3
│       └── local_odoo_handler.py   # Phase 3
└── deploy/
    ├── docker-compose.yml          # Phase 4
    ├── Caddyfile                   # Phase 4
    ├── backup.sh                   # Phase 4
    ├── ecosystem.cloud.config.js   # Phase 4
    ├── ecosystem.local.config.js   # Phase 4
    └── vault-init.sh               # Phase 5
```

---

## Acceptance Gates

Before marking the plan complete, all gates must pass:

- [ ] `vault_sync.py` pull/push cycle completes without error in local test
- [ ] `task_manager.claim_task()` tested for race: two threads claiming same file → exactly one succeeds
- [ ] `stale_reaper.py` recovers a file with `claimed_at` 31 min ago in integration test
- [ ] Cloud Agent creates approval file for test email within 5 min (Wi-Fi disabled on Local)
- [ ] Local Agent sends email within 60s of approval file appearing in `Approved/`
- [ ] Pre-push hook blocks `.env` file from being pushed
- [ ] `git ls-tree -r HEAD` shows no secret files after smoke test push
- [ ] `health_cloud.json` written within 65s of agent start; `health_local.json` same
- [ ] Odoo reachable via HTTPS with valid cert after Docker Compose deploy
- [ ] DRY_RUN=true run produces zero external sends and correct log entries

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Oracle VM capacity unavailable in chosen region | Medium | Provision in secondary region (Frankfurt, Singapore) as fallback |
| `Path.rename()` fails on NFS-mounted vault | Low | Document vault must be on local disk; validate `st_dev` match on startup |
| Git rebase conflict between Cloud and Local simultaneous pushes | Medium | Retry pull→rebase→push up to 3 times; if all fail, log and continue (vault remains usable locally) |
| Approval file expires while Local is offline long-term | Low | Configurable `APPROVAL_EXPIRY_HOURS`; Cloud re-drafts on next Gmail poll |
| WhatsApp session expires | Low | Local Agent flags `session_invalid` in health file; owner re-runs handshake |
