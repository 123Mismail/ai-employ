# Feature Specification: Platinum Tier — Always-On Cloud + Local AI Employee

**Feature Branch**: `004-platinum-cloud-local`
**Created**: 2026-03-25
**Status**: Draft
**Input**: Dual-agent Cloud+Local architecture running 24/7 with Git-synced vault, claim-by-move handoff, Odoo on Cloud VM, and offline-resilient email draft/approval workflow.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Offline-Resilient Email Draft & Approval (Priority: P1)

The owner's laptop is offline or closed. An important email arrives. The Cloud Agent detects it, drafts a reply, and writes an approval file into the shared vault. When the owner's machine comes back online, the vault syncs, the Local Agent detects the pending approval in Obsidian, and the owner drags it to `Approved/`. The Local Agent then sends the email and moves the task to `Done/`.

**Why this priority**: This is the minimum passing demo gate defined by the hackathon spec. It proves the dual-agent handoff and offline-resilience — the core value proposition of the Platinum tier.

**Independent Test**: Drop a test email into Gmail while Local is offline (Wi-Fi disabled). Re-enable Wi-Fi, sync vault, approve in Obsidian. Verify email is sent and task appears in `Done/`.

**Acceptance Scenarios**:

1. **Given** Local machine is offline, **When** an unread important email arrives in Gmail, **Then** Cloud Agent creates `EMAIL_<id>.md` in `Needs_Action/`, drafts a reply, and writes `APPROVE_REPLY_<id>.md` in `Pending_Approval/` — all within 5 minutes of email arrival.
2. **Given** a pending approval file exists in `Pending_Approval/`, **When** the owner moves it to `Approved/` in Obsidian, **Then** Local Agent sends the email via Gmail API, logs the action to `Logs/YYYY-MM-DD.json`, and moves both task and approval files to `Done/`.
3. **Given** the approval file contains an `expires:` timestamp that has passed, **When** Local Agent processes it, **Then** the file is moved to `Rejected/` and no email is sent.

---

### User Story 2 — Cloud-Side Social Post Drafting with Local Approval (Priority: P2)

The Cloud Agent proactively drafts a LinkedIn/X/Facebook post based on the daily business goal (one post per day). It writes the draft to `Pending_Approval/`. The owner reviews and approves or rejects via Obsidian. Only after approval does the Local Agent publish the post.

**Why this priority**: Proves Cloud-draft / Local-publish split for sensitive public-facing actions. Demonstrates proactive behavior without autonomous posting.

**Independent Test**: Manually trigger the Business Auditor on the Cloud VM. Verify a draft appears in `Pending_Approval/`. Approve it and verify the post is published from the Local machine.

**Acceptance Scenarios**:

1. **Given** no LinkedIn post was published today, **When** the Cloud Business Auditor runs, **Then** it creates `TASK_AUTO_POST_LINKEDIN_<date>.md` in `Needs_Action/`, and Cloud Agent drafts a post into `Pending_Approval/`.
2. **Given** a draft post is in `Pending_Approval/`, **When** owner approves it on Local machine, **Then** Local Agent publishes to LinkedIn/X/Facebook and moves files to `Done/`.
3. **Given** owner moves the draft to `Rejected/`, **Then** no post is published and the task is closed with status `rejected`.

---

### User Story 3 — Claim-by-Move Concurrency Safety (Priority: P3)

When both Cloud and Local agents are online simultaneously, only one agent should process any given task. The first agent to move an item from `Needs_Action/` to `In_Progress/<agent>/` claims it; the other agent ignores it.

**Why this priority**: Prevents double-processing which could cause duplicate emails, duplicate posts, or conflicting vault state.

**Independent Test**: Start both Cloud and Local agents simultaneously, drop a test task into `Needs_Action/`, and verify exactly one `PLAN_*.md` is created and no duplicate actions occur.

**Acceptance Scenarios**:

1. **Given** both agents are running, **When** a new `.md` file appears in `Needs_Action/`, **Then** exactly one agent moves it to `In_Progress/<agent>/` and the other leaves it alone.
2. **Given** one agent crashes mid-task with the file in `In_Progress/cloud/`, **When** Local agent restarts, **Then** it does not re-process the in-progress file unless a configurable stale timeout (default: 30 minutes) has elapsed.
3. **Given** a file is in `In_Progress/cloud/`, **When** Local agent scans `Needs_Action/`, **Then** the in-progress file is not present and Local agent takes no action on it.

---

### User Story 4 — Odoo Cloud Deployment: Draft-Only Accounting with Local Approval (Priority: P4)

