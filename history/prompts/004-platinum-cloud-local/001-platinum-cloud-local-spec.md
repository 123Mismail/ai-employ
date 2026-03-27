---
id: 004-001
title: platinum-cloud-local-spec
stage: spec
date: 2026-03-25
surface: claude-code
model: claude-sonnet-4-6
feature: 004-platinum-cloud-local
branch: 004-platinum-cloud-local
user: owner
command: /sp.specify
labels: [platinum, cloud, local, dual-agent, vault-sync, odoo]
links:
  spec: specs/004-platinum-cloud-local/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-platinum-cloud-local/spec.md
  - specs/004-platinum-cloud-local/checklists/requirements.md
  - history/prompts/004-platinum-cloud-local/001-platinum-cloud-local-spec.md
tests:
  - ""
---

## Prompt

Create a spec for the Platinum tier: Always-On Cloud + Local AI Employee — dual-agent Cloud+Local architecture running 24/7. Cloud VM hosts the always-on watchers and orchestrator for email triage, draft replies, and social post scheduling (draft-only, requires Local approval before send/post). Local machine owns approvals, WhatsApp session, payments/banking, and final send/post actions. Agents communicate via a Git-synced Obsidian vault using file-based handoff with claim-by-move rule. Vault sync includes only markdown/state — secrets never sync. Deploy Odoo Community on Cloud VM with HTTPS, backups, and health monitoring.

## Response snapshot

Created `specs/004-platinum-cloud-local/spec.md` on branch `004-platinum-cloud-local` with:
- 5 prioritised user stories covering: offline email draft/approval (P1), social post draft/approval (P2), claim-by-move concurrency safety (P3), Odoo draft-only accounting with local approval (P4), vault sync security (P5)
- 17 functional requirements split across CloudAgent, LocalAgent, VaultSync, and Safety domains
- 6 key entities: CloudAgent, LocalAgent, VaultTask, ApprovalFile, VaultSync, OdooInstance
- 8 measurable success criteria (timing, zero-duplicate, security, uptime)
- Full edge cases: vault sync failure, concurrent move conflict, disk full, expired approvals offline, WhatsApp session expiry
- Assumptions and Out-of-Scope sections documented
- Quality checklist: all items pass — ready for `/sp.plan`

## Outcome

- ✅ Impact: Full Platinum tier spec documented; unblocks planning and implementation phases
- 🧪 Tests: Acceptance scenarios defined for all 5 user stories; minimum demo gate (SC-007) specified as < 10 min end-to-end
- 📁 Files: specs/004-platinum-cloud-local/spec.md, checklists/requirements.md
- 🔁 Next prompts: /sp.plan, /sp.clarify (optional), /sp.tasks
- 🧠 Reflection: Claim-by-move rule and stale-file recovery are the most nuanced concurrency concerns; worth an ADR before implementation

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist all PASS
- Prompt variant (if applicable): ""
- Next experiment: run /sp.clarify to stress-test vault sync conflict resolution assumptions
