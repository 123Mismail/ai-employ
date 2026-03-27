# Cloud VM Deployment Guide — Digital FTE on Oracle Cloud

This guide walks you through deploying your AI Employee (Digital FTE) on Oracle Cloud's Always Free VM so it runs 24/7 — even when your local PC is off.

---

## Architecture Overview

```
Oracle Cloud VM (24/7)             GitHub Vault Repo           Your Local PC
──────────────────────             ─────────────────           ──────────────
Cloud Agent (PM2)                  AI_Employee_Vault           Local Agent (PM2)
Gmail Watcher                      (shared via Git)            WhatsApp Watcher
Odoo (Docker)                                                  LinkedIn Watcher
PostgreSQL (Docker)                                            Obsidian Dashboard
```

**Sync**: Both VM and local PC auto git push/pull every 60 seconds via `vault_sync.py`.

---

## Prerequisites

| Requirement | VM | Local PC |
|---|---|---|
| Oracle Cloud account | yes | no |
| GitHub account | yes | yes |
| Python 3.11+ | yes | yes |
| Docker | yes | no |
| PM2 | yes | yes |
| Obsidian | no | yes |

---

## Part 1 — GitHub Vault Repository Setup (Once)

This is the shared bridge between your VM and local PC.

### 1a. Create a new GitHub repo

1. Go to **github.com** → click **"New repository"**
2. Name it: `ai-employee-vault`
3. Set to **Private**
4. Click **"Create repository"**

### 1b. Push your local vault to GitHub

Run this on your **local PC**:

```bash
cd B:\hackathone0-ai-employee\ai-employ\AI_Employee_Vault
git init
git remote add origin https://github.com/YOUR_USERNAME/ai-employee-vault.git
git add -A
git commit -m "init: vault structure"
git push -u origin main
```

---

## Part 2 — Oracle Cloud VM Setup

### 2a. Create an Oracle Cloud Account

1. Go to **cloud.oracle.com**
2. Click **"Start for free"**
3. Fill in email, password, country
4. Verify your email
5. Add credit card (for identity only — you will NOT be charged)
6. Wait for activation email (5–30 minutes)

### 2b. Create the VM Instance

1. Log into Oracle Cloud dashboard
2. Click hamburger menu (≡) → **Compute → Instances**
3. Click **"Create Instance"**
4. Set name: `ai-employee-vm`

**Shape (Important):**
- Click **"Change shape"**
- Select **"Ampere"**
- Select **`VM.Standard.A1.Flex`**
- Set OCPU: **1**, Memory: **6 GB**
- Click **"Select shape"**

**Networking:**
- Select **"Create new public subnet"**
- Set **"Assign a public IPv4 address"** = **Yes**

**SSH Keys:**
- Select **"Generate a key pair for me"**
- Click **"Save private key"** — save to `C:\Users\ACER\.ssh\oracle-ai-employee.key`
- Click **"Save public key"** — save as backup

**Storage:**
- Leave all defaults (50 GB boot volume)

5. Click **"Create"**
6. Wait 2–3 minutes for status → **"Running"**
7. Copy the **Public IP address**

> ⚠️ If you get "Out of capacity" error — change Availability Domain (try AD-1, AD-2, AD-3)

### 2c. Connect via SSH

Open **PowerShell** on your local PC:

```powershell
# Fix key permissions (run once)
icacls "C:\Users\ACER\.ssh\oracle-ai-employee.key" /inheritance:r /grant:r "%USERNAME%:R"

# Connect to VM
ssh -i C:\Users\ACER\.ssh\oracle-ai-employee.key ubuntu@YOUR_PUBLIC_IP
```

You should see:
```
Welcome to Ubuntu 22.04 LTS
ubuntu@ai-employee-vm:~$
```

---

## Part 3 — Install Dependencies on VM

Run all these commands inside the VM (after SSH).

### 3a. Update system

```bash
sudo apt update && sudo apt upgrade -y
```

### 3b. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3c. Install Python, uv, Node, PM2

```bash
sudo apt install -y python3.11 python3.11-venv git nodejs npm
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
npm install -g pm2
```

### 3d. Clone your project

```bash
git clone https://github.com/YOUR_USERNAME/ai-employ.git ~/ai-employ
cd ~/ai-employ
uv venv && uv sync
```

### 3e. Clone the vault repo

```bash
git clone https://github.com/YOUR_USERNAME/ai-employee-vault.git ~/ai-employ/AI_Employee_Vault
cd ~/ai-employ/AI_Employee_Vault
git config core.hooksPath .githooks
```

---

## Part 4 — Configure Environment

```bash
cd ~/ai-employ
cp .env.example .env.cloud
nano .env.cloud
```

Set these values:

```env
# Vault
VAULT_PATH=/home/ubuntu/ai-employ/AI_Employee_Vault
AGENT_ROLE=cloud

# Git sync
VAULT_GIT_REMOTE=origin
VAULT_SYNC_INTERVAL=60

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Gmail
GMAIL_CREDENTIALS_PATH=/home/ubuntu/ai-employ/credentials.json
GMAIL_TOKEN_PATH=/home/ubuntu/ai-employ/token.json
GMAIL_QUERY=subject:testing is:unread

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=admin

# Safety
STALE_TASK_TIMEOUT_MINUTES=30
APPROVAL_EXPIRY_HOURS=24
DRY_RUN=false
```

Press `Ctrl+X` → `Y` → `Enter` to save.

---

## Part 5 — Start Odoo with Docker

```bash
cd ~/ai-employ
docker compose up -d
```

Wait 2 minutes then verify:

```bash
docker ps
```

Expected output:
```
odoo-app    running
odoo-db     running
```

Initialize Odoo database:

```bash
docker exec odoo-app odoo --init base --stop-after-init
docker exec odoo-app odoo --init account --stop-after-init
```

Test connection:

```bash
uv run python -c "
from dotenv import load_dotenv
load_dotenv('.env.cloud')
from PlatinumTier.scripts.odoo_client import connect
m, uid, db, pwd = connect()
print('Odoo connected! uid=', uid)
"
```

---

## Part 6 — Upload Gmail Credentials

Copy your `credentials.json` and `token.json` from local PC to VM:

```powershell
# Run on your LOCAL PC in PowerShell
scp -i C:\Users\ACER\.ssh\oracle-ai-employee.key C:\path\to\credentials.json ubuntu@YOUR_PUBLIC_IP:~/ai-employ/
scp -i C:\Users\ACER\.ssh\oracle-ai-employee.key C:\path\to\token.json ubuntu@YOUR_PUBLIC_IP:~/ai-employ/
```

---

## Part 7 — Start Cloud Agent with PM2

```bash
cd ~/ai-employ
pm2 start PlatinumTier/deploy/ecosystem.cloud.config.js
pm2 save

# Enable auto-start on VM reboot
pm2 startup
# Copy and run the command it outputs
```

Verify it's running:

```bash
pm2 list
```

Expected:
```
cloud-agent    online
```

---

## Part 8 — Verify Everything Works

### Check health

```bash
cat ~/ai-employ/AI_Employee_Vault/Logs/health_cloud.json
```

Should show:
```json
{
  "status": "running",
  "agent": "cloud"
}
```

### Check logs

```bash
pm2 logs cloud-agent --lines 20
```

Should show agent scanning for tasks every 30 seconds.

---

## Part 9 — Local PC Final Setup

On your **local PC**, update your `.env` to point vault to GitHub:

```env
VAULT_PATH=B:\hackathone0-ai-employee\ai-employ\AI_Employee_Vault
VAULT_GIT_REMOTE=origin
VAULT_SYNC_INTERVAL=60
```

Restart local agents:

```bash
pm2 restart all
```

---

## How It All Works Together

```
1. Email arrives in Gmail
        ↓
2. Cloud Agent (VM) picks it up
        ↓
3. Drafts reply using OpenAI
        ↓
4. Writes approval file → git push to GitHub
        ↓
5. Local PC git pulls → Obsidian shows the file
        ↓
6. You drag file to Approved/ in Obsidian
        ↓
7. Local PC git pushes → VM git pulls
        ↓
8. Local Agent sends the email ✅
```

---

## Daily Workflow (After Setup)

You only do **one thing** manually:

1. Open Obsidian in the morning
2. See pending approvals (VM worked overnight)
3. Drag files to `Approved/`
4. Local agent executes actions automatically

**Everything else is fully automated 24/7.**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| SSH connection refused | Check VM is running, port 22 open in Oracle Security List |
| Out of capacity error | Try different Availability Domain (AD-1, AD-2, AD-3) |
| No public IP on VM | Recreate with "Assign public IPv4 = Yes" in networking |
| Cloud agent not starting | Run `pm2 logs cloud-agent` to see the error |
| Odoo not reachable | Run `docker ps` to check containers are running |
| Git push/pull failing | Check GitHub credentials and remote URL in vault |
| Approval file not appearing in Obsidian | Check vault sync is running: `pm2 logs cloud-agent \| grep sync` |

---

## Important Notes

- ✅ `.env.cloud` is safe on the VM — only you can SSH in
- ✅ `.env` is in `.gitignore` — never pushed to GitHub
- ✅ PM2 auto-restarts cloud agent if it crashes
- ✅ Oracle A1.Flex VM is **free forever** — no charges
- ✅ Odoo runs locally on the VM — no SaaS API keys needed
