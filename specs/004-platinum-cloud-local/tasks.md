# Tasks: Platinum Tier — Cloud + Local AI Employee

**Feature**: `004-platinum-cloud-local`
**Branch**: `004-platinum-cloud-local`
**Input**: specs/004-platinum-cloud-local/plan.md, spec.md, data-model.md, contracts/
**Tests**: Not requested — no test tasks generated

**Organization**: Tasks grouped by user story. Each story is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story this task belongs to (US1–US5)
- No story label = Setup/Foundational/Polish phase

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create the PlatinumTier directory tree and install dependencies.

- [x] T001 Create PlatinumTier/ directory structure: `PlatinumTier/scripts/handlers/`, `PlatinumTier/deploy/`
- [x] T002 [P] Add PlatinumTier dependencies to requirements.txt: `pyyaml`, `gitpython` (fallback: subprocess), `python-dotenv`
- [x] T003 [P] Create `PlatinumTier/__init__.py` and `PlatinumTier/scripts/__init__.py` and `PlatinumTier/scripts/handlers/__init__.py`
- [x] T004 [P] Create `PlatinumTier/deploy/` directory with `.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core vault infrastructure that ALL user stories depend on. Nothing else starts until this phase is complete.

**Contains**: vault sync, atomic file ops, stale reaper, health writer, vault bootstrap — all from plan.md Phase 1 deliverables.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T00X Implement `PlatinumTier/scripts/vault_sync.py` with `pull_rebase()`, `push(commit_msg)`, `sync_loop(interval=60)` background thread; use `subprocess.run(['git', ...], check=True, cwd=vault_path)`; raise `VaultSyncError` on failure after 3 retries with exponential backoff
- [x] T00X Implement `PlatinumTier/scripts/task_manager.py` with `claim_task(task_path, agent_role) -> bool`: validate `source.stat().st_dev == dest_parent.stat().st_dev`, call `Path.rename()`, update YAML frontmatter (`claimed_by`, `claimed_at=now().isoformat()`, `status=in_progress`); catch `FileNotFoundError` → return False (already claimed by other agent)
- [x] T00X Implement `move_task(task_path, dest_folder) -> Path` and `update_frontmatter(task_path, updates: dict)` and `list_tasks(folder) -> list[Path]` in `PlatinumTier/scripts/task_manager.py` (same file as T006, complete the module)
- [x] T00X Implement `PlatinumTier/scripts/stale_reaper.py` with `reap_stale(vault_path, timeout_minutes=30)`: scan `In_Progress/cloud/` and `In_Progress/local/`, parse `claimed_at` from YAML, if `(now - claimed_at).total_seconds() / 60 > timeout` call `move_task()` back to `Needs_Action/`, increment `stale_recovery_count`, log `action_type=stale_recovery`; `start_reaper_thread(vault_path)` starts daemon thread every 5 min
- [x] T00X Implement `PlatinumTier/scripts/health_writer.py` with `write_health(vault_path, agent_role, status, last_task="", queue_depth=0)` writing JSON to `Logs/health_<agent_role>.json`; schema: `{agent, timestamp, pid, status, last_task, queue_depth, last_sync_push, last_sync_pull, vault_path}`; `start_health_thread(vault_path, agent_role)` writes every 60s as daemon thread
- [x] T01X Implement `ensure_vault_structure(vault_path)` function in `PlatinumTier/scripts/task_manager.py`: creates all required Platinum folders (`Needs_Action/`, `In_Progress/cloud/`, `In_Progress/local/`, `Plans/`, `Pending_Approval/`, `Approved/`, `Rejected/`, `Done/`, `Logs/`, `Briefings/`, `Inbox/drop_zone/`) with `.gitkeep` files; idempotent — safe to call on every startup
- [x] T01X [P] Create `PlatinumTier/scripts/exceptions.py` with custom exceptions: `VaultSyncError`, `CrossDeviceMoveError`, `ApprovalExpiredError`, `OdooConnectionError`

**Checkpoint**: vault_sync, task_manager, stale_reaper, health_writer all importable. `ensure_vault_structure()` creates correct folders.

---

## Phase 3: User Story 1 — Offline-Resilient Email Draft & Approval (Priority: P1) 🎯 MVP

**Goal**: Cloud Agent detects email while Local is offline, drafts reply, writes approval file. When Local returns online and owner approves in Obsidian, Local Agent sends the email and moves task to Done/.

**Independent Test**: Disable Wi-Fi on Local. Send test email. Re-enable Wi-Fi. Approve in Obsidian. Verify email sent and task in Done/ within 60s.

### Cloud-side: email detection and drafting

- [x] T01X [US1] Implement `PlatinumTier/scripts/handlers/cloud_email_handler.py` with `handle(task_path, vault_path, claude_client)`: read email body from task file markdown body, call Claude API to draft reply, write `APPROVE_REPLY_EMAIL_<msg_id>_<ts>.md` to `Pending_Approval/` with full YAML frontmatter (`type=email_approval`, `status=pending_approval`, `recipient`, `subject`, `message_body`, `created_at`, `expires=now+APPROVAL_EXPIRY_HOURS`, `claimed_by=cloud`, `approved_by=""`, `approved_at=""`); move task file to `Plans/`
- [x] T01X [US1] Implement `PlatinumTier/scripts/cloud_agent.py` main process: startup sequence (`pull_rebase()`, `ensure_vault_structure()`, `start_sync_loop()`, `start_reaper_thread()`, `start_health_thread()`); main loop every 30s scans `Needs_Action/` with `list_tasks()`; for each task calls `claim_task()`; dispatches to handler by `type` YAML field; after each write calls `push()`; handles `FileNotFoundError` from race loss gracefully (logs and continues)
- [x] T01X [US1] Wire email handler into cloud_agent.py dispatcher: `if task_type == "email": cloud_email_handler.handle(task_path, vault_path, claude_client)` — requires T012 and T013

### Local-side: approval processing and send

- [x] T01X [US1] Implement `PlatinumTier/scripts/handlers/local_email_handler.py` with `execute(approval_path, vault_path, gmail_service)`: parse `recipient`, `subject`, `message_body`, `expires` from approval frontmatter; check `datetime.fromisoformat(expires) > datetime.now(UTC)` — if expired raise `ApprovalExpiredError`; call Gmail API `users().messages().send()` with base64-encoded MIME message; on success move approval to `Done/`; find linked task file in `Plans/` by msg_id, move to `Done/`; update `status=done`; respect `DRY_RUN=true` (log + move without sending)
- [x] T01X [US1] Implement `PlatinumTier/scripts/local_agent.py` main process: startup sequence (`pull_rebase()`, `ensure_vault_structure()`, `start_sync_loop()`, `start_reaper_thread()`, `start_health_thread()`); approval loop every 10s scans `Approved/` for `APPROVE_*.md` files; validates `expires` field first (move to `Rejected/` if past); dispatches to handler by `type` field; after each write calls `push()`
- [x] T01X [US1] Wire email handler into local_agent.py dispatcher: `if approval_type == "email_approval": local_email_handler.execute(approval_path, vault_path, gmail_service)` — requires T015 and T016
- [x] T01X [US1] Add full audit logging to both cloud_agent.py and local_agent.py: every action calls `log_action(vault_path, action_type, actor, target, parameters, result, approval_status, approved_by)` writing to `Logs/YYYY-MM-DD.json` (append JSON lines); matches FR-016 schema: `{timestamp, action_type, actor, target, parameters, approval_status, approved_by, result}`

**Checkpoint**: US1 fully functional. Email offline → draft → approve in Obsidian → sent → Done/ in under 10 minutes (SC-007 gate).

---

## Phase 4: User Story 2 — Cloud-Side Social Post Drafting with Local Approval (Priority: P2)

**Goal**: Cloud Agent proactively drafts a LinkedIn/X/Facebook post from Business_Goals.md. Owner approves via Obsidian. Local Agent publishes the post.

**Independent Test**: Trigger Business Auditor manually. Verify draft appears in Pending_Approval/. Approve it. Verify post published from Local machine.

- [x] T01X [P] [US2] Implement `PlatinumTier/scripts/handlers/cloud_social_handler.py` with `handle(task_path, vault_path, claude_client)`: read `Business_Goals.md` content; call Claude API to generate platform-appropriate post draft; write `APPROVE_POST_LINKEDIN_<date>.md` (or X/Facebook variant) to `Pending_Approval/` with frontmatter (`type=linkedin_post|x_post|facebook_post`, `target`, `post_content`, `created_at`, `expires`); move task to `Plans/`
- [x] T02X [P] [US2] Implement `PlatinumTier/scripts/handlers/local_social_handler.py` with `execute(approval_path, vault_path)`: parse `target` and `post_content` from frontmatter; dispatch to existing `GoldTier/scripts/skills/linkedin_post.py`, `social_post.py` by target; check expiry first; respect `DRY_RUN`; move approval to `Done/` on success
- [x] T02X [US2] Wire social handlers into cloud_agent.py and local_agent.py dispatchers: add `proactive_task`/`social_post` task types → `cloud_social_handler.handle()` in cloud; add `linkedin_post|x_post|facebook_post|social_post` approval types → `local_social_handler.execute()` in local — requires T019, T020

**Checkpoint**: US2 functional. Social draft in Pending_Approval/ within 5 min of trigger. Approved post published by Local.

---

## Phase 5: User Story 3 — Claim-by-Move Concurrency Safety (Priority: P3)

**Goal**: When both Cloud and Local agents run simultaneously, exactly one claims each task. Stale In_Progress/ files are recovered after 30 minutes.

**Independent Test**: Start both agents, drop test task into Needs_Action/, verify exactly one PLAN_*.md created and no duplicate actions.

- [x] T02X [US3] Validate `claim_task()` cross-device guard in `PlatinumTier/scripts/task_manager.py`: add `if task_path.stat().st_dev != dest_folder.stat().st_dev: raise CrossDeviceMoveError(...)` before rename; add Windows retry wrapper (`try: rename; except PermissionError: sleep(1), retry x3`) per R-002 edge case — review T006 and update in-place
- [x] T02X [US3] Validate stale reaper integration in `PlatinumTier/scripts/stale_reaper.py`: confirm reaper daemon started in BOTH `cloud_agent.py` and `local_agent.py`; confirm `stale_recovery_count` incremented in frontmatter update; confirm `action_type=stale_recovery` logged to `Logs/YYYY-MM-DD.json`; add early-exit if `stale_recovery_count >= 5` (flag as permanently failed, move to `Done/` with `status=failed`) — review T008 and update in-place
- [x] T02X [US3] Add concurrent-startup guard in both agents: on startup scan `In_Progress/cloud/` (for local agent) and `In_Progress/local/` (for cloud agent) for files older than `STALE_TASK_TIMEOUT_MINUTES`; log count; do NOT immediately reap on startup — wait for reaper thread to handle (prevents thundering-herd reap on restart)

**Checkpoint**: US3 functional. Zero duplicate task executions across 20 consecutive test drops (SC-003 gate).

---

## Phase 6: User Story 4 — Odoo Draft-Only Accounting with Local Approval (Priority: P4)

**Goal**: Odoo Community runs on Cloud VM with HTTPS and daily backups. Cloud Agent creates draft invoices; Local Agent posts them after approval.

**Independent Test**: Trigger invoice task via file drop. Verify draft appears in Odoo (status=draft). Approve posting task. Verify invoice confirmed in Odoo.

### Odoo agent handlers

- [x] T02X [P] [US4] Implement `PlatinumTier/scripts/handlers/cloud_odoo_handler.py` with `handle(task_path, vault_path, odoo_conn)`: parse Odoo fields from task frontmatter (`odoo_partner_id`, `odoo_amount`); call Odoo XML-RPC `object.execute_kw(db, uid, pwd, 'account.move', 'create', [{...}])` to create draft invoice; on success update task frontmatter with `odoo_invoice_id` and `odoo_status=draft`; write `APPROVE_POST_INVOICE_<ref>_<ts>.md` to `Pending_Approval/`; on `OdooConnectionError`: log error, keep task in `Needs_Action/`, do NOT create approval file — per FR-004 and spec US4 acceptance scenario 3
- [x] T02X [P] [US4] Implement `PlatinumTier/scripts/handlers/local_odoo_handler.py` with `execute(approval_path, vault_path, odoo_conn)`: parse `odoo_invoice_id` from frontmatter; call Odoo XML-RPC `object.execute_kw(db, uid, pwd, 'account.move', 'action_post', [[invoice_id]])` to confirm invoice; update linked task frontmatter `odoo_status=posted`; move approval to `Done/`; respect `DRY_RUN`
- [x] T02X [US4] Wire Odoo handlers into cloud_agent.py and local_agent.py dispatchers: add `odoo_invoice` task type → `cloud_odoo_handler.handle()` in cloud; add `odoo_invoice` approval type → `local_odoo_handler.execute()` in local — requires T025, T026
- [x] T02X [US4] Implement Odoo connection helper in `PlatinumTier/scripts/odoo_client.py`: `connect(url, db, user, password) -> (models_proxy, uid)` using `xmlrpc.client`; wrap in `@with_retry(max_attempts=3)` from `Core/scripts/utils/retry_handler.py`; raise `OdooConnectionError` if all attempts fail

### Cloud VM deployment

- [x] T02X [US4] Create `PlatinumTier/deploy/docker-compose.yml` with three services: `db` (postgres:15, named volume `pgdata`), `odoo` (odoo:17, depends_on db, named volume `odoo_filestore`, port 8069), `caddy` (caddy:2, ports 80+443, mounts `Caddyfile` and named volume `caddy_data`); all services `restart: unless-stopped`
- [x] T03X [US4] Create `PlatinumTier/deploy/Caddyfile` with single domain block: `${ODOO_DOMAIN} { reverse_proxy odoo:8069 }` using env var for domain
- [x] T03X [US4] Create `PlatinumTier/deploy/backup.sh`: stops odoo container, runs `pg_dump -U odoo -d odoo_db -F c | gzip > /backups/odoo_$(date +%Y-%m-%d).dump.gz`, tars filestore, starts odoo, runs `find /backups/ -mtime +6 -delete`; add cron comment at top: `# Add to cron: 0 2 * * * /path/to/backup.sh`
- [x] T03X [P] [US4] Create `PlatinumTier/deploy/ecosystem.cloud.config.js` with PM2 app definition: `name: "cloud-agent"`, `script: "/home/ubuntu/ai-employ/.venv/bin/python"`, `args: "PlatinumTier/scripts/cloud_agent.py"`, `env: {PYTHONUNBUFFERED: "1"}`, `exec_mode: "fork"`, `max_restarts: 10`, `restart_delay: 5000`
- [x] T03X [P] [US4] Create `PlatinumTier/deploy/ecosystem.local.config.js` with same structure for local agent; script path uses local venv path with `${HOME}` placeholder

