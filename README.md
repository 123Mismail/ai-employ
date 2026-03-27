# Personal AI Employee

An autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using a **Perception → Reasoning → Action** architecture with Obsidian as the central dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     PERCEPTION LAYER                    │
│  BronzeTier/watchers/filesystem.py  (Inbox drop zone)  │
│  SilverTier/watchers/gmail.py        (Gmail polling)   │
│  SilverTier/watchers/whatsapp.py     (WhatsApp Web)    │
└─────────────────────┬───────────────────────────────────┘
                      │ writes .md files to Needs_Action/
┌─────────────────────▼───────────────────────────────────┐
│                     REASONING LAYER                     │
│  Core/scripts/orchestrator.py  (Master Orchestrator)   │
│  Core/scripts/skills/vault_processor.py                │
│  Core/scripts/skills/smart_agent.py  (GPT-4o-mini)    │
└─────────────────────┬───────────────────────────────────┘
                      │ writes approval files to Pending_Approval/
                      │ human moves to Approved/ (HITL gate)
┌─────────────────────▼───────────────────────────────────┐
│                      ACTION LAYER                       │
│  SilverTier/skills/email_action.py   (Gmail API)       │
│  SilverTier/skills/whatsapp_reply.py (Playwright)      │
│  GoldTier/skills/linkedin_post.py    (Playwright)      │
│  GoldTier/skills/social_post.py      (X, FB, Instagram)│
│  GoldTier/skills/odoo_skill.py       (XML-RPC)         │
│  GoldTier/skills/business_auditor.py (CEO Briefing)    │
└─────────────────────────────────────────────────────────┘
```

## Vault Folder Workflow

```
Inbox/drop_zone/  →  Needs_Action/  →  Plans/  →  Pending_Approval/
                                                         │
                                              (human drag-drop in Obsidian)
                                                         │
                                                     Approved/  →  Done/
                                                     Rejected/
```

---

## Setup

### 1. Prerequisites

- Python 3.13+
- Node.js v24+ (for PM2)
- Obsidian v1.10.6+
- UV package manager

### 2. Install dependencies

```bash
uv sync
playwright install chromium
```

### 3. Configure credentials

Copy the example below into a `.env` file at the project root:

```env
# AI
OPENAI_API_KEY=your_key

# Gmail (download credentials.json from Google Cloud Console)
GMAIL_QUERY=is:unread is:important

# WhatsApp
WHATSAPP_OWNER_NAME="Mine(You)"
WHATSAPP_NUMBER=+1234567890

# LinkedIn
LINKEDIN_MOCK=true

# Social Media
# X_API_KEY=...
# X_API_SECRET=...
# X_ACCESS_TOKEN=...
# X_ACCESS_TOKEN_SECRET=...
# FB_ACCESS_TOKEN=...

# Instagram (requires Facebook Business Page linked to IG Business Account)
# INSTAGRAM_BUSINESS_ACCOUNT_ID=...
# INSTAGRAM_ACCESS_TOKEN=...
# INSTAGRAM_IMAGE_URL=https://example.com/image.jpg

# Odoo ERP
# ODOO_URL=https://your-instance.odoo.com
# ODOO_DB=your_db
# ODOO_USERNAME=...
# ODOO_PASSWORD=...

# Safety
DRY_RUN=false
```

### 4. Authenticate Gmail

```bash
uv run python SilverTier/scripts/utils/google_auth.py
```

### 5. Save browser sessions (one-time)

```bash
uv run python Core/scripts/utils/handshake.py linkedin
uv run python Core/scripts/utils/handshake.py whatsapp
```

### 6. Initialize the Vault

```bash
uv run python BronzeTier/scripts/init_vault.py
```

---

## Running

### Development (all-in-one)

```bash
uv run python main.py
```

### Production (PM2)

```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## Safety Flags

| Env Var | Default | Purpose |
|---|---|---|
| `DRY_RUN=true` | `false` | Log all actions without executing them |
| `LINKEDIN_MOCK=true` | `true` | Skip real LinkedIn browser automation |
| `GMAIL_QUERY` | `is:unread is:important` | Control which emails are picked up |

---

## Tier Completion

| Tier | Status | Key Features |
|---|---|---|
| Bronze | Complete | Vault, filesystem watcher, HITL flow |
| Silver | Complete | Gmail + WhatsApp watchers, email send, LinkedIn post |
| Gold | Complete | Odoo, X/Twitter, Facebook, Instagram, CEO Briefing, Ralph Wiggum loop |
| Platinum | Not started | Cloud deployment, dual-agent Cloud+Local split |

---

## Project Structure

```
ai-employ/
├── main.py                        # Dev launcher
├── ecosystem.config.js            # PM2 production config
├── AI_Employee_Vault/             # Obsidian vault
│   ├── Dashboard.md
│   ├── Company_Handbook.md
│   ├── Business_Goals.md
│   ├── Needs_Action/
│   ├── Plans/
│   ├── Pending_Approval/
│   ├── Approved/
│   ├── Done/
│   └── Logs/
├── Core/
│   └── scripts/
│       ├── orchestrator.py
│       ├── skills/
│       │   ├── vault_processor.py
│       │   └── smart_agent.py
│       └── utils/
│           ├── base_watcher.py
│           ├── retry_handler.py
│           ├── rate_limiter.py
│           └── handshake.py
├── BronzeTier/
│   └── scripts/
│       ├── init_vault.py
│       └── watchers/filesystem.py
├── SilverTier/
│   └── scripts/
│       ├── watchers/
│       │   ├── gmail.py
│       │   └── whatsapp.py
│       ├── skills/
│       │   ├── email_action.py
│       │   └── whatsapp_reply.py
│       └── utils/google_auth.py
└── GoldTier/
    └── scripts/
        └── skills/
            ├── linkedin_post.py
            ├── social_post.py
            ├── odoo_skill.py
            └── business_auditor.py
```
