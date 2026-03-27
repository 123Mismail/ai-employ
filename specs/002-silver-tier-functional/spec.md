# Feature Specification: Silver Tier - Functional Assistant

**Feature Branch**: `002-silver-tier-functional`  
**Created**: 2026-03-16  
**Status**: Draft  
**Input**: User description: "Silver Tier: Functional Assistant with Gmail Watcher and MCP Email Action"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Email Senses (Perception) (Priority: P1)
As a user, I want the AI to automatically detect unread "Important" emails from my Gmail and create a task in the vault so I don't miss business opportunities.

**Independent Test**: Send an email to the configured Gmail account with the label "Important" and verify a `EMAIL_...md` file appears in `Needs_Action/`.

**Acceptance Scenarios**:
1. **Given** the Gmail Watcher is running, **When** a new important email is received, **Then** the watcher generates a Markdown file with YAML frontmatter (sender, subject, date).

---

### User Story 2 - The Safety Gate (HITL) (Priority: P1)
As a user, I want the AI to ask for my explicit approval before it sends any emails to clients, so I can review the draft for accuracy and tone.

**Independent Test**: Run the processor on an email task and verify it creates a file in `Pending_Approval/` rather than sending it immediately.

**Acceptance Scenarios**:
1. **Given** a new email task, **When** the AI processes it, **Then** it creates a draft in `/Pending_Approval/` and waits.

---

### User Story 3 - Taking Action (The Hands) (Priority: P2)
As a user, I want the AI to actually send the email once I move the approval file to the `Approved/` folder.

**Independent Test**: Move an email approval file to `Approved/` and verify the email is sent via the Gmail API/MCP.

**Acceptance Scenarios**:
1. **Given** a file in `/Approved/`, **When** the action handler runs, **Then** the email is sent and the task is moved to `Done/`.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Implement a **Gmail Watcher** (`gmail_watcher.py`) using Google OAuth2 and Gmail API.
- **FR-002**: Implement a **Human-in-the-Loop (HITL) Logic** in the `VaultProcessor`.
- **FR-003**: Implement an **Email Action Skill** (MCP or Direct API) to send approved emails.
- **FR-004**: Integrate **LinkedIn Post Skill** (Optional: Basic API-based or placeholder for Silver).
- **FR-005**: All actions MUST be logged in the JSON audit trail.
- **FR-006**: Support **Scheduling** (Task Scheduler on Windows) for the Gmail Watcher.

### Non-Functional Requirements
- **NFR-001**: **Credential Security**: OAuth tokens MUST be stored securely (not in the vault).
- **NFR-002**: **Reliability**: Use PM2 to keep the Gmail Watcher running 24/7.
- **NFR-003**: **Auditability**: Every sent email must be linked back to its approval file.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Gmail detection latency is < 5 minutes.
- **SC-002**: 100% of outgoing emails require manual approval in `Pending_Approval`.
- **SC-003**: AI successfully drafts a professional reply based on the email context.
- **SC-004**: Audit log confirms the "Approved By" status for every external action.
