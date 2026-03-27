#!/usr/bin/env bash
# vault-init.sh — Idempotent Platinum vault bootstrap
# Safe to run multiple times. Run once after cloning the vault repo.
# Usage: bash vault-init.sh /path/to/AI_Employee_Vault

set -euo pipefail

VAULT_PATH="${1:-$VAULT_PATH}"
if [ -z "$VAULT_PATH" ]; then
  echo "ERROR: pass vault path as argument or set VAULT_PATH env var"
  exit 1
fi

echo "[vault-init] Bootstrapping vault at: $VAULT_PATH"
cd "$VAULT_PATH"

# 1. Create folder structure with .gitkeep files
FOLDERS=(
  "Needs_Action"
  "In_Progress/cloud"
  "In_Progress/local"
  "Plans"
  "Pending_Approval"
  "Approved"
  "Rejected"
  "Done"
  "Logs"
  "Briefings"
  "Inbox/drop_zone"
)
for folder in "${FOLDERS[@]}"; do
  mkdir -p "$folder"
  touch "$folder/.gitkeep"
done
echo "[vault-init] Folders created"

# 2. Write .gitattributes (union merge for .md, ours for .json)
cat > .gitattributes << 'EOF'
*.md merge=union
*.json merge=ours
EOF
echo "[vault-init] .gitattributes written"

# 3. Write .gitignore
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
.DS_Store
EOF
echo "[vault-init] .gitignore written"

# 4. Write pre-push hook
mkdir -p .githooks
cat > .githooks/pre-push << 'HOOK'
#!/bin/bash
# Block secret/credential files from being pushed to the remote vault repo
FORBIDDEN="\.env$|token\.json$|credentials\.json$|whatsapp_session/|linkedin_session/|processed_emails\.txt$|processed_chats\.txt$|rate_limit_state\.json$"

STAGED=$(git diff --cached --name-only 2>/dev/null)
if echo "$STAGED" | grep -qE "$FORBIDDEN"; then
  echo ""
  echo "ERROR: Pre-push hook blocked — secret/credential file detected in staged files:"
  echo "$STAGED" | grep -E "$FORBIDDEN"
  echo ""
  echo "Remove the sensitive file(s) from staging with: git reset HEAD <file>"
  echo ""
  exit 1
fi
HOOK
chmod +x .githooks/pre-push
echo "[vault-init] pre-push hook written and made executable"

# 5. Configure git to use .githooks/
git config core.hooksPath .githooks
echo "[vault-init] git hooks path set to .githooks/"

# 6. Create starter vault files if missing
[ -f Dashboard.md ]        || echo "# Dashboard"        > Dashboard.md
[ -f Company_Handbook.md ] || echo "# Company Handbook" > Company_Handbook.md
[ -f Business_Goals.md ]   || echo "# Business Goals"   > Business_Goals.md

echo "[vault-init] Done — vault is ready"
echo ""
echo "Next: git add -A && git commit -m 'init: Platinum vault structure' && git push"
