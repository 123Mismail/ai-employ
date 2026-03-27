# Implementation Plan: Silver Tier - Functional Assistant (Digital FTE)

**Branch**: `002-silver-tier-functional` | **Date**: 2026-03-16 | **Spec**: [specs/002-silver-tier-functional/spec.md]

## Summary
Implement the "Functional Assistant" (Silver Tier) by adding communication senses (Gmail) and action capabilities (Email Send via MCP), while maintaining strict HITL safety gates.

## Technical Context
**Language/Version**: Python 3.13 (Managed via `uv`)  
**Primary Dependencies**: `google-api-python-client`, `google-auth-oauthlib`, `pm2`  
**Storage**: Local Markdown (Obsidian Vault) + SQLite (optional for processed IDs)  
**Security**: Google OAuth2 (Credentials stored in `credentials.json` and `token.json` - IGNORED by Git)  
**Process Manager**: PM2 (for 24/7 Gmail Watcher)

## Constitution Check
- **HITL Safety**: ✅ MANDATORY - All outgoing emails MUST go through `/Pending_Approval`.
- **Privacy**: ✅ Local triage and drafting; only approved content leaves the system.
- **Auditability**: ✅ All send actions linked to approval files and logged in JSON.

## Project Structure (Silver Extension)

```text
BronzeTier/
├── scripts/
│   ├── watchers/
│   │   ├── filesystem.py
│   │   └── gmail.py           # NEW: Gmail Watcher
│   ├── skills/
│   │   ├── processor.py       # UPDATED: HITL for Email
│   │   └── email_action.py     # NEW: Sending logic (MCP-like)
│   └── utils/
│       └── google_auth.py     # NEW: Shared OAuth logic
└── ecosystem.config.js        # UPDATED: Add Gmail watcher
```

## Phase 0: Research & Google API Setup
- **Task**: Configure Google Cloud project, enable Gmail API, and download `credentials.json`.
- **Decision**: Use `token.json` for persistent OAuth session to allow 24/7 operation.

## Phase 1: The Email Sense (Gmail Watcher)
- **Task**: Implement `scripts/watchers/gmail.py`.
- **Logic**: Poll for `is:unread is:important` every 5 mins. Create `EMAIL_<id>.md` in `/Needs_Action`.
- **Format**: Include Sender, Subject, Snippet, and a "Suggested Reply" block.

## Phase 2: The Safety Gate (HITL Strategy)
- **Task**: Update `scripts/skills/processor.py`.
- **Logic**: When an Email task is claimed, create a draft in `Pending_Approval/EMAIL_REPLY_<id>.md`.

## Phase 3: The Hands (Action Layer)
- **Task**: Implement `scripts/skills/email_action.py`.
- **Logic**: Monitor the `/Approved/` folder. When a reply file arrives, send it via Gmail API and move to `Done/`.

## Phase 4: Reliability
- **Task**: Add `gmail-watcher` to `ecosystem.config.js`.
- **Task**: Set up a Windows Task Scheduler job to run the `email_action.py` "Sender" every 10 mins (or keep it as a watcher).