**Checkpoint**: US4 functional. Odoo reachable via HTTPS (SC-006). Draft invoice created on Cloud, confirmed after Local approval.

---

## Phase 7: User Story 5 — Vault Sync Security: Secrets Never Sync (Priority: P5)

**Goal**: No secret file (.env, tokens, sessions) ever appears in the remote Git repository under any scenario.

**Independent Test**: After vault sync push, run `git ls-tree -r HEAD --name-only` on remote — zero matches for secret patterns.

- [x] T03X [US5] Create `PlatinumTier/deploy/vault-init.sh` idempotent bootstrap script: creates all Platinum vault folders with `.gitkeep`; writes `.gitattributes` (`*.md merge=union`, `*.json merge=ours`); writes `.gitignore` (`.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`, `processed_emails.txt`, `processed_chats.txt`, `rate_limit_state.json`); creates `.githooks/pre-push` hook script that scans `git diff --cached --name-only` for forbidden patterns and exits 1 if found; runs `git config core.hooksPath .githooks`; marks `+x` on hook file; safe to run multiple times (idempotent)
- [x] T03X [US5] Verify vault-init.sh pre-push hook blocks forbidden files: trace through the hook logic to confirm `FORBIDDEN` regex matches all patterns in FR-012 (`.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`, `processed_emails.txt`, `processed_chats.txt`); add `rate_limit_state.json` to the blocked list per data-model.md
- [x] T03X [US5] Add vault sync security to `PlatinumTier/scripts/vault_sync.py`: on startup call `subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'], cwd=vault_path)` to ensure hook is active even if git clone bypassed vault-init.sh; log warning if `.githooks/pre-push` is missing (does not crash — hooks may be intentionally absent in CI)

