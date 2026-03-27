---
id: PHR-005-green-001
title: linkedin-engagement-implementation
stage: green
date: 2026-03-26
surface: claude-code
model: claude-sonnet-4-6
feature: 005-linkedin-engagement
branch: 005-linkedin-engagement
user: owner
command: /sp.implement
labels: [linkedin, engagement, playwright, rate-limiter, hitl, silver-tier, platinum-tier]
links:
  spec: specs/005-linkedin-engagement/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - PlatinumTier/scripts/linkedin_rate_limiter.py
  - SilverTier/scripts/watchers/linkedin.py
  - PlatinumTier/scripts/handlers/cloud_linkedin_reply_handler.py
  - PlatinumTier/scripts/handlers/cloud_linkedin_comment_handler.py
  - PlatinumTier/scripts/handlers/cloud_linkedin_connect_handler.py
  - PlatinumTier/scripts/handlers/local_linkedin_reply_handler.py
  - PlatinumTier/scripts/handlers/local_linkedin_comment_handler.py
  - PlatinumTier/scripts/handlers/local_linkedin_connect_handler.py
  - PlatinumTier/scripts/cloud_agent.py
  - PlatinumTier/scripts/local_agent.py
  - ecosystem.config.js
  - AI_Employee_Vault/Logs/linkedin_rate_state.json
tests: []
---

## Prompt

/sp.implement — start

Execute the implementation plan defined in specs/005-linkedin-engagement/tasks.md.
Feature: LinkedIn Advanced Engagement — reply to comments on own posts, comment on AI posts in feed, auto-connect with AI startup people.
All features go through HITL approval flow (Pending_Approval → Approved → local agent executes).
Built on existing Platinum Tier architecture.

## Response snapshot

Implemented all 44 tasks across Phases 1–5 plus T046 of Phase 6:

**Phase 1 (Setup)**: Added env vars to .env, created deduplication registry files, created linkedin_rate_state.json with defaults.

**Phase 2 (Foundation)**: Created `linkedin_rate_limiter.py` with:
- `RateLimitState` dataclass with atomic save via .tmp rename
- `RateLimiter` class: `can_execute()`, `record_action()`, `pause_account()` — daily counters reset at midnight
- `SessionLock` context manager: PID liveness check, 60s timeout, force-acquire on dead process

**Phase 3 (US1 — Reply)**: Full reply-to-comment pipeline:
- LinkedIn watcher polls `/notifications/`, detects "commented on your post", creates `LINKEDIN_REPLY_*.md`
- Cloud handler drafts reply via OpenAI (max_tokens=200), writes `APPROVE_REPLY_LINKEDIN_*.md`
- Local handler acquires SessionLock, navigates to post, finds commenter, types reply with delay=40ms, submits

**Phase 4 (US2 — Comment)**: Full comment-on-feed pipeline:
- Watcher scans `/feed/`, keyword-filters AI posts (max 5), creates `LINKEDIN_COMMENT_*.md`
- Cloud handler drafts insightful comment (banned phrases enforced), max_tokens=150
- Local handler checks daily limit (10/day), claims file, posts comment, increments counter

**Phase 5 (US3 — Connect)**: Full connect pipeline:
- Watcher searches LinkedIn people with 2nd-degree filter, extracts up to 3 profiles
- Cloud handler drafts personalised note (max_tokens=80, ≤300 chars enforced)
- Local handler waits mandatory 30s before clicking Connect, sends with note, records action (5/day limit)

**Route wiring**: All 6 new handlers registered in cloud_agent.py and local_agent.py dispatch blocks.
**PM2**: silver-linkedin-watcher added to ecosystem.config.js, started, pm2 save executed.
**Bug fix during implementation**: `parents[4]` → `parents[3]` in linkedin.py REPO_ROOT detection.

All handlers verified importable: `ALL HANDLERS IMPORTED SUCCESSFULLY`.
Watcher confirmed running: last log line `Polling LinkedIn notifications for new comments...`.

## Outcome

- ✅ Impact: Full LinkedIn engagement automation implemented — 3 new task types (reply/comment/connect), all with HITL approval flow, rate limiting (10 comments/5 connects per day), session locking, security challenge detection, and human-like delays.
- 🧪 Tests: Manual import verification passed. Watcher startup confirmed. End-to-end smoke test pending (T049).
- 📁 Files: 8 new handler files, 1 new rate limiter utility, 1 updated watcher, 2 updated agents, 1 updated PM2 config, 3 dedup registry files, 1 rate state JSON.
- 🔁 Next prompts: T049 end-to-end smoke test (post comment on own LinkedIn → verify reply flow), T045 health dashboard integration, T048 Dashboard.md update.
- 🧠 Reflection: parents[3] vs parents[4] REPO_ROOT bug caught early by import verification step. Claim-before-execute pattern applied consistently across all 3 local handlers. Rate limiter design (leave file in Approved/ on limit hit, auto-executes next day) is elegant for daily caps.

## Evaluation notes (flywheel)

- Implementation followed spec→plan→tasks→implement pipeline cleanly
- All 3 user stories delivered in priority order (reply P1, comment P2, connect P3)
- Session locking prevents concurrent Playwright contexts — critical for LinkedIn anti-bot safety
- PYTHONPATH sys.path.insert(0, ...) pattern works but requires correct parents[N] depth — worth adding a test
