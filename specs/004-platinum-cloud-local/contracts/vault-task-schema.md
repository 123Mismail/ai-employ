# Contract: VaultTask File Schema

**Feature**: `004-platinum-cloud-local`
**Date**: 2026-03-25
**Version**: 1.0.0

---

## Overview

Every unit of work flowing through the Platinum vault is represented as a `.md` file with YAML frontmatter. The file moves through folders as its state changes (claim-by-move pattern). This document defines the canonical schema for all VaultTask files.

---

## YAML Frontmatter Schema

```yaml
---
# REQUIRED FIELDS
type: email | whatsapp | file_drop | proactive_task | odoo_invoice | social_post
source: Gmail | WhatsApp | Filesystem | Proactive
status: pending | in_progress | pending_approval | approved | rejected | done | stale_recovered
claimed_by: cloud | local | ""
claimed_at: ""                        # ISO 8601 — set when moved to In_Progress/
agent_version: "1.0.0"
timestamp: "2026-03-25T10:25:00"      # file creation time, ISO 8601

# STALE RECOVERY
stale_recovery_count: 0               # incremented each time reaper returns to Needs_Action/

# OPTIONAL: Odoo-specific fields (only when type = odoo_invoice)
odoo_invoice_id: ~                    # integer, set after Odoo draft created
odoo_partner_id: ~                    # integer, Odoo partner record ID
odoo_amount: ~                        # float, invoice total
odoo_status: ~                        # draft | posted
---
```

---

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | yes | Category of work item |
| `source` | enum | yes | System that originated this task |
| `status` | enum | yes | Current lifecycle state |
| `claimed_by` | enum | yes | Agent that owns this task; empty string if unclaimed |
| `claimed_at` | ISO 8601 string | yes | Timestamp when agent moved file to In_Progress/; empty string if unclaimed |
| `agent_version` | semver string | yes | Version of the agent that created this file |
| `timestamp` | ISO 8601 string | yes | File creation time |
| `stale_recovery_count` | integer | yes | Number of times this file was returned to Needs_Action/ by the stale reaper |
| `odoo_invoice_id` | integer | no | Odoo invoice record ID (type=odoo_invoice only) |
| `odoo_partner_id` | integer | no | Odoo partner ID (type=odoo_invoice only) |
| `odoo_amount` | float | no | Invoice amount (type=odoo_invoice only) |
| `odoo_status` | enum | no | Odoo record status: draft or posted |

---

## Status Transitions

```
[created]
    |
    v
Needs_Action/        status=pending,      claimed_by="",      claimed_at=""
    |
    | (claim-by-move: atomic rename)
    v
In_Progress/cloud/   status=in_progress,  claimed_by=cloud,   claimed_at=<ISO>
In_Progress/local/   status=in_progress,  claimed_by=local,   claimed_at=<ISO>
    |
    | (AI reasoning complete)
    v
Plans/               status=in_progress,  claimed_by=<agent>  (plan written)
    |
    | (approval file created)
    v
Pending_Approval/    status=pending_approval
    |
    |-- (human drag to Approved/)  -->  Approved/  status=approved
    |-- (human drag to Rejected/)  -->  Rejected/  status=rejected
    |-- (expires: timestamp past)  -->  Rejected/  status=rejected
    |
    v
Done/                status=done          (after Local executes action)

STALE RECOVERY PATH:
In_Progress/* --> (stale timeout 30min) --> Needs_Action/  status=stale_recovered
```

---

## File Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Gmail email | `EMAIL_<msg_id>_<timestamp>.md` | `EMAIL_19d2404c_20260325130615.md` |
| WhatsApp message | `WHATSAPP_OWNER_<timestamp>.md` | `WHATSAPP_OWNER_20260325131000.md` |
| File drop | `FILE_<filename>_<timestamp>.md` | `FILE_invoice.pdf_20260325131200.md` |
| Proactive task | `TASK_<type>_<date>.md` | `TASK_AUTO_POST_LINKEDIN_20260325.md` |
| Odoo invoice | `ODOO_INVOICE_<ref>_<timestamp>.md` | `ODOO_INVOICE_INV001_20260325.md` |

Timestamp format: `YYYYMMDDHHmmss` (compact, no separators, UTC)

---

## Validation Rules

1. `claimed_at` MUST be non-empty when `claimed_by` is non-empty, and vice versa.
2. `stale_recovery_count` MUST be a non-negative integer; never decremented.
3. `timestamp` MUST be set at file creation and never changed.
4. `type` and `source` MUST be set at file creation and never changed.
5. `odoo_*` fields are only valid when `type = odoo_invoice`; MUST be omitted otherwise.
6. Files in `Done/` MUST have `status = done`.
7. Files in `Rejected/` MUST have `status = rejected`.

---

## Body (below frontmatter)

The Markdown body contains the human-readable summary of the task, written by the Cloud Agent or Watcher that created the file. Format:

```markdown
## Summary

[One-paragraph description of what this task is about]

## Details

[Structured details relevant to the task type, e.g. email subject/body, WhatsApp message text, invoice line items]

## Plan

[Written by the Cloud Agent when moved to Plans/ — action steps]
```
