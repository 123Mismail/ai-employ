# Quickstart: Platinum Tier — Cloud + Local AI Employee

**Feature**: `004-platinum-cloud-local`
**Date**: 2026-03-25

---

## Prerequisites

| Requirement | Cloud VM | Local Machine |
|-------------|----------|---------------|
| Python 3.11+ | yes | yes |
| Git | yes | yes |
| Docker + Docker Compose | yes | no |
| PM2 (`npm install -g pm2`) | yes | yes |
| uv (`pip install uv`) | yes | yes |
| Obsidian | no | yes |

---

## Part 1: Vault Git Repository Setup (once)

Run this once — on any machine. Creates the shared vault repo on GitHub.

```bash
# 1. Create the vault directory
mkdir AI_Employee_Vault && cd AI_Employee_Vault
git init

# 2. Create the folder structure
mkdir -p Needs_Action "In_Progress/cloud" "In_Progress/local" Plans \
         Pending_Approval Approved Rejected Done Logs Briefings "Inbox/drop_zone"

# 3. Create placeholder files (git won't track empty dirs)
touch Needs_Action/.gitkeep "In_Progress/cloud/.gitkeep" "In_Progress/local/.gitkeep" \
      Plans/.gitkeep Pending_Approval/.gitkeep Approved/.gitkeep Rejected/.gitkeep \
      Done/.gitkeep Logs/.gitkeep Briefings/.gitkeep "Inbox/drop_zone/.gitkeep"

# 4. Create starter vault files
echo "# Dashboard" > Dashboard.md
echo "# Company Handbook" > Company_Handbook.md
echo "# Business Goals" > Business_Goals.md

# 5. Configure merge strategy
cat > .gitattributes << 'EOF'
*.md merge=union
*.json merge=ours
EOF

# 6. Create .gitignore for secrets
cat > .gitignore << 'EOF'
.env
token.json
credentials.json
whatsapp_session/
linkedin_session/
processed_emails.txt
processed_chats.txt
rate_limit_state.json
*.pyc
__pycache__/
EOF

# 7. Create pre-push hook directory
mkdir -p .githooks
cat > .githooks/pre-push << 'HOOK'
#!/bin/bash
# Block secret files from being pushed
FORBIDDEN="\.env|token\.json|credentials\.json|whatsapp_session/|linkedin_session/|processed_emails\.txt|processed_chats\.txt"
if git diff --cached --name-only | grep -qE "$FORBIDDEN"; then
  echo "ERROR: Attempt to push secret/credential files blocked."
  echo "Remove the sensitive files and try again."
  exit 1
fi
HOOK
chmod +x .githooks/pre-push

# 8. Configure git to use the hooks
git config core.hooksPath .githooks

# 9. Commit and push
git add -A
git commit -m "init: Platinum vault structure"
git remote add origin git@github.com:<YOUR_USERNAME>/ai-employee-vault.git
git push -u origin main
```

---

## Part 2: Cloud VM Setup (Oracle Always Free — Ampere A1)

### 2a. Provision the VM

