# Phase 0 Research: Platinum Tier — Cloud + Local AI Employee

**Feature**: `004-platinum-cloud-local`
**Date**: 2026-03-25
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## R-001: Git Vault Sync Strategy

**Decision**: `git pull --rebase` + `*.md merge=union` driver in `.gitattributes`

**Rationale**:
- Rebase keeps a linear history; avoids noisy merge commits in a single-vault async workflow
- The `union` merge driver for `*.md` files concatenates divergent hunks instead of inserting conflict markers — safe for task files with distinct YAML frontmatter blocks
- Conflict markers in Obsidian break Markdown rendering; union avoids them

**Alternatives considered**:
- Three-way merge: Creates conflict markers in `.md` files; requires human intervention in Obsidian — rejected
- `git pull --ff-only`: Strict linear history, but blocks when both agents push simultaneously — rejected

**Edge cases**:
- NFS delays: Add 2–3s grace period after pull before scanning `Needs_Action/`
- Windows CRLF: Set `core.autocrlf=true` in vault repo to prevent spurious diffs

---

## R-002: Claim-by-Move Atomicity

**Decision**: Use `pathlib.Path.rename()` (wraps `os.rename()`) validated to same filesystem; reject cross-device moves loudly.

**Rationale**:
- On Linux: `os.rename()` is atomic (POSIX spec) when source and destination are on the same filesystem
- On Windows: `os.rename()` is atomic via `MoveFileEx` on same volume; `shutil.move()` falls back to copy+delete when crossing devices (not atomic)
- Validating `os.stat().st_dev` equality before rename guarantees atomicity on both platforms

**Alternatives considered**:
- `shutil.move()` everywhere: Falls back to non-atomic copy+delete on cross-device — rejected for production
- Advisory lockfile (`.md.lock`): Adds complexity with no benefit when rename is already atomic — rejected

**Edge cases**:
- NFS mounts: `st_dev` is identical across NFS shares but `rename()` is not atomic — document as unsupported; vault must be on local disk
- Windows file-in-use: Wrap rename in try/except; retry with 1s backoff (max 3 attempts)

---

## R-003: Stale Task Recovery

**Decision**: YAML frontmatter `claimed_at` field + background reaper thread polling every 5 minutes.

**Rationale**:
- File `mtime` is unreliable — reset by copies, Git operations, sync tools, and backups
- `claimed_at` is already set in the YAML frontmatter when the file is moved to `In_Progress/`; it survives all file operations
- YAML timestamp is human-readable in Obsidian and debuggable without OS tools

**Recovery flow**:
```
Every 5 minutes:
  Scan In_Progress/cloud/ and In_Progress/local/
  Parse YAML claimed_at for each .md file
  If (now - claimed_at) > STALE_TASK_TIMEOUT_MINUTES (default: 30):
    Move back to Needs_Action/
    Append stale_recovery_count++ to frontmatter
    Log to Logs/YYYY-MM-DD.json with action_type=stale_recovery
```

**Alternatives considered**:
- File mtime only: Unreliable on NFS and after Git sync — rejected
- Heartbeat file per task: Over-engineered for file-based workflow — rejected

---

## R-004: Pre-Push Git Hook for Secret Blocking

**Decision**: Shell script in `.githooks/pre-push` scanning `git diff --cached --name-only`; activated via `git config core.hooksPath .githooks`.

**Rationale**:
- Pre-push hook runs after commit but before push; blocking here is the last line of defence
- `git diff --cached` lists staged files (what will be pushed); scanning filenames with grep is reliable and fast
- Storing in `.githooks/` (not `.git/hooks/`) allows the hook to be version-controlled and applied automatically via `git config core.hooksPath`

**Patterns blocked**: `.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`, `processed_emails.txt`, `processed_chats.txt`

**Alternatives considered**:
- Full commit diff scan (`git diff HEAD~1 HEAD`): Catches past commits too late (already committed) — rejected
- Client-side pre-commit hook: Runs before commit; useful but does not protect against manual `--no-verify` commits — use as additional layer only

---

## R-005: Health Check Design

**Decision**: File-based `Logs/health.json` written every 60 seconds; PM2 monitors via external `cron` check on file mtime.

**Rationale**:
- No additional dependencies (no Flask/FastAPI port needed)
- Both agents can read each other's health files (Cloud reads `Logs/health_cloud.json`, Local reads `Logs/health_local.json`)
- File survives process restart; stale mtime indicates crashed process
- PM2 `--max-restarts` + `watch` on a specific file provides equivalent monitoring

**Health file schema**:
```json
{
  "agent": "cloud | local",
  "timestamp": "ISO8601",
  "pid": 12345,
  "status": "running | degraded | error",
  "last_task": "FILE_xxx.md",
  "queue_depth": 3,
  "last_sync": "ISO8601",
  "vault_path": "/path/to/vault"
}
```

**Alternatives considered**:
- HTTP `/health` endpoint: Adds port management, network binding, and process lifecycle complexity — overkill for single-machine agent — rejected for Phase 1
- PM2 built-in metrics: Only available in PM2 Plus (paid) — rejected

---

