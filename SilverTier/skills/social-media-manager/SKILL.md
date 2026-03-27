---
name: social-media-manager
description: Manages cross-platform social media presence (X, Facebook, Instagram). Use to draft engagement-focused posts, handle scheduling via the vault, and execute posts after human approval.
---

# Social Media Manager

## Overview
Automates the lifecycle of social media content while maintaining human oversight for brand safety.

## Workflow
1. **Drafting**: Brain generates post ideas in `Plans/` based on current trends or business goals.
2. **Review**: Drafts are moved to `Pending_Approval/SOCIAL_POST_...md`.
3. **Execution**: Once approved, the orchestrator triggers the posting skill to hit the respective APIs/MCP servers.
4. **Archiving**: Moves post record to `Done/`.

## Constraints
- 100% HITL: No post can be published without being in the `Approved/` folder.
- Maintain a log of engagement summaries if possible.
