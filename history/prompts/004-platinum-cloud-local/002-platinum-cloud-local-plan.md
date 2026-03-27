---
id: 004-002
title: platinum-cloud-local-plan
stage: plan
date: 2026-03-25
surface: claude-code
model: claude-sonnet-4-6
feature: 004-platinum-cloud-local
branch: 004-platinum-cloud-local
user: owner
command: /sp.plan
labels: [platinum, cloud, local, dual-agent, vault-sync, odoo, git, pm2]
links:
  spec: specs/004-platinum-cloud-local/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-platinum-cloud-local/research.md
  - specs/004-platinum-cloud-local/data-model.md
  - specs/004-platinum-cloud-local/contracts/vault-task-schema.md
  - specs/004-platinum-cloud-local/contracts/approval-file-schema.md
  - specs/004-platinum-cloud-local/quickstart.md
  - specs/004-platinum-cloud-local/plan.md
  - history/prompts/004-platinum-cloud-local/002-platinum-cloud-local-plan.md
tests:
  - ""
---

## Prompt

Execute /sp.plan for 004-platinum-cloud-local. Generate all Phase 0 research and Phase 1 design artifacts for the Platinum tier dual-agent Cloud+Local architecture.

## Response snapshot

**Phase 0 — Research** (`research.md`):
- R-001: Git sync — `pull --rebase` + `*.md merge=union` driver in `.gitattributes`
- R-002: Atomic claim — `pathlib.Path.rename()` same-filesystem validated via `st_dev`
- R-003: Stale recovery — YAML `claimed_at` + 5-min background reaper thread
- R-004: Pre-push hook — `.githooks/pre-push` + `git diff --cached` scan for secrets
- R-005: Health check — file-based `Logs/health_<agent>.json` written every 60s
- R-006: Cloud VM — Oracle Always Free Ampere A1 (4 OCPU / 24 GB RAM)
- R-007: Odoo deploy — Docker Compose (Odoo 17 + PostgreSQL 15 + Caddy)
- R-008: HTTPS — Caddy automatic Let's Encrypt
- R-009: DB backup — `pg_dump` custom format + tar, daily cron at 2 AM, 7-day rotation
- R-010: PM2 Python — full venv path, fork mode, PYTHONUNBUFFERED=1

**Phase 1 — Design Artifacts**:
- `data-model.md`: VaultTask state machine (Needs_Action → In_Progress/{cloud,local} → Plans → Pending_Approval → Approved/Rejected → Done), YAML frontmatter schemas for VaultTask + ApprovalFile + AgentHealthFile, `.gitattributes` config, vault folder tree with new `In_Progress/cloud/` and `In_Progress/local/` Platinum additions
- `contracts/vault-task-schema.md`: full YAML schema, field definitions, status transition table, naming conventions, validation rules, body format
- `contracts/approval-file-schema.md`: full YAML schema for all approval types (email, whatsapp, social, odoo_invoice), expiry policy (24h default, configurable), lifecycle diagram, body format
- `quickstart.md`: 4-part setup guide — vault git repo init (with `.gitattributes`, `.githooks/pre-push`), Cloud VM provisioning (Oracle ARM + Docker Compose Odoo stack + PM2), Local machine setup, smoke test verification
- `plan.md`: 5-phase implementation plan (Vault Infrastructure, Cloud Agent, Local Agent, Cloud VM Deploy, Security Hardening), 19 deliverables, architecture diagram, constitution check, key invariants, file map, acceptance gates, risk table

## Outcome

- Impact: Full Platinum tier implementation plan documented; all Phase 0 + Phase 1 artifacts complete; unblocks /sp.tasks
- Tests: 10 acceptance gates defined in plan.md covering atomic claim race condition, stale recovery, end-to-end email flow, secret leak prevention, DRY_RUN behavior
- Files: research.md, data-model.md, contracts/vault-task-schema.md, contracts/approval-file-schema.md, quickstart.md, plan.md
- Next prompts: /sp.tasks 004-platinum-cloud-local, /sp.implement
- Reflection: The hardest invariant to enforce is the Cloud-Agent-never-sends rule — it must be structurally impossible (no send credentials on Cloud) not just a code convention. The vault-init.sh idempotent bootstrap script is the single most important deployment artifact.

## Evaluation notes (flywheel)

- Failure modes observed: `update-agent-context.sh` and `create-phr.sh` fail on Windows due to missing template path resolution — both scripts use Unix absolute paths incompatible with Windows Git Bash path translation
- Graders run and results (PASS/FAIL): constitution check all PASS; plan acceptance gates all defined
- Prompt variant (if applicable): ""
- Next experiment: test whether `Path.rename()` is truly atomic on Windows NTFS with two simultaneous processes (the research decision assumes POSIX — needs Windows validation in tasks)
