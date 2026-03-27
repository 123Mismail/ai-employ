# Project Context: Personal AI Employee (Digital FTE)

## Core Stack
- **Knowledge Base**: Obsidian (Local Markdown)
- **Reasoning Engine**: Claude Code / Gemini CLI (local CLI)
- **Sensors (Watchers)**: Python scripts (Gmail, WhatsApp, Filesystem)
- **Hands (MCP)**: Model Context Protocol (MCP) servers (Email, Browser, Banking)
- **Workflow**: Perception-Reasoning-Action (SpecKit Plus)
- **OS**: Windows 32 (PowerShell)

## Architecture
- **Perception Layer**: Lightweight Python watchers that monitor external inputs and drop files into Obsidian `/Needs_Action/`.
- **Reasoning Layer**: `MasterOrchestrator` (Core) automatically claims tasks from `Needs_Action`, creates plans, and follows `Company_Handbook.md`.
- **Action Layer**: MCP servers executing tasks with **Human-in-the-Loop (HITL)** safety.
- **Persistence**: Ralph Wiggum loop for autonomous multi-step tasks.

## Principles
- **Local-First & Privacy**: Sensitive data remains local.
- **HITL Safety**: Mandatory human approval for irreversible actions.
- **Auditability**: Comprehensive logging of all AI actions (JSON audit trail).

## Workflow Progress
- [X] Project Initialized
- [X] Universal AI OS Structure Implemented (ai/ directory)
- [X] npm scripts configured for agent-agnostic development
- [X] **BRONZE TIER (Foundation)**
  - [X] Implement Obsidian Vault (AI_Employee_Vault)
  - [X] Create Dashboard.md & Company_Handbook.md
  - [X] Build First Watcher (Filesystem/Local Drop)
  - [X] Connect Claude/Gemini to Vault
- [X] **SILVER TIER (Functional Assistant)**
  - [X] Gmail Watcher (Perception)
  - [X] WhatsApp Watcher (Perception - De-noised)
  - [X] Email Skill (Action)
  - [X] HITL Approval Workflow
- [>] **GOLD TIER (Autonomous Employee)**
  - [X] Automated Reasoning Layer (Master Orchestrator monitoring Needs_Action)
  - [X] Ralph Wiggum Persistence Loop
  - [ ] Weekly Business Audit (Logic implemented, needs scheduling)
  - [ ] Odoo JSON-RPC Skill (Implemented, needs testing)
  - [ ] Social Media Posting (X/FB/LinkedIn Skills implemented)
