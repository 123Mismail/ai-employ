# File Contracts: LinkedIn Advanced Engagement

**Feature**: 005-linkedin-engagement
**Date**: 2026-03-26

This document defines the file-based interface contracts between all components.
Since the system uses file-based communication (not HTTP APIs), contracts are defined
as file schemas, naming conventions, and processing guarantees.

---

## Contract 1: Watcher → Vault (Task Creation)

**Producer**: `silver-linkedin-watcher`
**Consumer**: `platinum-cloud-agent`
**Channel**: `AI_Employee_Vault/Needs_Action/`

### Reply Task
```
File: LINKEDIN_REPLY_{notification_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_reply"              # MUST be exactly this string
  - notification_id: str                # LinkedIn notification URN
  - post_url: str                       # Full LinkedIn post URL
  - commenter_name: str                 # Display name of commenter
  - comment_snippet: str                # First 200 chars of comment
  - timestamp: ISO-8601 local datetime
  - status: "pending"
```

### Comment Task
```
File: LINKEDIN_COMMENT_{post_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_comment"            # MUST be exactly this string
  - post_url: str                       # Full LinkedIn post URL
  - post_author: str                    # Author display name
  - post_snippet: str                   # First 300 chars of post text
  - keywords_matched: list[str]         # Which keywords triggered detection
  - timestamp: ISO-8601 local datetime
  - status: "pending"
```

### Connect Task
```
File: LINKEDIN_CONNECT_{profile_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_connect"            # MUST be exactly this string
  - profile_url: str                    # Full LinkedIn profile URL
  - candidate_name: str                 # Display name
  - candidate_headline: str             # LinkedIn headline
  - candidate_company: str              # Current company (if extractable)
  - search_keywords: str               # Search query that found this person
  - timestamp: ISO-8601 local datetime
  - status: "pending"
```

**Guarantees**:
- Watcher MUST NOT create a task if the ID/URL already exists in the deduplication registry
- Watcher MUST append the ID/URL to the deduplication file immediately after task creation
- Watcher MUST use UTF-8 encoding for all file writes

---

## Contract 2: Cloud Agent → Vault (Approval Creation)

**Producer**: `platinum-cloud-agent` (via cloud handlers)
**Consumer**: human (Obsidian) → `platinum-local-agent`
**Channel**: `AI_Employee_Vault/Pending_Approval/`

### Reply Approval
```
File: APPROVE_REPLY_LINKEDIN_{notification_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_reply_approval"     # Exact string for local agent routing
  - status: "pending_approval"
  - created_at: "YYYY-MM-DD HH:MM"     # Human-readable local time
  - expires: "YYYY-MM-DD HH:MM"        # 24 hours after created_at
  - post_url: str                       # Passed through from task
  - commenter_name: str                 # For display in Obsidian
  - reply_body: str                     # AI-drafted reply text
  - approved_by: ""
  - approved_at: ""
```

### Comment Approval
```
File: APPROVE_COMMENT_LINKEDIN_{post_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_comment_approval"
  - status: "pending_approval"
  - created_at: "YYYY-MM-DD HH:MM"
  - expires: "YYYY-MM-DD HH:MM"
  - post_url: str
  - post_author: str
  - comment_body: str                   # AI-drafted comment text
  - approved_by: ""
  - approved_at: ""
```

### Connect Approval
```
File: APPROVE_CONNECT_LINKEDIN_{profile_id}_{YYYYMMDDHHmmss}.md
Required frontmatter fields:
  - type: "linkedin_connect_approval"
  - status: "pending_approval"
  - created_at: "YYYY-MM-DD HH:MM"
  - expires: "YYYY-MM-DD HH:MM"
  - profile_url: str
  - candidate_name: str
  - candidate_headline: str
  - connection_note: str                # AI-drafted note (≤300 chars)
  - approved_by: ""
  - approved_at: ""
```

**Guarantees**:
- Cloud handler MUST move the source task to `Plans/` after writing approval
- Cloud handler MUST log `linkedin_{type}_draft_created` to audit log
- `connection_note` MUST be ≤ 300 characters (LinkedIn hard limit)
- Draft MUST NOT contain any of the banned generic phrases:
  `["Great post!", "So true!", "Totally agree!", "Love this!", "Amazing!"]`

---

## Contract 3: Local Agent → LinkedIn (Execution)

**Producer**: `platinum-local-agent` (via local handlers)
**Consumer**: LinkedIn Web (via Playwright)

### Reply Execution
```
Input:  claimed approval file with reply_body + post_url
Action: Navigate to post_url → find comment by commenter_name → click Reply → type reply_body → submit
Output: audit log entry with result=success/error, post_url, commenter_name
```

### Comment Execution
```
Input:  claimed approval file with comment_body + post_url
Action: Navigate to post_url → click comment field → type comment_body → submit
Output: audit log entry with result=success/error, post_url, post_author
```

### Connect Execution
```
Input:  claimed approval file with connection_note + profile_url
Action: Navigate to profile_url → click Connect → click Add a note → type connection_note → Send
Output: audit log entry with result=success/error, profile_url, candidate_name
```

**Guarantees**:
- Local handler MUST acquire session lock before launching browser
- Local handler MUST check rate limit BEFORE claiming the file
- Local handler MUST use randomised delay 3–8s between major interactions
- Local handler MUST detect login redirect and abort without executing
- Local handler MUST detect security challenge page and set `account_paused: true`
- On success: file moves to `Done/`, rate limit counter incremented
- On failure: file moves to `Rejected/` with error note in frontmatter

---

## Contract 4: Rate Limit State File

**Path**: `AI_Employee_Vault/Logs/linkedin_rate_state.json`
**Readers**: all local LinkedIn handlers (before execution)
**Writers**: all local LinkedIn handlers (after execution), watcher (on security pause)

```json
{
  "date": "YYYY-MM-DD",
  "comments_today": 0,
  "connections_today": 0,
  "comment_limit": 10,
  "connection_limit": 5,
  "account_paused": false,
  "pause_reason": "",
  "last_action_at": "ISO-8601"
}
```

**Read contract**: Any process reading this file MUST handle `FileNotFoundError` by treating all counters as 0 and creating the file with defaults.

**Write contract**: Any process writing this file MUST use atomic write (write to `.tmp` then rename) to avoid corruption during concurrent access.

---

## Contract 5: Session Lock File

**Path**: `linkedin_session/browser.lock`
**Protocol**:
1. Try to read existing lock → check if PID in file is alive (`os.kill(pid, 0)`)
2. If alive: wait up to 60s (poll every 5s)
3. If dead or no file: write `{"pid": os.getpid(), "holder": "process-name", "acquired_at": "ISO-8601"}`
4. On release: delete file in `finally` block

**Timeout behaviour**: After 60s wait, force-delete stale lock and acquire. Log warning.
