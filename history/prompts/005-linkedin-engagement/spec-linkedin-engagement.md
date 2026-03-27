---
id: PHR-005-001
title: linkedin-engagement-spec
stage: spec
date: 2026-03-26
surface: project
model: claude-sonnet-4-6
feature: 005-linkedin-engagement
branch: 005-linkedin-engagement
user: human
command: /sp.specify
labels: [linkedin, engagement, social, hitl, rate-limiting, safety]
links:
  spec: specs/005-linkedin-engagement/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/005-linkedin-engagement/spec.md
  - specs/005-linkedin-engagement/checklists/requirements.md
tests: []
---

## Prompt

LinkedIn Advanced Engagement Features — Auto-comment on AI posts, reply to comments on own posts, auto-connect with AI startup and tech people. All features must be safe, rate-limited, and go through the existing HITL approval flow (Pending_Approval → Approved → local agent executes). Built on top of existing Platinum Tier architecture: same Playwright LinkedIn session, same cloud/local agent pattern, same Obsidian vault task files. Key risks to address: LinkedIn anti-bot detection, account ban from aggressive automation, DOM instability, session conflicts with existing LinkedIn poster. Build order priority: 1) Reply to comments on own posts, 2) Comment on others posts, 3) Auto-connect with AI people.

## Response snapshot

Created `specs/005-linkedin-engagement/spec.md` on branch `005-linkedin-engagement` with:
- 3 prioritised user stories (P1 reply, P2 comment, P3 connect)
- 18 functional requirements covering watcher, rate limiting, HITL, content quality, audit
- 5 key entities: LinkedInEngagementTask, EngagementApproval, RateLimitState, DeduplicationRegistry, SessionLock
- 8 measurable success criteria
- Full edge cases covering DOM instability, session expiry, concurrent access, account flagging
- All checklist items passing — ready for /sp.plan

## Outcome

- Impact: Spec defines safe, HITL-gated LinkedIn engagement automation with conservative rate limits (10 comments/day, 5 connections/day) to protect the account
- Tests: Acceptance scenarios defined for all 3 features, independently testable
- Files: specs/005-linkedin-engagement/spec.md, checklists/requirements.md
- Next prompts: /sp.plan, /sp.tasks
- Reflection: Rate limits and session locking are the critical safety mechanisms — build order (P1→P2→P3) ensures the safest features are proven before the highest-risk connect feature is implemented

## Evaluation notes (flywheel)

Key decisions made without clarification:
- 10 comments/day and 5 connections/day as conservative safe thresholds (adjustable via .env)
- Session lock file pattern chosen over process serialisation for simplicity
- Claim-before-execute mandated (FR-013) based on lessons from LinkedIn retry storm bug
- CRITICAL pause on security challenge (FR-010) is a hard safety requirement
