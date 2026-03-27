# Data Model: LinkedIn Advanced Engagement

**Feature**: 005-linkedin-engagement
**Date**: 2026-03-26

---

## Entities

### 1. LinkedInEngagementTask (Vault file — `Needs_Action/`)

Three sub-types, all sharing a common frontmatter structure:

**LINKEDIN_REPLY_{notification_id}_{ts}.md** — comment reply task
```yaml
---
type: linkedin_reply
source: linkedin_notifications
notification_id: "urn:li:notification:12345678"
post_url: "https://www.linkedin.com/feed/update/urn:li:activity:..."
commenter_name: "Jane Doe"
commenter_headline: "ML Engineer @ Anthropic"
comment_snippet: "This is exactly what we've been building..."
timestamp: "2026-03-26T10:30:00"
status: pending
---
```

**LINKEDIN_COMMENT_{post_id}_{ts}.md** — comment on others' post task
```yaml
---
type: linkedin_comment
source: linkedin_feed
post_url: "https://www.linkedin.com/feed/update/urn:li:activity:..."
post_author: "Sam Altman"
post_author_headline: "CEO @ OpenAI"
post_snippet: "The next wave of AI agents will be..."
keywords_matched: ["AI agents", "autonomous"]
timestamp: "2026-03-26T10:35:00"
status: pending
---
```

**LINKEDIN_CONNECT_{profile_id}_{ts}.md** — connection request task
```yaml
---
type: linkedin_connect
source: linkedin_people_search
profile_url: "https://www.linkedin.com/in/username/"
candidate_name: "Ali Hassan"
candidate_headline: "Founder @ AI Startup | LLM Engineer"
candidate_company: "AgentFlow AI"
search_keywords: "AI agent founder"
timestamp: "2026-03-26T10:40:00"
status: pending
---
```

**State transitions**: `pending` → `pending_approval` (claimed by cloud agent) → `done`

---

### 2. EngagementApproval (Vault file — `Pending_Approval/`)

**APPROVE_REPLY_LINKEDIN_{notification_id}_{ts}.md**
```yaml
---
type: linkedin_reply_approval
status: pending_approval
created_at: "2026-03-26 10:31"
expires: "2026-03-27 10:31"
claimed_by: cloud
approved_by: ""
approved_at: ""
post_url: "https://www.linkedin.com/feed/update/urn:li:activity:..."
commenter_name: "Jane Doe"
reply_body: "Jane, great point! The pattern you're describing is exactly what..."
---
```

**APPROVE_COMMENT_LINKEDIN_{post_id}_{ts}.md**
```yaml
---
type: linkedin_comment_approval
status: pending_approval
created_at: "2026-03-26 10:36"
expires: "2026-03-27 10:36"
claimed_by: cloud
approved_by: ""
approved_at: ""
post_url: "https://www.linkedin.com/feed/update/urn:li:activity:..."
post_author: "Sam Altman"
comment_body: "The shift from single-step LLMs to multi-agent orchestration..."
---
```

**APPROVE_CONNECT_LINKEDIN_{profile_id}_{ts}.md**
```yaml
---
type: linkedin_connect_approval
status: pending_approval
created_at: "2026-03-26 10:41"
expires: "2026-03-27 10:41"
claimed_by: cloud
approved_by: ""
approved_at: ""
profile_url: "https://www.linkedin.com/in/username/"
candidate_name: "Ali Hassan"
candidate_headline: "Founder @ AgentFlow AI"
connection_note: "Hi Ali — your work on LLM orchestration at AgentFlow caught my eye..."
---
```

**State transitions**: `pending_approval` → moved to `Approved/` by human → claimed to `In_Progress/local/` → `Done/` or `Rejected/`

---

### 3. RateLimitState (JSON file — `AI_Employee_Vault/Logs/linkedin_rate_state.json`)

```json
{
  "date": "2026-03-26",
  "comments_today": 3,
  "connections_today": 1,
  "comment_limit": 10,
  "connection_limit": 5,
  "account_paused": false,
  "pause_reason": "",
  "last_action_at": "2026-03-26T14:22:00"
}
```

**Validation rules**:
- `comments_today` must never exceed `comment_limit`
- `connections_today` must never exceed `connection_limit`
- When `date` != today → reset `comments_today` and `connections_today` to 0, update `date`
- `account_paused: true` blocks ALL LinkedIn execution regardless of other fields
- Only a human (manual edit) can set `account_paused: false`

---

### 4. DeduplicationRegistry (flat text files — repo root)

| File | Contains | Updated when |
|---|---|---|
| `processed_linkedin_comments.txt` | `notification_id` per line | Watcher creates a reply task |
| `processed_linkedin_posts.txt` | `post_url` per line | Watcher creates a comment task |
| `processed_linkedin_profiles.txt` | `profile_url` per line | Watcher creates a connect task |

**Loaded** into a Python `set()` at watcher startup. **Checked** O(1) per candidate. **Appended** atomically (open mode `"a"`) on new task creation.

---

### 5. SessionLock (lock file — `linkedin_session/browser.lock`)

```
PID: 12345
acquired_at: 2026-03-26T10:30:00
holder: silver-linkedin-watcher
```

**Acquisition logic**:
1. Check if file exists and PID is alive → if yes, wait up to 60s polling every 5s
2. If PID dead or timeout → force-delete lock and acquire
3. Write own PID + timestamp + holder name to file
4. Delete file in `finally` block after browser context closes

---

## State Machine Summary

```
WATCHER DETECTS
      │
      ▼
Needs_Action/LINKEDIN_{TYPE}_{id}_{ts}.md   [status: pending]
      │
      │ cloud_agent picks up (10s poll)
      ▼
Plans/LINKEDIN_{TYPE}_{id}_{ts}.md          [status: pending_approval]
+ Pending_Approval/APPROVE_{TYPE}_{id}_{ts}.md
      │
      │ human drags to Approved/ in Obsidian
      ▼
Approved/APPROVE_{TYPE}_{id}_{ts}.md
      │
      │ local_agent picks up (10s poll)
      │ → rate limit check
      │ → claim to In_Progress/local/
      ▼
In_Progress/local/APPROVE_{TYPE}_{id}_{ts}.md
      │
      ├─ success ──► Done/  [audit logged]
      └─ failure ──► Rejected/  [audit logged]
```
