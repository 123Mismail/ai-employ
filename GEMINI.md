# Gemini Agent Guide - Personal AI Employee (Digital FTE)

This file instructs Gemini agents on how to execute the SpecKit Plus workflow for this project.

## Core Mandate
Follow the **Perception-Reasoning-Action** architecture. All development must prioritize **Local-First**, **Privacy**, and **Human-in-the-Loop (HITL)** safety.

## Universal Workflow
Use the following commands and prompts to maintain consistency with other agents (Claude, GPT):

1. **Specification Phase**:
   - `npm run spec 'Feature description'` or `task spec -- 'Feature description'`
   - Follow: `ai/prompts/spec.prompt.md`

2. **Planning Phase**:
   - `npm run plan` or `task plan`
   - Follow: `ai/prompts/plan.prompt.md`

3. **Task Breakdown Phase**:
   - Follow: `ai/prompts/tasks.prompt.md`
   - Output: `tasks.md` in the current feature's specs directory.

4. **Implementation Phase**:
   - Follow: `ai/prompts/implement.prompt.md`
   - Execute each task in `tasks.md`.

## Key Directories
- `ai/prompts/`: Agent-agnostic instruction sets.
- `ai/memory/`: Shared project context and state.
- `ai/rules/`: Coding standards for backend, frontend, and security.
- `.specify/`: Underlying SpecKit Plus bash scripts and templates.
- `AI_Employee_Vault/`: Obsidian vault (Graphical Interface & Long-Term Memory).

## Special Instructions
- Always read `ai/memory/context.md` at the start of a session to understand the current state.
- When creating files for sensitive actions (payments, emails), place them in `/Pending_Approval/`.
- Never execute a sensitive action until a corresponding file appears in `/Approved/`.
- Maintain audit logs in `ai/history/` or the vault's `/Logs/` directory.