Odoo Community runs on the Cloud VM with HTTPS and daily backups. The Cloud Agent can create draft invoices and calendar events but cannot post or confirm them. Posting requires Local approval.

**Why this priority**: Adds financial safety — no money movement or confirmed invoices without human sign-off on the Local machine.

**Independent Test**: Trigger an invoice creation task via a test file drop. Verify a draft invoice appears in Odoo (status: draft). Approve the posting task on Local. Verify invoice is confirmed in Odoo.

**Acceptance Scenarios**:

1. **Given** an invoice task arrives in `Needs_Action/`, **When** Cloud Agent processes it, **Then** a draft invoice is created in Odoo (status = `draft`) and a `APPROVE_POST_INVOICE_<id>.md` is written to `Pending_Approval/`.
2. **Given** the invoice approval is moved to `Approved/` on Local, **When** Local Agent processes it, **Then** the Odoo invoice status changes to `posted` and the approval file moves to `Done/`.
3. **Given** Odoo is unreachable, **When** Cloud Agent tries to create a draft invoice, **Then** the error is logged, the task remains in `Needs_Action/`, and no approval file is created.

---

### User Story 5 — Vault Sync Security: Secrets Never Sync (Priority: P5)

The Git-synced vault repository contains only Markdown state files. Credential files (`.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`) are excluded from sync via `.gitignore` and never appear in the remote repository.

**Why this priority**: Fundamental security boundary — a compromised cloud repo must never expose local credentials or session tokens.

**Independent Test**: After a vault sync push from Cloud VM, inspect the remote repo via `git ls-tree -r HEAD` and confirm no secret files are present.

**Acceptance Scenarios**:

1. **Given** the vault is synced via Git, **When** `git ls-tree -r HEAD` is run on the remote, **Then** no `.env`, `token.json`, `credentials.json`, `whatsapp_session/`, or `linkedin_session/` files are present.
2. **Given** a developer accidentally adds a secret file to the vault, **When** they attempt `git push`, **Then** the push is blocked by a pre-push hook and the file is not uploaded.
3. **Given** Cloud and Local are running simultaneously, **When** Cloud writes a draft to `Pending_Approval/` and pushes, **Then** Local pulls and the approval file is visible in Obsidian within 60 seconds.

---

### Edge Cases

- What happens when the vault Git sync fails (network down, merge conflict)? Local and Cloud must continue operating independently on their local vault copies and retry sync.
- What happens when both agents simultaneously move the same file from `Needs_Action/`? Git conflict on the move — the later push gets a merge conflict; the losing agent must detect the conflict, abort, and leave the file to the winner.
- What happens when the Cloud VM runs out of disk space? The orchestrator must stop creating new task files and send an alert to `Logs/` without crashing.
- What happens when the approval file's `expires:` field passes while Local is still offline? When Local comes back online and syncs, it must immediately move the expired approval to `Rejected/` without executing the action.
- What happens when WhatsApp session token expires on Local? Cloud continues to draft WhatsApp replies, but Local flags the session as invalid and prompts the owner to re-run the handshake tool rather than silently failing.

---

## Requirements *(mandatory)*

### Functional Requirements

**Cloud Agent (always-on VM):**
- **FR-001**: Cloud Agent MUST monitor Gmail continuously and create task files in `Needs_Action/` for unread important emails within 5 minutes of arrival.
- **FR-002**: Cloud Agent MUST draft replies and social posts using the AI reasoning layer and write approval files to `Pending_Approval/` — never send or publish directly.
- **FR-003**: Cloud Agent MUST implement the claim-by-move rule: move task from `Needs_Action/` to `In_Progress/cloud/` before processing; skip any file already in `In_Progress/`.
- **FR-004**: Cloud Agent MUST create draft-only Odoo invoices and calendar events; posting/confirmation is forbidden without Local approval.
- **FR-005**: Cloud Agent MUST push vault changes to the remote Git repository after every write operation.
- **FR-006**: Cloud Agent MUST run a health check endpoint that reports process status, last sync time, and last task processed.
- **FR-007**: Cloud VM MUST run Odoo Community with a valid HTTPS certificate, automated daily backups, and auto-restart on crash.