**Checkpoint**: US5 functional. `git ls-tree -r HEAD` shows no secret files (SC-005 gate). Pre-push hook blocks test secret file.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Deployment docs, WhatsApp handler, env var completeness, and final validation.

- [x] T03X [P] Implement `PlatinumTier/scripts/handlers/local_whatsapp_handler.py` with `execute(approval_path, vault_path)`: parse `recipient` and `message_body` from frontmatter; call existing `SilverTier/scripts/skills/whatsapp_reply.WhatsAppReply.send_message()`; check expiry; respect `DRY_RUN`; wire into local_agent.py dispatcher for `whatsapp_reply` approval type
- [x] T03X [P] Create `.env.example` with all Platinum-tier env vars documented: `VAULT_PATH`, `AGENT_ROLE`, `AGENT_VERSION`, `VAULT_GIT_REMOTE`, `VAULT_SYNC_INTERVAL`, `STALE_TASK_TIMEOUT_MINUTES`, `APPROVAL_EXPIRY_HOURS`, `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`, `ODOO_DOMAIN`, `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, `GMAIL_QUERY`, `DRY_RUN` — with comments explaining each
- [x] T03X Add exponential backoff `@with_retry` decorator from `Core/scripts/utils/retry_handler.py` to all network calls in cloud_agent.py and local_agent.py: Gmail API calls, Odoo XML-RPC calls, social post API calls — per FR-017 (max 3 attempts)
- [x] T04X [P] Verify `Dashboard.md` single-writer rule: confirm only `local_agent.py` writes to `Dashboard.md`; add assertion in `cloud_agent.py` that raises `PermissionError` if it ever tries to write `Dashboard.md`
- [x] T04X Run quickstart.md smoke test validation: follow Part 4 steps (health check + end-to-end email flow + secret leak check) and confirm all pass; document any deviations in quickstart.md troubleshooting section

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup          — no dependencies; start immediately
Phase 2: Foundational   — depends on Phase 1; BLOCKS all user stories
Phase 3: US1 (P1)       — depends on Phase 2; can start as soon as foundational is done
Phase 4: US2 (P2)       — depends on Phase 2; can run in parallel with US1 after Phase 2
Phase 5: US3 (P3)       — depends on Phase 2 + T006/T008 (foundational); mostly validation tasks
Phase 6: US4 (P4)       — depends on Phase 2; Odoo handlers can run in parallel with US1/US2
Phase 7: US5 (P5)       — depends on Phase 1 only; vault-init.sh is independent of agents
Phase 8: Polish         — depends on all prior phases
```

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 complete. No dependency on other user stories. Delivers MVP.
- **US2 (P2)**: Requires Phase 2 complete. Uses same cloud_agent/local_agent from US1 (extends dispatchers). Independently testable.
- **US3 (P3)**: Requires T006 (claim_task) and T008 (stale_reaper) from Phase 2. Validates/hardens existing code — no new modules.
- **US4 (P4)**: Requires Phase 2 complete. Odoo handlers parallel with US1/US2. Deployment artifacts (T029–T033) are independent of agent code.
- **US5 (P5)**: Requires Phase 1 only. vault-init.sh is pure shell — no Python dependencies.

