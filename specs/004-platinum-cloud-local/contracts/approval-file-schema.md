# Contract: ApprovalFile Schema

**Feature**: `004-platinum-cloud-local`
**Date**: 2026-03-25
**Version**: 1.0.0

---

## Overview

An `APPROVE_*.md` file is written by the Cloud Agent into `Pending_Approval/` whenever an action requires human sign-off before execution. The owner approves by dragging the file to `Approved/` in Obsidian. The Local Agent polls `Approved/` and executes the contained action.

Approval files are separate from VaultTask files to allow the task to remain in `Pending_Approval/` while the approval file itself moves independently.

---

## YAML Frontmatter Schema

```yaml
---
# REQUIRED FIELDS
type: email_approval | whatsapp_reply | linkedin_post | facebook_post | x_post | social_post | odoo_invoice
status: pending_approval | approved | rejected

# TIMING
created_at: "2026-03-25T10:30:00"     # ISO 8601, set by Cloud Agent on creation
expires: "2026-03-26T10:30:00"        # ISO 8601; Local Agent MUST reject if past this time

# AUTHORSHIP
claimed_by: cloud                      # always "cloud" — only Cloud Agent creates approval files
approved_by: "" | human                # set by Local Agent after processing
approved_at: ""                        # ISO 8601; set by Local Agent when processed

# TYPE-SPECIFIC: email / whatsapp
recipient: ""                          # email address or phone number
subject: ""                            # email subject line (email type only)
message_body: ""                       # draft message content

# TYPE-SPECIFIC: social / LinkedIn
target: "" | linkedin | x | facebook  # destination platform
post_content: ""                       # draft post text
image_url: ""                          # optional image URL (instagram/facebook)

# TYPE-SPECIFIC: odoo_invoice
odoo_task_file: ""                     # filename of the linked VaultTask file
odoo_invoice_id: ~                     # Odoo draft invoice ID to post
odoo_partner_name: ""                  # human-readable partner name
odoo_amount: ~                         # float, invoice amount for display
---
```

---

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | yes | Type of action requiring approval |
| `status` | enum | yes | Lifecycle state of this approval file |
| `created_at` | ISO 8601 | yes | When Cloud Agent created this file |
| `expires` | ISO 8601 | yes | Deadline for approval; Local Agent rejects if elapsed |
| `claimed_by` | string | yes | Always `cloud` |
| `approved_by` | string | yes | Empty until Local processes; set to `human` |
| `approved_at` | ISO 8601 | yes | Empty until Local processes |
| `recipient` | string | conditional | Required for email_approval and whatsapp_reply types |
| `subject` | string | conditional | Required for email_approval type only |
| `message_body` | string | conditional | Required for email and whatsapp types |
| `target` | string | conditional | Required for social/linkedin/x/facebook types |
| `post_content` | string | conditional | Required for all social post types |
| `image_url` | string | no | Optional for social posts that include an image |
| `odoo_task_file` | string | conditional | Required for odoo_invoice type |
| `odoo_invoice_id` | integer | conditional | Required for odoo_invoice type |
| `odoo_partner_name` | string | conditional | Required for odoo_invoice type |
| `odoo_amount` | float | conditional | Required for odoo_invoice type |

---

## Expiry Policy

- Default expiry: **24 hours** from `created_at`
- Configurable via `.env`: `APPROVAL_EXPIRY_HOURS` (default: 24)
- Local Agent MUST check `expires` before executing any approved action
- If `expires` < `now()`: move file to `Rejected/`, set `status=rejected`, log the rejection
- Expired files must NOT be executed even if the owner moved them to `Approved/` — the expiry check takes precedence

---

## File Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Email reply | `APPROVE_REPLY_EMAIL_<msg_id>_<ts>.md` | `APPROVE_REPLY_EMAIL_19d2_20260325.md` |
| WhatsApp reply | `APPROVE_REPLY_WHATSAPP_<ts>.md` | `APPROVE_REPLY_WHATSAPP_20260325.md` |
| LinkedIn post | `APPROVE_POST_LINKEDIN_<date>.md` | `APPROVE_POST_LINKEDIN_20260325.md` |
| X (Twitter) post | `APPROVE_POST_X_<ts>.md` | `APPROVE_POST_X_20260325.md` |
| Facebook post | `APPROVE_POST_FACEBOOK_<ts>.md` | `APPROVE_POST_FACEBOOK_20260325.md` |
| Social (multi) | `APPROVE_POST_SOCIAL_<ts>.md` | `APPROVE_POST_SOCIAL_20260325.md` |
| Odoo invoice | `APPROVE_POST_INVOICE_<ref>_<ts>.md` | `APPROVE_POST_INVOICE_INV001.md` |

Timestamp format: `YYYYMMDDHHmmss` (compact UTC)

---

## Lifecycle

```
[Cloud Agent writes]
        |
        v
  Pending_Approval/      status=pending_approval
        |
        |-- human drags to Approved/  -->  Approved/  (Local Agent reads expires, then executes)
        |-- human drags to Rejected/  -->  Rejected/  (Local Agent logs rejection, no action)
        |-- expires elapsed            -->  Rejected/  (Local Agent moves during next poll)
        |
        v
     Done/               (after Local Agent executes successfully)
```

---

## Body (below frontmatter)

The Markdown body contains the human-readable content for the owner to review before approving:

```markdown
## Action Required

[One-sentence description of what will happen if approved]

**Expires**: [human-readable expiry time, e.g. "by 2026-03-26 10:30 UTC"]

---

## Draft Content

[The full draft email, WhatsApp message, social post, or invoice summary for the owner to read]

---

## Context

[Why this action was suggested — summary from the Cloud Agent's reasoning]
```