**Local Agent (owner's machine):**
- **FR-008**: Local Agent MUST pull vault changes from Git on startup and on a configurable interval (default: 60 seconds).
- **FR-009**: Local Agent MUST be the sole executor of: sending emails, sending WhatsApp messages, publishing social posts, and posting/confirming Odoo invoices.
- **FR-010**: Local Agent MUST implement the same claim-by-move rule using `In_Progress/local/` to prevent double-processing when both agents are online.
- **FR-011**: Local Agent MUST check the `expires:` field of every approval file before executing; expired approvals MUST be moved to `Rejected/` without action.

**Vault Sync:**
- **FR-012**: The Git repository MUST exclude all secret files via `.gitignore`: `.env`, `token.json`, `credentials.json`, `whatsapp_session/`, `linkedin_session/`, `processed_emails.txt`, `processed_chats.txt`.
- **FR-013**: A pre-push Git hook MUST block any commit containing secret files from being pushed to the remote.
- **FR-014**: Vault folder structure MUST include: `Needs_Action/`, `In_Progress/cloud/`, `In_Progress/local/`, `Plans/`, `Pending_Approval/`, `Approved/`, `Rejected/`, `Done/`, `Logs/`, `Briefings/`.

**Safety & Recovery:**
- **FR-015**: Stale `In_Progress/` files older than 30 minutes MUST be returned to `Needs_Action/` by whichever agent detects them first.
- **FR-016**: All actions taken by either agent MUST be logged to `Logs/YYYY-MM-DD.json` with the full schema: `timestamp`, `action_type`, `actor`, `target`, `parameters`, `approval_status`, `approved_by`, `result`.
- **FR-017**: Both agents MUST implement exponential-backoff retry (max 3 attempts) for all network operations before marking a task as failed.

### Key Entities

- **CloudAgent**: The always-on process on the VM. Responsible for perception (Gmail, filesystem) and reasoning (drafting). Never executes send/publish/post/pay actions.
- **LocalAgent**: The owner's machine process. Responsible for approval processing, all external send actions, WhatsApp, and Odoo posting.
- **VaultTask**: A `.md` file representing a unit of work. Moves through: `Needs_Action/` → `In_Progress/<agent>/` → `Plans/` → `Pending_Approval/` → `Approved/` or `Rejected/` → `Done/`.
- **ApprovalFile**: A `APPROVE_*.md` file in `Pending_Approval/` with YAML frontmatter containing `type`, `expires`, `status`, and a human-readable draft. The owner approves by drag-drop to `Approved/`.
- **VaultSync**: The Git remote repository containing only Markdown state. No secrets. Synced by both agents; merge conflicts are resolved by retry-pull-push.
- **OdooInstance**: The Cloud VM-hosted Odoo Community ERP. CloudAgent creates draft records; LocalAgent posts/confirms them after approval.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An email arriving while Local is offline produces a complete approval draft in `Pending_Approval/` within 5 minutes on the Cloud side.
- **SC-002**: After the owner approves, the email is sent and the task reaches `Done/` within 60 seconds on the Local side.
- **SC-003**: When both agents are online, zero duplicate task executions occur across 20 consecutive test task drops.
- **SC-004**: Vault sync (push + pull) completes within 60 seconds under normal network conditions.
- **SC-005**: No secret file (`.env`, tokens, sessions) appears in the remote Git repository under any tested scenario.
- **SC-006**: Odoo remains reachable via HTTPS with valid certificate; uptime target is 99% over any 7-day window.
- **SC-007**: The full minimum demo flow (email arrives offline → draft → approve → send → Done) completes end-to-end in under 10 minutes.
- **SC-008**: Stale `In_Progress/` files are detected and returned to `Needs_Action/` within 35 minutes of the owning agent going silent.

---

## Assumptions

- The Cloud VM has a static IP or DNS hostname accessible from the Local machine for vault sync; Git remote is hosted on GitHub or a self-hosted Git server.
- Git is the chosen vault sync mechanism (Phase 1); A2A messaging is out of scope for this spec.
- WhatsApp Web sessions remain on Local only; Cloud Agent drafts WhatsApp replies but cannot send them without a Local WhatsApp session.
- Odoo Community 17+ is used (XML-RPC API compatible); self-hosted on the same Cloud VM as the orchestrator.
- The pre-push hook blocks secret files but does not prevent accidental commits locally — developers must still use `git status` discipline.
- The stale timeout of 30 minutes is configurable via `.env` (`STALE_TASK_TIMEOUT_MINUTES`).
- Dashboard.md is written exclusively by the Local Agent (single-writer rule) to avoid merge conflicts on the most-frequently-updated file.

---

## Out of Scope

- A2A (Agent-to-Agent) direct messaging between Cloud and Local (Phase 2 upgrade path only).
- Banking API integration (no direct payment execution — Odoo invoice posting is the payment proxy).
- Instagram posting from Cloud side (Cloud drafts only; Instagram publish requires Local browser session).
- Multi-user or multi-owner vault access.
- Mobile app or web dashboard beyond Obsidian.
