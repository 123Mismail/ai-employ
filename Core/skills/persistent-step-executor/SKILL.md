---
name: persistent-step-executor
description: Autonomously executes multi-step plans by monitoring file state transitions in the Obsidian Vault. Use when a task requires sequential processing (e.g., Triage -> Draft -> Approve -> Send) to ensure the agent continues working until the task moves to /Done.
---

# Persistent Step Executor (Ralph Wiggum Loop)

## Overview
This skill implements the "Ralph Wiggum" persistence pattern. It ensures the AI Employee doesn't stop after a single action but instead iterates through a multi-step plan until the final objective is reached.

## Workflow
1. **Monitor**: Watch for files in `Needs_Action/`, `To_Draft/`, and `Approved/`.
2. **Execute**: 
   - If in `Needs_Action`, move to `To_Draft` (based on filters).
   - If in `To_Draft`, generate a Smart Draft and move to `Pending_Approval`.
   - If in `Approved`, execute the final action (Email/Post) and move to `Done`.
3. **Loop**: Re-scan the vault immediately after completing any step to see if the next step is ready.

## Rules
- Never move a file to `Approved` autonomously; this requires a human.
- Always log every transition in the `/Logs/` directory.
- If a task is "stuck" for more than 3 loops, flag it in `Dashboard.md`.