## R-006: Cloud VM Platform

**Decision**: Oracle Cloud Always Free Tier — Ampere A1 (ARM) — 4 OCPU, 24 GB RAM, 200 GB storage.

**Rationale**:
- 4 OCPU / 24 GB RAM comfortably fits: Python orchestrator + PM2 + Odoo Community + PostgreSQL + Caddy
- Lifetime free (no credit card expiry risk); 10 TB/month outbound data transfer included
- ARM (aarch64) has full support for Python 3.13, PostgreSQL 15, Odoo Community, Docker

**Gotchas**:
- Ampere instances are often oversubscribed; provision in multiple regions if first choice fails
- Oracle may reclaim VMs with <20% CPU over 7 days — ensure watchers loop actively (they do via `time.sleep(60)`)

**Alternatives considered**:
- AWS EC2 t3.micro (1 GB RAM): Insufficient for Odoo + orchestrator simultaneously — rejected
- DigitalOcean: $6/month; cost not justified when Oracle Free covers the stack — rejected
- Hetzner CAX11 (ARM): €3.29/month; good alternative if Oracle capacity unavailable

---

## R-007: Odoo Deployment Method

**Decision**: Docker Compose (Odoo Community + PostgreSQL 15 + Caddy) on the Cloud VM.

**Rationale**:
- Container isolation: Odoo, database, and proxy run independently; one crash does not affect others
- Backup simplicity: Named Docker volumes for PostgreSQL data + Odoo filestore; single `pg_dump` command
- Portability: Entire stack moveable via `docker-compose.yml` + volume snapshots
- Caddy in the compose handles automatic HTTPS (Let's Encrypt) with zero configuration

**Alternatives considered**:
- Native apt install: No isolation; system package conflicts; harder to upgrade — rejected
- Kubernetes: Overkill for single-VM deployment — rejected

---

## R-008: HTTPS / Reverse Proxy

**Decision**: Caddy with automatic HTTPS (Let's Encrypt ACME protocol built in).

**Rationale**:
- Zero Certbot management: Caddy obtains, renews, and installs TLS certificates automatically when it detects a public domain
- Caddyfile is 4 lines vs 30+ lines for Nginx + Certbot + renewal cron
- Renewal is handled internally; no cron job needed

**Alternatives considered**:
- Nginx + Certbot: Battle-tested but requires manual cron setup and renewal scripts — rejected for new deployments
- Traefik: Container-first, adds complexity for single-domain use — rejected

---

## R-009: Database Backup Strategy

**Decision**: `pg_dump` (custom format) + `tar` filestore archive, daily at 2 AM via cron, 7-day rotation.

**Backup sequence**:
1. Stop Odoo container briefly (prevents hot-backup inconsistencies)
2. `pg_dump -U odoo -d odoo_db -F c | gzip > /backups/odoo_YYYY-MM-DD.dump.gz`
3. `tar -czf /backups/odoo_filestore_YYYY-MM-DD.tar.gz /var/lib/odoo/filestore/`
4. Start Odoo container
5. `find /backups/ -mtime +6 -delete` (keep last 7 days)
6. Sync latest backup to Oracle Object Storage (10 TB/month free)

**Alternatives considered**:
- Odoo's built-in ZIP backup (via web UI): Simpler but not scriptable for automation — use as supplemental only
- WAL archiving (point-in-time recovery): Enterprise-grade; overkill for single-instance — rejected

---

## R-010: PM2 Configuration for Python on Linux

**Decision**: PM2 with full venv interpreter path, `exec_mode: fork`, `PYTHONUNBUFFERED=1`.

**Key rules**:
- Script filename must NOT end in `.py` when using `interpreter` field, OR use `script: python` with `args`
- Always reference full path to venv Python: `/home/user/.venv/bin/python`
- Set `PYTHONUNBUFFERED=1` to prevent log buffering
- Use `uv run python` as interpreter command for uv-managed venvs

**Alternatives considered**:
- systemd user services: More verbose, requires root for system services — use as fallback on minimal VMs
- Supervisord: Heavier; PM2 already in use for Node.js ecosystem — rejected

---

## Summary of All Resolved Decisions

| ID | Topic | Decision |
|----|-------|----------|
| R-001 | Git sync | `pull --rebase` + `union` merge driver for `.md` |
| R-002 | Atomic claim | `pathlib.Path.rename()` same-filesystem, validated |
| R-003 | Stale recovery | YAML `claimed_at` + 5-min reaper thread |
| R-004 | Secret blocking | `.githooks/pre-push` + `git diff --cached` scan |
| R-005 | Health check | File-based `Logs/health_<agent>.json` every 60s |
| R-006 | Cloud VM | Oracle Always Free Ampere A1 (4 OCPU / 24 GB) |
| R-007 | Odoo deploy | Docker Compose (Odoo + PostgreSQL + Caddy) |
| R-008 | HTTPS | Caddy automatic Let's Encrypt |
| R-009 | DB backup | `pg_dump` + tar, daily cron, 7-day rotation |
| R-010 | PM2 Python | Full venv path, fork mode, PYTHONUNBUFFERED=1 |
