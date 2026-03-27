Read the specification (spec.md), technical plan (plan.md), and tasks list (tasks.md).

# Implementation Steps
- Process and execute all tasks defined in tasks.md sequentially.
- Respect dependencies: Complete blocking prerequisites before user stories.
- Mark completed tasks with [X] in tasks.md.
- Ensure all implementation follows the project's Core Principles (Local-First, HITL, Privacy).
- Implement Python watchers, Claude Code logic, and MCP servers as specified.

# Validation
- Verify each phase completion before proceeding.
- Ensure implemented features match the original specification and technical plan.
- Confirm audit logging and transparency in all actions.

Follow the Perception-Reasoning-Action architecture.
- Perception: Watchers (Python/Playwright)
- Reasoning: Claude Code (Rules, Handbook, Dashboard)
- Action: MCP Servers (Email, Browser, Banking)

Maintain the Human-in-the-Loop (HITL) pattern for sensitive operations.
- Create /Pending_Approval/ files for irreversible actions.
- Wait for files to move to /Approved/ before execution.
