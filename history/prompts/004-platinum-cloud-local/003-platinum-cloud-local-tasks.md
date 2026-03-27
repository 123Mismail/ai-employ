---
id: 004-003
title: platinum-cloud-local-tasks
stage: tasks
date: 2026-03-25
surface: claude-code
model: claude-sonnet-4-6
feature: 004-platinum-cloud-local
branch: 004-platinum-cloud-local
user: owner
command: /sp.tasks
labels: [platinum, cloud, local, dual-agent, tasks, vault-sync, odoo]
links:
  spec: specs/004-platinum-cloud-local/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-platinum-cloud-local/tasks.md
  - history/prompts/004-platinum-cloud-local/003-platinum-cloud-local-tasks.md
tests:
  - ""
---

## Prompt

Generate tasks.md for 004-platinum-cloud-local based on plan.md, spec.md, data-model.md, and contracts/.

## Response snapshot

Generated `specs/004-platinum-cloud-local/tasks.md` with 42 tasks across 8 phases:

- **Phase 1 (Setup)**: 4 tasks — PlatinumTier directory structure, dependencies, init files
- **Phase 2 (Foundational)**: 7 tasks — vault_sync.py, task_manager.py, stale_reaper.py, health_writer.py, exceptions.py, ensure_vault_structure()
- **Phase 3 (US1 P1 — Email)**: 7 tasks — cloud_email_handler.py, cloud_agent.py, local_email_handler.py, local_agent.py, dispatcher wiring, audit logging
- **Phase 4 (US2 P2 — Social)**: 3 tasks — cloud_social_handler.py, local_social_handler.py, dispatcher wiring
- **Phase 5 (US3 P3 — Concurrency)**: 3 tasks — cross-device guard validation, stale reaper integration checks, startup guard
- **Phase 6 (US4 P4 — Odoo+Deploy)**: 10 tasks — cloud/local Odoo handlers, odoo_client.py, docker-compose.yml, Caddyfile, backup.sh, PM2 configs
- **Phase 7 (US5 P5 — Secrets)**: 3 tasks — vault-init.sh, pre-push hook validation, vault_sync.py security check
- **Phase 8 (Polish)**: 5 tasks — WhatsApp handler, .env.example, retry wiring, Dashboard single-writer assertion, smoke test

20 of 42 tasks marked [P] (parallelizable). MVP scope = Phases 1–3 (US1 only, 18 tasks). Hackathon demo gate = SC-007 (end-to-end email flow under 10 min).

## Outcome

- Impact: 42 actionable tasks covering full Platinum tier implementation; immediately executable by /sp.implement
- Tests: No test tasks generated (not requested in spec); acceptance gates documented per story phase
- Files: specs/004-platinum-cloud-local/tasks.md
- Next prompts: /sp.implement 004-platinum-cloud-local
- Reflection: Phase 2 (Foundational) is the true critical path — 7 tasks before any user story can start. The Cloud-Agent-never-sends invariant should be enforced by import structure (credentials only in .env.local), not just convention.

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh returns empty AVAILABLE_DOCS on Windows (path translation issue) — worked around by using already-loaded context
- Graders run and results (PASS/FAIL): all 42 tasks have checkbox + ID + description + file path; all US-phase tasks have [Story] label
- Prompt variant (if applicable): ""
- Next experiment: split vault_sync.py into two tasks (pull utilities vs. sync_loop) to enable true parallelism with task_manager.py in Phase 2
