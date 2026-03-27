---
id: PHR-005-002
title: plan-linkedin-engagement
stage: plan
date: 2026-03-26
surface: project
model: claude-sonnet-4-6
feature: 005-linkedin-engagement
branch: 005-linkedin-engagement
user: human
command: /sp.plan
labels: [linkedin, engagement, plan, playwright, rate-limiting, hitl, session-lock]
links:
  spec: specs/005-linkedin-engagement/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/005-linkedin-engagement/plan.md
  - specs/005-linkedin-engagement/research.md
  - specs/005-linkedin-engagement/data-model.md
  - specs/005-linkedin-engagement/quickstart.md
  - specs/005-linkedin-engagement/contracts/file-contracts.md
tests: []
---

## Prompt

/sp.plan — Generate implementation plan for 005-linkedin-engagement (LinkedIn Advanced Engagement: reply to comments, comment on AI posts, auto-connect with AI people). Safe, rate-limited, HITL-gated.

## Response snapshot

Generated 5 planning artifacts:

**research.md** — 10 architectural decisions resolved:
- Single watcher process (not 3 separate) to avoid Playwright session conflicts
- File-based session lock (PID + aliveness check + 60s timeout)
- Notification page polling for own-post comments
- Feed page JS evaluate for AI post discovery (max 5/cycle)
- People search URL with 2nd-degree filter (max 3/cycle)
- Rate state JSON file with atomic write + midnight reset
- Flat-text deduplication registries (same pattern as Gmail)
- Cloud/local agent routing extended with 3 new type handlers each
- Human-like interaction: type(), scroll-into-view, 3-8s random delays
- CRITICAL account_paused flag cleared only by human

**data-model.md** — 5 entities: LinkedInEngagementTask (3 sub-types), EngagementApproval (3 sub-types), RateLimitState, DeduplicationRegistry, SessionLock. Full state machine diagram.

**plan.md** — 3 implementation phases (P1 reply → P2 comment → P3 connect). New files: linkedin.py watcher, 6 handlers, linkedin_rate_limiter.py shared utility. Modified files: cloud_agent.py, local_agent.py, ecosystem.config.js.

**contracts/file-contracts.md** — 5 file contracts: task creation, approval creation, local execution, rate limit state, session lock protocol.

**quickstart.md** — Step-by-step setup, test triggers for each phase, monitoring commands, account_paused recovery procedure.

## Outcome

- Impact: Complete implementation blueprint for all 3 LinkedIn engagement features with safety architecture preventing account bans
- Tests: Each phase independently testable; quickstart includes manual trigger method for each
- Files: 5 planning artifacts across specs/005-linkedin-engagement/
- Next prompts: /sp.tasks to generate dependency-ordered task list
- Reflection: The RateLimiter + SessionLock shared utility is the critical foundation — must be built and tested before any handler. Phase ordering (P1→P2→P3) is safety-driven: start with own-content actions before outbound.

## Evaluation notes (flywheel)

Key design decision: `account_paused` flag can only be cleared by human (manual JSON edit). This is intentional — no automated recovery from a LinkedIn security challenge. This matches the constitution's HITL mandate for sensitive operations.
