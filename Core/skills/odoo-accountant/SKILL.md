---
name: odoo-accountant
description: Integrates with Odoo Community (v19+) to manage business finances. Use to check bank balances, create draft invoices, and reconcile transactions via the Odoo JSON-RPC API.
---

# Odoo Accountant

## Overview
Connects the AI Employee's reasoning to the business's official financial source of truth.

## Workflow
1. **Connect**: Authenticate with local/self-hosted Odoo via `JSON-RPC`.
2. **Retrieve**: Pull latest transaction data or invoice status.
3. **Report**: Write financial summaries into `AI_Employee_Vault/Accounting/`.
4. **Draft**: Create invoices in Odoo as "Drafts" for human validation.

## Technical Details
- Endpoint: `http://localhost:8069/jsonrpc` (Default).
- Method: Uses Python's standard `xmlrpc.client` or generic JSON-RPC.
- Constraint: Never "Post" or "Validate" payments automatically; stay in Draft state.
