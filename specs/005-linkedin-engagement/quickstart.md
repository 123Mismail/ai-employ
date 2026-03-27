# Quickstart: LinkedIn Advanced Engagement

**Feature**: 005-linkedin-engagement
**Date**: 2026-03-26

## Prerequisites

- LinkedIn already authenticated in `linkedin_session/` (existing — from GoldTier)
- PM2 running with `platinum-cloud-agent` and `platinum-local-agent` online
- `.env` file present at repo root with `OPENAI_API_KEY` set

## Step 1 — Add env vars to `.env`

```bash
LINKEDIN_KEYWORDS=AI agents,LLM,autonomous,Digital FTE,Claude,OpenAI,AI startup
LINKEDIN_CONNECT_KEYWORDS=AI agent founder,LLM engineer,AI startup founder
LINKEDIN_POLL_INTERVAL=120
LINKEDIN_COMMENT_LIMIT=10
LINKEDIN_CONNECTION_LIMIT=5
```

## Step 2 — Start the LinkedIn watcher

```bash
pm2 delete silver-linkedin-watcher 2>/dev/null
pm2 start ecosystem.config.js --only silver-linkedin-watcher
pm2 logs silver-linkedin-watcher --lines 20
```

Expected startup log:
```
Starting LinkedIn Engagement Watcher (poll every 120s)...
Session lock acquired
Polling notifications for comment replies...
Found 0 new comment notifications
Feed scan: checking for AI posts...
Session lock released
```

## Step 3 — Trigger a test (P1: Reply flow)

1. From another account or phone, comment on one of your LinkedIn posts
2. Wait up to 2 minutes for the watcher poll cycle
3. Check `AI_Employee_Vault/Needs_Action/` — a `LINKEDIN_REPLY_*.md` file should appear
4. Wait ~30s for cloud agent to draft the reply
5. Check `AI_Employee_Vault/Pending_Approval/` — `APPROVE_REPLY_LINKEDIN_*.md` appears
6. Open in Obsidian, read the draft, drag to `Approved/`
7. Local agent executes within 10s — reply appears on LinkedIn

## Step 4 — Verify rate limit state

```bash
cat AI_Employee_Vault/Logs/linkedin_rate_state.json
```

Expected after one reply:
```json
{
  "date": "2026-03-26",
  "comments_today": 0,
  "connections_today": 0,
  "account_paused": false,
  ...
}
```
*(Replies are not rate-limited — only comments on others' posts and connection requests)*

## Step 5 — Trigger P2 (Comment on others' posts)

Drop a task file manually to test without waiting for feed scan:

```bash
cat > AI_Employee_Vault/Needs_Action/LINKEDIN_COMMENT_test_$(date +%Y%m%d%H%M%S).md << 'EOF'
---
type: linkedin_comment
source: linkedin_feed
post_url: "https://www.linkedin.com/feed/update/urn:li:activity:TEST"
post_author: "Test Author"
post_author_headline: "AI Engineer"
post_snippet: "The rise of autonomous AI agents is reshaping how we think about digital work..."
keywords_matched: ["AI agents", "autonomous"]
timestamp: "2026-03-26T10:00:00"
status: pending
---
EOF
```

Watch cloud agent draft a comment → approve → local agent posts.

## Monitoring

```bash
# Live watcher logs
pm2 logs silver-linkedin-watcher --lines 50

# Rate limit state
cat AI_Employee_Vault/Logs/linkedin_rate_state.json

# Audit trail
tail -5 AI_Employee_Vault/Logs/2026-03-26.json | python -m json.tool

# All processes
pm2 list
```

## If account_paused is true

```bash
# 1. Check the reason
cat AI_Employee_Vault/Logs/linkedin_rate_state.json | python -m json.tool

# 2. Go to LinkedIn manually, resolve any challenge/CAPTCHA
# 3. Only then clear the pause:
python -c "
import json; from pathlib import Path
p = Path('AI_Employee_Vault/Logs/linkedin_rate_state.json')
s = json.loads(p.read_text())
s['account_paused'] = False
s['pause_reason'] = ''
p.write_text(json.dumps(s, indent=2))
print('Pause cleared')
"

# 4. Restart the watcher
pm2 restart silver-linkedin-watcher
```