1. Log into [cloud.oracle.com](https://cloud.oracle.com)
2. Create a VM: **Compute > Instances > Create Instance**
   - Shape: `VM.Standard.A1.Flex` — 4 OCPU, 24 GB RAM
   - OS: Ubuntu 22.04 (aarch64)
   - Boot volume: 100 GB
3. Note the public IP. Set a DNS A record (e.g. `ai.yourdomain.com → <public IP>`).
4. Open ports 80 and 443 in the OCI Security List.

### 2b. Install dependencies on Cloud VM

```bash
# SSH into the VM
ssh ubuntu@<YOUR_VM_IP>

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Python 3.11, uv, PM2
sudo apt update && sudo apt install -y python3.11 python3.11-venv git
curl -LsSf https://astral.sh/uv/install.sh | sh
npm install -g pm2
```

### 2c. Clone vault and code repos

```bash
# Clone vault
git clone git@github.com:<YOUR_USERNAME>/ai-employee-vault.git ~/AI_Employee_Vault
cd ~/AI_Employee_Vault
git config core.hooksPath .githooks
git config merge.union.driver "union"

# Clone code repo
git clone git@github.com:<YOUR_USERNAME>/ai-employ.git ~/ai-employ
cd ~/ai-employ
uv venv && uv pip install -r requirements.txt
```

### 2d. Configure Cloud .env

```bash
cp .env.example .env.cloud
nano .env.cloud
```

Required values for cloud:

```env
# Vault
VAULT_PATH=/home/ubuntu/AI_Employee_Vault
AGENT_ROLE=cloud
AGENT_VERSION=1.0.0

# Git sync
VAULT_GIT_REMOTE=origin
VAULT_SYNC_INTERVAL=60

# Gmail (Cloud watcher)
GMAIL_CREDENTIALS_PATH=/home/ubuntu/credentials.json
GMAIL_TOKEN_PATH=/home/ubuntu/token.json
GMAIL_QUERY=is:unread is:important

# Stale task recovery
STALE_TASK_TIMEOUT_MINUTES=30

# Approval expiry
APPROVAL_EXPIRY_HOURS=24

# Odoo (Cloud draft-only)
ODOO_URL=http://localhost:8069
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=your_odoo_password

# Dry run (set to true for safe testing)
DRY_RUN=false
```

### 2e. Deploy Odoo with Docker Compose

```bash
mkdir -p ~/odoo-deploy && cd ~/odoo-deploy

cat > docker-compose.yml << 'EOF'
version: "3.9"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: odoo_db
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: ${ODOO_DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  odoo:
    image: odoo:17
    depends_on: [db]
    environment:
      HOST: db
      USER: odoo
      PASSWORD: ${ODOO_DB_PASSWORD}
    volumes:
      - odoo_filestore:/var/lib/odoo
    ports:
      - "8069:8069"
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped

volumes:
  pgdata:
  odoo_filestore:
  caddy_data:
EOF

cat > Caddyfile << 'EOF'
ai.yourdomain.com {
    reverse_proxy odoo:8069
}
EOF

# Start stack
ODOO_DB_PASSWORD=your_secure_password docker compose up -d
```

### 2f. Start Cloud Agent with PM2

```bash
cd ~/ai-employ

cat > ecosystem.cloud.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: "cloud-agent",
      script: "/home/ubuntu/ai-employ/.venv/bin/python",
      args: "PlatinumTier/scripts/cloud_agent.py",
      env: {
        PYTHONUNBUFFERED: "1",
        ENV_FILE: "/home/ubuntu/ai-employ/.env.cloud"
      },
      restart_delay: 5000,
      max_restarts: 10,
      exec_mode: "fork"
    }
  ]
}
EOF

pm2 start ecosystem.cloud.config.js
pm2 save
pm2 startup  # follow the output instructions to enable auto-start on reboot
```

---

## Part 3: Local Machine Setup

### 3a. Clone vault and code repos

```bash
# Clone vault (same remote as Cloud VM)
git clone git@github.com:<YOUR_USERNAME>/ai-employee-vault.git ~/AI_Employee_Vault
cd ~/AI_Employee_Vault
git config core.hooksPath .githooks
git config merge.union.driver "union"

# Clone code repo
git clone git@github.com:<YOUR_USERNAME>/ai-employ.git ~/ai-employ
cd ~/ai-employ
uv venv && uv pip install -r requirements.txt
```

### 3b. Open vault in Obsidian

1. Open Obsidian → **Open folder as vault** → select `~/AI_Employee_Vault`
2. The folder structure should be visible in the left sidebar

### 3c. Configure Local .env

```bash
cp .env.example .env.local
nano .env.local
```

Required values for local:

```env
# Vault
VAULT_PATH=/Users/you/AI_Employee_Vault   # adjust for your OS
AGENT_ROLE=local
AGENT_VERSION=1.0.0

# Git sync
VAULT_GIT_REMOTE=origin
VAULT_SYNC_INTERVAL=60

# Gmail (Local send-only)
GMAIL_CREDENTIALS_PATH=/Users/you/credentials.json
GMAIL_TOKEN_PATH=/Users/you/token.json

# WhatsApp
WHATSAPP_SESSION_PATH=/Users/you/whatsapp_session

# LinkedIn
LINKEDIN_SESSION_PATH=/Users/you/linkedin_session

# Odoo (Local post/confirm)
ODOO_URL=https://ai.yourdomain.com
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=your_odoo_password

# Stale task recovery
STALE_TASK_TIMEOUT_MINUTES=30

# Dry run (set to true for safe testing)
DRY_RUN=false
```

### 3d. Start Local Agent with PM2

```bash
cd ~/ai-employ

cat > ecosystem.local.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: "local-agent",
      script: "/Users/you/ai-employ/.venv/bin/python",
      args: "PlatinumTier/scripts/local_agent.py",
      env: {
        PYTHONUNBUFFERED: "1",
        ENV_FILE: "/Users/you/ai-employ/.env.local"
      },
      restart_delay: 5000,
      max_restarts: 10,
      exec_mode: "fork"
    }
  ]
}
EOF

pm2 start ecosystem.local.config.js
pm2 save
pm2 startup
```

---

## Part 4: Verify Setup

### 4a. Health check

```bash
# Cloud VM
cat ~/AI_Employee_Vault/Logs/health_cloud.json

# Local machine
cat ~/AI_Employee_Vault/Logs/health_local.json
```

Both files should have `"status": "running"` and a `timestamp` within the last 2 minutes.

### 4b. End-to-end smoke test

1. **Disable Wi-Fi** on the Local machine
2. Send a test email to your Gmail inbox with subject `[TEST] Platinum Demo`
3. Wait up to 5 minutes
4. **Re-enable Wi-Fi** — vault syncs within 60 seconds
5. In Obsidian, check `Pending_Approval/` for an `APPROVE_REPLY_EMAIL_*.md` file
6. Drag the file to `Approved/`
7. Within 60 seconds, the email is sent and the task file appears in `Done/`

### 4c. Secret leak check

```bash
# Run on the cloud VM after any push:
git ls-tree -r HEAD --name-only | grep -E "\.env|token\.json|credentials\.json|whatsapp_session|linkedin_session"
# Expected output: (empty — no matches)
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `health_cloud.json` timestamp is stale (>3 min) | `pm2 logs cloud-agent` on Cloud VM |
| Approval file doesn't appear after email arrives | Check `Logs/YYYY-MM-DD.json` on Cloud VM for errors |
| Local agent doesn't send email after approval | Check `expires:` field in the approval file; may have expired |
| Git push blocked by pre-push hook | Remove the flagged secret file from staging with `git reset HEAD <file>` |
| Odoo unreachable | `docker compose ps` in `~/odoo-deploy`; check Caddy logs |
| Stale task not recovered | Verify `STALE_TASK_TIMEOUT_MINUTES` env var; check `Logs/` for `stale_recovery` entries |
