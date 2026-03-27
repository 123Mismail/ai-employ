Read the plan (plan.md) and specification (spec.md).

# Goal
Break down the implementation plan into actionable, dependency-ordered tasks.

# Task Format
- [ ] [TaskID] [P?] [Story?] Description with file path

# Structure
- Phase 1: Setup (project initialization)
- Phase 2: Foundational (blocking prerequisites)
- Phase 3+: User Stories in priority order (P1, P2, P3...)
- Final Phase: Polish & Cross-Cutting Concerns

# Example
- [ ] T001 [P] Create project structure per implementation plan
- [ ] T012 [P] [US1] Create Gmail Watcher in src/watchers/gmail.py
- [ ] T014 [US1] Implement Email Service in src/services/email_service.py

Each task MUST be specific enough for an LLM to complete without additional context.

Save in ai/specs/tasks.md or the feature-specific specs/ directory.