### Within Each User Story

- Cloud handler → Cloud agent wiring → Local handler → Local agent wiring → Audit logging
- Odoo handlers: client helper (T028) before handlers (T025, T026)
- Deployment (T029–T033) can run in parallel with Odoo handler code

### Parallel Opportunities

```bash
# Phase 2 — all foundational tasks can run in parallel across separate files:
Task: "vault_sync.py"         # T005
Task: "task_manager.py"       # T006, T007, T010
Task: "stale_reaper.py"       # T008
Task: "health_writer.py"      # T009
Task: "exceptions.py"         # T011

# Phase 3 — cloud-side and local-side can start in parallel:
Task: "cloud_email_handler.py"  # T012
Task: "local_email_handler.py"  # T015 (different file, no shared state)

# Phase 4 — cloud and local social handlers in parallel:
Task: "cloud_social_handler.py" # T019
Task: "local_social_handler.py" # T020

# Phase 6 — Odoo handlers and deployment artifacts fully parallel:
Task: "cloud_odoo_handler.py"         # T025
Task: "local_odoo_handler.py"         # T026
Task: "docker-compose.yml"            # T029
Task: "Caddyfile"                     # T030
Task: "ecosystem.cloud.config.js"     # T032
Task: "ecosystem.local.config.js"     # T033
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T011) — **CRITICAL, blocks everything**
3. Complete Phase 3: US1 Email Draft & Approval (T012–T018)
4. **STOP and VALIDATE**: Run quickstart.md Part 4 smoke test
5. End-to-end demo gate: email offline → draft → approve → send → Done/ in under 10 minutes (SC-007)

### Incremental Delivery

1. Setup + Foundational → vault infrastructure working
2. US1 → email offline/approval loop working → **hackathon MVP demo ready**
3. US2 → social post drafting added
4. US3 → concurrency hardening (validates existing code, low effort)
5. US4 → Odoo + Cloud VM deployed
6. US5 → secret protection hardened
7. Polish → WhatsApp, env docs, retry wiring

### Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|---------------|
| Phase 1: Setup | 4 | 3 |
| Phase 2: Foundational | 7 | 5 |
| Phase 3: US1 (P1) | 7 | 1 |
| Phase 4: US2 (P2) | 3 | 2 |
| Phase 5: US3 (P3) | 3 | 0 |
| Phase 6: US4 (P4) | 10 | 6 |
| Phase 7: US5 (P5) | 3 | 0 |
| Phase 8: Polish | 5 | 3 |
| **Total** | **42** | **20** |

---

## Notes

- **Cloud-Agent-never-sends invariant**: Enforce structurally — `cloud_agent.py` must NEVER import Gmail send, WhatsApp send, LinkedIn post, or Odoo `action_post`. Move all credentials for these to `.env.local` only.
- **DRY_RUN=true** must be the default in all development `.env` files. Set `DRY_RUN=false` explicitly for production.
- **`Path.rename()` on Windows**: Test the cross-device guard (T022) on NTFS — the `st_dev` check behaves differently on Windows network drives.
- Tasks T006/T007/T010 are in the same file (`task_manager.py`) — implement sequentially, not truly parallel.
- Commit after each checkpoint to create clean rollback points.
