# Implementation Plan: Gold Tier - Autonomous Employee (Digital FTE)

**Branch**: `003-gold-tier-autonomous` | **Date**: 2026-03-19 | **Spec**: [specs/003-gold-tier-autonomous/spec.md]

## Summary
Implement the "Autonomous Employee" (Gold Tier) by enabling proactive business auditing, financial ERP integration (Odoo), and multi-platform social media management. This tier also introduces the "Ralph Wiggum" persistence loop for multi-step autonomy.

## Technical Context
**Language/Version**: Python 3.13 (Managed via `uv`)  
**Primary Dependencies**: `xmlrpc.client` (Odoo), `tweepy` (X/Twitter), `facebook-sdk`, `pm2`  
**Storage**: Obsidian Vault (Markdown) + Odoo Community (ERP)  
**Security**: All API Keys (Odoo, Social Media) stored in `.env`. Strict HITL for all external actions.

## Constitution Check
- **Proactivity**: ✅ MANDATORY - Weekly Auditor must generate briefings without user prompts.
- **Persistence**: ✅ Ralph Wiggum loop ensures tasks move through the vault phases autonomously.
- **HITL Safety**: ✅ MANDATORY - No public posts or invoices without `/Approved/` folder presence.

## Project Structure (Gold Modules)

```text
Core/
├── scripts/
│   ├── orchestrator.py        # UPDATED: Ralph Wiggum Persistence logic
│   └── skills/
│       ├── smart_agent.py
│       ├── business_auditor.py # NEW: Weekly audit logic
│       └── odoo_skill.py       # NEW: Odoo JSON-RPC integration
SilverTier/
└── scripts/
    ├── watchers/
    │   ├── gmail.py
    │   └── social_watcher.py   # NEW: Social engagement monitor
    └── skills/
        └── social_post.py      # NEW: X/FB API posting logic
```

## Phase 1: Persistence (The Ralph Wiggum Loop)
- **Goal**: Make the AI "work until done."
- **Logic**: Update `orchestrator.py` to recursively check if a task in `Plans/` has a "Next Step" and trigger it automatically until the file reaches `Done/`.

## Phase 2: Proactive Partner (The Auditor)
- **Goal**: Generate the "Monday Morning CEO Briefing."
- **Logic**: A new script `business_auditor.py` that aggregates data from `Business_Goals.md` and `/Done/*.md`. It calculates revenue from completed invoice tasks.

## Phase 3: The Accountant (Odoo)
- **Goal**: Connect to Odoo Community.
- **Logic**: Use `xmlrpc.client` to authenticate with Odoo. Focus on `account.move` (Invoices) and `res.partner` (Customers).

## Phase 4: The Influencer (Social Media)
- **Goal**: Multi-platform posting.
- **Logic**: Use `tweepy` for X and `facebook-sdk` for FB. All posts start as drafts in `Pending_Approval`.

## Phase 5: Reliability
- **Task**: Update `ecosystem.config.js` to include the auditor as a "Scheduled Task" (or run it via the Orchestrator's internal clock).
