# Tasks: Gold Tier - Autonomous Employee

**Feature Branch**: `003-gold-tier-autonomous` | **Date**: 2026-03-19 | **Spec**: [spec.md] | **Plan**: [plan.md]

## Phase 1: Persistence (The Ralph Wiggum Loop)
Goal: Ensure the AI continues working until a task reaches the /Done folder.

- [ ] T001 Update `Core/scripts/orchestrator.py` to add recursive monitoring
- [ ] T002 Implement logic to detect when a Plan file has unprocessed "Steps" and re-trigger the Brain
- [ ] T003 Verify the loop: Drop file in `To_Draft` -> AI drafts -> AI waits for approval -> User moves to `Approved` -> AI sends -> AI moves everything to `Done`.

## Phase 2: Proactive Partner (The Business Auditor)
Goal: Generate autonomous weekly briefings from business data.

- [ ] T004 Create `Core/scripts/skills/business_auditor.py`
- [ ] T005 Implement logic to parse `Business_Goals.md` and current week's `/Done/` folder
- [ ] T006 Implement "Monday Morning CEO Briefing" template generation in `/Briefings/`
- [ ] T007 [P] Schedule the auditor to run every Sunday night via `ecosystem.config.js`

## Phase 3: The Accountant (Odoo ERP)
Goal: Connect the AI Employee to Odoo Community for financial management.

- [ ] T008 Install `odoo-rpc` or use standard `xmlrpc.client`
- [ ] T009 Create `Core/scripts/skills/odoo_skill.py` for ERP interaction
- [ ] T010 Implement `get_balance` and `create_draft_invoice` functions
- [ ] T011 [US2] Verify end-to-end flow: Email "Send invoice" -> AI creates draft in Odoo -> AI reports success in Obsidian.

## Phase 4: The Influencer (Social Media Integration)
Goal: Enable cross-platform posting to X and Facebook.

- [ ] T012 Install `tweepy` and `facebook-sdk`
- [ ] T013 Create `SilverTier/scripts/skills/social_post.py`
- [ ] T014 Implement posting logic for X (Twitter) and Facebook Graph API
- [ ] T015 [US3] Verify social workflow: Move post draft to `Approved` -> AI publishes to live feed.

## Final Phase: Polish & Production
Goal: Final validation of the Gold Tier production system.

- [ ] T016 Perform a "Business Handover" test (Full Audit + Revenue Check)
- [ ] T017 Update `Dashboard.md` with Gold Tier metrics (MTD Revenue vs Goal)
- [ ] T018 Verify comprehensive audit logging for all Gold actions
