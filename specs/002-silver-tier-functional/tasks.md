# Tasks: Silver Tier - Functional Assistant

**Feature Branch**: `002-silver-tier-functional` | **Date**: 2026-03-16 | **Spec**: [spec.md] | **Plan**: [plan.md]

## Phase 1: Setup & Infrastructure
Goal: Configure Google Cloud project and enable the Gmail API.

- [ ] T001 Create Google Cloud project and enable Gmail API
- [ ] T002 Configure OAuth2 consent screen and download `credentials.json`
- [ ] T003 Install Python dependencies: `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`
- [ ] T004 Create `BronzeTier/scripts/utils/google_auth.py` to handle OAuth tokens
- [ ] T005 [P] Add `token.json` and `credentials.json` to `.gitignore`

## Phase 2: The Email Sense (Gmail Watcher)
Goal: Implement a background watcher to detect "Important" unread emails.

- [ ] T006 Create `BronzeTier/scripts/watchers/gmail.py` using Gmail API
- [ ] T007 Implement logic in `gmail.py` to poll for `is:unread is:important`
- [ ] T008 Implement logic to generate `EMAIL_<id>.md` in `AI_Employee_Vault/Needs_Action/`
- [ ] T009 [US1] Verify Gmail Watcher correctly triggers when a new email is received

## Phase 3: The Safety Gate (HITL Strategy)
Goal: Update the reasoning loop to handle email triage and drafting.

- [ ] T010 Update `BronzeTier/scripts/skills/vault_processor.py` to recognize email tasks
- [ ] T011 [US2] Implement logic to create a "Draft Reply" in `AI_Employee_Vault/Pending_Approval/` for email tasks
- [ ] T012 Implement logic to move the original `EMAIL_<id>.md` to `AI_Employee_Vault/Plans/` for tracking

## Phase 4: The Hands (Action Layer - Email Sending)
Goal: Implement the "Action" layer to send approved emails.

- [ ] T013 Create `BronzeTier/scripts/skills/email_action.py` to monitor the `/Approved/` folder
- [ ] T014 Implement logic in `email_action.py` to read an approved draft and send it via Gmail API
- [ ] T015 Implement logic to move approved files to `AI_Employee_Vault/Done/` after successful send
- [ ] T016 [US3] Verify end-to-end email flow: Triage -> Approval -> Send

## Phase 5: Reliability & Persistence
Goal: Ensure the Silver Tier components are "Always-On."

- [ ] T017 Update `BronzeTier/ecosystem.config.js` to include the `gmail-watcher`
- [ ] T018 Add the `email-sender` (orchestrator) to PM2 to monitor the `/Approved/` folder
- [ ] T019 Restart and save PM2: `pm2 restart ecosystem.config.js && pm2 save`

## Final Phase: Polish & Validation
Goal: Final check against Silver Tier requirements.

- [ ] T020 Perform an end-to-end test of the "Functional Assistant" (Email + Filesystem)
- [ ] T021 Verify audit logs for all external email actions
