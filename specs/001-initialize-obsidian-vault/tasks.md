# Tasks: Bronze Tier Foundation (Digital FTE)

**Feature Branch**: `001-bronze-tier-foundation` | **Date**: 2026-03-16 | **Spec**: [spec.md] | **Plan**: [plan.md]

## Phase 1: Setup & Infrastructure
Goal: Initialize the project environment and dependencies for the Bronze Tier.

- [x] T001 Initialize `uv` Python project in the root directory
- [x] T002 Install Python dependencies: `watchdog`, `python-dotenv` via `uv add`
- [x] T003 Install `pm2` globally (if not present) for process management
- [x] T004 [P] Create `.env` file from a template and add to `.gitignore`

## Phase 2: The Nerve Center (Obsidian Vault)
Goal: Scaffold the local-first "Memory & GUI" as defined in the Bronze Tier.

- [x] T005 [P] Create `scripts/init_vault.py` to automate directory creation
- [x] T006 Implement directory structure in `AI_Employee_Vault/`: `/Inbox`, `/Needs_Action`, `/Plans`, `/Pending_Approval`, `/Approved`, `/Done`, `/Logs`
- [x] T007 [P] Create `AI_Employee_Vault/Dashboard.md` with sections: `## Executive Summary`, `## Revenue`, `## Recent Activity`, `## Pending Approvals`
- [x] T008 [P] Create `AI_Employee_Vault/Company_Handbook.md` with "Rules of Engagement" template from constitution
- [x] T009 [P] Create `AI_Employee_Vault/Business_Goals.md` with Q1 Targets schema

## Phase 3: The First Sense (Perception - File Watcher)
Goal: Implement the "Sense" layer that monitors for new tasks via the filesystem.

- [x] T010 [P] Create `./drop_zone/` folder to serve as the external intake point
- [x] T011 Create `scripts/watchers/filesystem.py` using `watchdog` library
- [x] T012 Implement logic in `filesystem.py` to detect new files in `./drop_zone/` and copy them to `AI_Employee_Vault/Inbox/`
- [x] T013 Implement logic to generate a corresponding `.md` file in `AI_Employee_Vault/Needs_Action/` with YAML metadata (source, type, timestamp)
- [x] T014 [US2] Verify File Watcher correctly triggers when a new file is dropped

## Phase 4: The Brain (Reasoning Loop & Agent Skills)
Goal: Enable the AI Agent (Gemini/Claude) to process vault files autonomously.

- [x] T015 Create `scripts/skills/vault_processor.py` for agent-to-vault interaction logic
- [x] T016 [US3] Implement logic for the agent to "claim" a file by moving it from `/Needs_Action/` to `/In_Progress/` (or a subfolder)
- [x] T017 Implement logic to update `Dashboard.md` "Recent Activity" section upon file processing
- [x] T018 Implement a basic JSON audit logger in `AI_Employee_Vault/Logs/` for every agent action

## Phase 5: Persistence & Reliability (PM2)
Goal: Ensure the "Always-On" status of the AI Employee watchers.

- [x] T019 Create `ecosystem.config.js` to manage the `filesystem.py` watcher via PM2
- [x] T020 [P] Start and save the PM2 process: `pm2 start ecosystem.config.js && pm2 save`
- [x] T021 [P] Verify watcher auto-restarts after a manual crash or "blip"

## Final Phase: Polish & Validation
Goal: Final check against Bronze Tier requirements.

- [x] T022 [P] Perform an end-to-end "Bronze Test": Drop file -> Watcher -> Needs_Action -> Agent Process -> Dashboard Update -> Logs
- [x] T023 Verify all filenames and folder structures exactly match the Hackathon doc diagram (p. 27)
