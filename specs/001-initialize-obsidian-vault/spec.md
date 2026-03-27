# Feature Specification: Bronze Tier - Foundation (Digital FTE)

**Feature Branch**: `001-bronze-tier-foundation`  
**Created**: 2026-03-16  
**Status**: Draft  
**Input**: User description: "Initialize the complete Bronze Tier as defined in the Hackathon document"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Nerve Center (Priority: P1)
As a user, I want a local Obsidian vault with a dashboard so I can manage my AI Employee's activities and rules of engagement locally and privately.

**Independent Test**: Can be tested by opening the `AI_Employee_Vault` in Obsidian and verifying the presence of `Dashboard.md` and `Company_Handbook.md`.

**Acceptance Scenarios**:
1. **Given** no vault exists, **When** I run the init script, **Then** `AI_Employee_Vault/` is created with folders: `/Inbox`, `/Needs_Action`, `/Plans`, `/Pending_Approval`, `/Approved`, `/Done`, and `/Logs`.
2. **Given** the vault is created, **When** I open `Company_Handbook.md`, **Then** I see the "Rules of Engagement" based on the project constitution.

---

### User Story 2 - The First Sense (Perception) (Priority: P2)
As a user, I want a File System Watcher that automatically detects new files I drop into a folder and notifies the AI Employee.

**Independent Test**: Drop a text file into a "Drop" folder and verify a corresponding `.md` file appears in `AI_Employee_Vault/Needs_Action/`.

**Acceptance Scenarios**:
1. **Given** the File System Watcher is running, **When** I add a file to the designated drop zone, **Then** the watcher creates a metadata-rich Markdown file in `/Needs_Action/`.

---

### User Story 3 - Agentic Skill Execution (Priority: P3)
As an AI Agent (Gemini/Claude), I need to be able to read tasks from the vault and write reports back to it using a standardized "Skill" format.

**Independent Test**: Prompt the AI to "Read the latest item in Needs_Action and write a summary to Dashboard.md" and verify the file content changes.

**Acceptance Scenarios**:
1. **Given** an item in `/Needs_Action/`, **When** I prompt the agent, **Then** it uses its filesystem tools to process the file and update the `Dashboard.md` "Recent Activity" section.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Create `AI_Employee_Vault` with the hierarchy: `/Inbox`, `/Needs_Action`, `/Plans`, `/Pending_Approval`, `/Approved`, `/Done`, `/Logs`.
- **FR-002**: Initialize `Dashboard.md` and `Company_Handbook.md` with templates from the hackathon document.
- **FR-003**: Implement a **Python File System Watcher** (`filesystem_watcher.py`) using the `watchdog` library.
- **FR-004**: The Watcher MUST create YAML-frontmatter-enabled Markdown files for every detected file.
- **FR-005**: All AI actions (reading/writing) MUST be implemented as **Agent Skills** to ensure modularity.
- **FR-006**: Implement a basic **Audit Log** system that writes every action to `Logs/YYYY-MM-DD.json`.

### Non-Functional Requirements
- **NFR-001**: **Local-First**: No data should leave the local machine during the Bronze phase.
- **NFR-002**: **Reliability**: The Watcher script must be robust against transient filesystem errors.
- **NFR-003**: **Security**: No credentials should be stored in the vault; use `.env` files.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: 100% of Bronze Tier folder requirements are met.
- **SC-002**: File System Watcher latency is < 2 seconds for detection.
- **SC-003**: AI Agent successfully reads from `/Needs_Action` and writes to `/Done` without human intervention (Reasoning loop).
- **SC-004**: Dashboard updates correctly reflected in Obsidian within 1 second of file write.
