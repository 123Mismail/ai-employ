---
id: PHR-005-003
title: tasks-linkedin-engagement
stage: tasks
date: 2026-03-26
surface: project
model: claude-sonnet-4-6
feature: 005-linkedin-engagement
branch: 005-linkedin-engagement
user: human
command: /sp.tasks
labels: [linkedin, engagement, tasks, playwright, rate-limiting, hitl]
links:
  spec: specs/005-linkedin-engagement/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/005-linkedin-engagement/tasks.md
tests: []
---

## Prompt

/sp.tasks — Generate dependency-ordered task list for 005-linkedin-engagement (LinkedIn Advanced Engagement: reply to comments, comment on AI posts, auto-connect).

## Response snapshot

Generated `specs/005-linkedin-engagement/tasks.md` with 49 tasks across 6 phases:

- Phase 1 (Setup): 3 tasks — env vars, deduplication files, rate state JSON
- Phase 2 (Foundation): 4 tasks — `linkedin_rate_limiter.py` with RateLimiter + SessionLock classes (BLOCKING prerequisite for all phases)
- Phase 3 (US1 Reply): 15 tasks — watcher notification polling, cloud reply handler, local reply handler, PM2 registration — MVP scope
- Phase 4 (US2 Comment): 11 tasks — feed scanner extension, cloud comment handler, local comment handler with 10/day rate limit
- Phase 5 (US3 Connect): 11 tasks — people search extension, cloud connect handler (≤300 char notes), local connect handler with 5/day limit + 30s delay
- Phase 6 (Polish): 5 tasks — dashboard update, PM2 persistence, smoke test

MVP = Phase 1+2+3 (22 tasks). Delivers reply flow end-to-end with zero rate-limit risk.

## Outcome

- Impact: 49 actionable tasks enabling safe, phased LinkedIn engagement automation — each phase independently testable
- Tests: Manual end-to-end acceptance test defined per phase; no automated tests (not requested in spec)
- Files: specs/005-linkedin-engagement/tasks.md
- Next prompts: /sp.implement (start with MVP phases 1-3)
- Reflection: Foundation phase (T004-T007) is the critical path — RateLimiter and SessionLock must be solid before any handler. Build order enforces safety: own-content replies first, outbound second, connection requests last.

## Evaluation notes (flywheel)

The `can_execute()` check in local handlers deliberately leaves files in `Approved/` when limit is reached (not Rejected). This means approved items auto-execute the next day when counters reset — correct behaviour for a daily queue.
