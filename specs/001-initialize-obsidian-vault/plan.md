# Implementation Plan: Bronze Tier Foundation (Digital FTE) - Doc-Perfect Version

**Branch**: `001-bronze-tier-foundation` | **Date**: 2026-03-16 | **Spec**: [specs/001-initialize-obsidian-vault/spec.md]

## Summary
Implement the "Foundational Layer" (Bronze Tier) exactly as defined in the Hackathon Blueprint. This includes the Obsidian "Nerve Center," a Python-based File System Watcher, and the "Brain" interface via Claude Agent Skills.

## Technical Context
**Language/Version**: Python 3.13 (Managed via `uv`), Node.js v24 (for MCP/Claude Code)  
**Primary Dependencies**: `watchdog` (Python), `pm2` (Process Management), `python-dotenv`  
**Storage**: Local Markdown (Obsidian Vault)  
**Process Manager**: PM2 (for 24/7 Watcher reliability)  
**Constraints**: 100% Local-First. Secrets stored in `.env` (NEVER in Vault).

## Constitution Check
- **Local-First**: ✅ All vault files are local markdown.
- **HITL Safety**: ✅ Mandatory `/Pending_Approval` gate included.
- **Persistence**: ✅ PM2 used to prevent script fragility.

## Project Structure (Doc-Aligned)

### Vault Structure (`/AI_Employee_Vault/`)
- `Dashboard.md`: Real-time summary (Bank, Messages, Projects).
- `Company_Handbook.md`: Rules of Engagement.
- `Business_Goals.md`: Q1 Targets & Metrics.
- `/Inbox/`: Raw file drops.
- `/Needs_Action/`: Formatted metadata files for Agent processing.
- `/Plans/`: Step-by-step implementation plans.
- `/Pending_Approval/`: HITL safety gate.
- `/Approved/`: Action triggers.
- `/Done/`: Archived completions.
- `/Logs/`: Audit trail (JSON).

### Source Code Structure
```text
scripts/
├── init_vault.py        # Scaffolds vault & templates
├── watchers/
│   └── filesystem.py    # Python Watchdog script
└── skills/
    └── processor.py     # Agent Skill: Process Needs_Action
```

## Phase 0: Setup & Research
- **Task**: Initialize `uv` project and install `watchdog`.
- **Decision**: Use `PM2` for process management as recommended in Doc p. 28.

## Phase 1: The Nerve Center (Vault)
- **Task**: Create `init_vault.py` to generate the folder hierarchy and markdown templates.
- **Requirement**: `Dashboard.md` must contain sections for: `## Executive Summary`, `## Revenue`, `## Recent Activity`.

## Phase 2: The Sense (Watcher)
- **Task**: Implement `watchers/filesystem.py`.
- **Logic**: Monitor `./drop_zone/`. On file creation, generate a `.md` in `/Needs_Action/` with YAML metadata (type, source, timestamp).

## Phase 3: The Brain (Agent Skills)
- **Task**: Implement `skills/processor.py`.
- **Logic**: Logic for the Agent to "claim" a file from `/Needs_Action/`, move it to `/In_Progress/` (or create a Plan), and eventually to `/Done/`.

## Phase 4: Reliability & PM2
- **Task**: Configure `ecosystem.config.js` or PM2 commands to keep the watcher running 24/7.
