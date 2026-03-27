# Research: LinkedIn Advanced Engagement

**Feature**: 005-linkedin-engagement
**Date**: 2026-03-26
**Status**: Complete — all unknowns resolved

---

## Decision 1: LinkedIn Watcher Architecture

**Decision**: Single `silver-linkedin-watcher.py` process handles all three perception tasks (notifications polling, feed scanning, people search) in a sequential loop — not three separate processes.

**Rationale**: The LinkedIn session (`linkedin_session/` Playwright persistent context) cannot be shared across concurrent processes — only one `launch_persistent_context` can hold the lock on the user data directory at a time. A single watcher serialises all perception tasks naturally and eliminates the session conflict problem entirely.

**Alternatives considered**:
- Three separate PM2 processes: Rejected — concurrent `launch_persistent_context` on same dir causes `EPERM` / lock errors, confirmed by WhatsApp watcher experience.
- Single process + async: Rejected — Playwright sync API is used throughout the codebase; mixing async would require a larger refactor.

---

## Decision 2: Session Lock Between Watcher and Existing Poster

**Decision**: The new watcher and the existing `LinkedInManager.post_update()` both need the browser session. Use a **file-based mutex** (`linkedin_session/browser.lock`) with a 60-second timeout. The watcher acquires the lock at the start of each poll cycle and releases it when done. The local agent's social handler tries to acquire the lock before calling `LinkedInManager`.

**Rationale**: Both processes are Python, file-based locking (`fcntl`/`msvcrt`) works cross-process on Windows and Linux, no Redis or IPC needed. Timeout prevents permanent deadlock if a process crashes mid-session.

**Alternatives considered**:
- Serialise via outbox (watcher polls, poster queues to outbox): Rejected — adds latency and complexity; the existing poster already works well direct.
- Single mega-process combining posting + engagement watcher: Rejected — violates single-responsibility and makes PM2 restart scope too broad.

---

## Decision 3: Notification Polling Strategy for Own-Post Comments

**Decision**: Poll `https://www.linkedin.com/notifications/` page. Extract notification items matching "commented on your post". Extract commenter name, comment snippet, and post URL from the notification DOM using JS evaluate with multi-selector fallback.

**Rationale**: LinkedIn does not expose a public API for notifications. The notifications page is the most reliable DOM surface — it is stable, LinkedIn-maintained, and purpose-built for this data. Activity page (`/in/me/recent-activity/`) is an alternative but requires more scrolling and has less structured DOM.

**Alternatives considered**:
- LinkedIn API (official): Rejected — requires OAuth app review and Marketing Developer Platform access; not available to personal accounts.
- Scraping own post pages directly: Rejected — requires knowing post URLs in advance; notifications page has them ready.

---

## Decision 4: Feed Scanning for AI Posts

**Decision**: Navigate to `https://www.linkedin.com/feed/` and use `page.evaluate()` to extract visible post cards. Filter by keyword match against configurable list stored in `.env` (`LINKEDIN_KEYWORDS`). Capture post URL, author name, and first 300 chars of post text. Process max 5 posts per watcher cycle to avoid long session locks.

**Rationale**: Feed page is the canonical discovery surface. JS evaluate is resilient to class name changes (proven by WhatsApp watcher). Capping at 5 posts/cycle prevents the watcher from holding the browser lock for too long and blocking post publishing.

**Alternatives considered**:
- LinkedIn Search for posts: Less reliable DOM, often redirects to login for search results.
- Hashtag pages (`/feed/hashtag/aiagents`): Good secondary source — can be added as Phase 2 enhancement.

---

## Decision 5: People Search for Auto-Connect

**Decision**: Navigate to `https://www.linkedin.com/search/results/people/?keywords=AI+agent+founder&network=%5B%22S%22%5D` (2nd-degree connections filter). Extract profile cards via JS evaluate: name, headline, profile URL. Limit to 3 candidates per watcher cycle.

**Rationale**: URL-parameter-based search is stable across LinkedIn UI updates. `network=S` (2nd degree) targets warm connections who are more likely to accept. JS evaluate avoids brittle CSS selector dependencies.

**Alternatives considered**:
- Sales Navigator: Requires paid subscription.
- LinkedIn API People Search: Restricted to approved partners.
- 1st-degree filter: Too narrow — user already knows these people.

---

## Decision 6: Rate Limit State File

**Decision**: Persist rate limit counters to `AI_Employee_Vault/Logs/linkedin_rate_state.json`:
```json
{
  "date": "2026-03-26",
  "comments_today": 0,
  "connections_today": 0,
  "account_paused": false,
  "pause_reason": ""
}
```
Reset `comments_today` and `connections_today` to 0 when `date` differs from today. `account_paused` is set to `true` on security challenge detection and only cleared by manual edit.

**Rationale**: JSON file is readable in Obsidian, auditable, and writable from any Python process. No database dependency needed. Manual clear of `account_paused` is intentional safety gate — requires human to investigate before resuming.

---

## Decision 7: Deduplication Strategy

**Decision**: Three flat text files in repo root (same pattern as `processed_emails.txt`):
- `processed_linkedin_comments.txt` — notification IDs of comments already tasked
- `processed_linkedin_posts.txt` — post URLs already tasked for commenting
- `processed_linkedin_profiles.txt` — profile URLs already sent connection requests

Each line is one identifier. Loaded into a set on watcher startup, checked O(1) per item, appended on new task creation.

**Rationale**: Proven pattern already used for Gmail and WhatsApp watchers. Simple, reliable, no external dependencies.

---

## Decision 8: Cloud Agent Handler Routing

**Decision**: Extend the existing `cloud_agent.py` task type router with three new type handlers:
- `type: linkedin_reply` → `cloud_linkedin_reply_handler.handle()`
- `type: linkedin_comment` → `cloud_linkedin_comment_handler.handle()`
- `type: linkedin_connect` → `cloud_linkedin_connect_handler.handle()`

Each handler reads the task frontmatter, calls OpenAI to draft content, writes the approval file to `Pending_Approval/`, and moves the task to `Plans/`.

**Rationale**: Follows exact same pattern as `cloud_email_handler` and `cloud_social_handler`. Zero new infrastructure needed — existing cloud agent loop already polls `Needs_Action/` every 10 seconds.

---

## Decision 9: Local Agent Handler Routing

**Decision**: Extend `local_agent.py` approval file router with three new type handlers:
- `type: linkedin_reply_approval` → `local_linkedin_reply_handler.execute()`
- `type: linkedin_comment_approval` → `local_linkedin_comment_handler.execute()`
- `type: linkedin_connect_approval` → `local_linkedin_connect_handler.execute()`

All three follow the claim-before-execute pattern (move to `In_Progress/local/` first).

**Rationale**: Same pattern as `local_email_handler` and `local_social_handler`. Rate limit check happens at the start of `execute()` before claiming — if limit exceeded, file stays in `Approved/` for the next day.

---

## Decision 10: Human-Like Behaviour Pattern

**Decision**: Every browser interaction within a LinkedIn session follows this sequence:
1. Wait for page load (`networkidle` with 30s timeout, fallback to `domcontentloaded`)
2. Scroll the target element into view before clicking
3. Sleep random 3–8 seconds between major actions
4. Type text character-by-character with `page.type()` (not `fill()`) at ~80 WPM equivalent
5. Sleep 1–2 seconds before final submit action

**Rationale**: LinkedIn's bot detection watches for instantaneous interactions, identical timing patterns, and missing scroll events. These mitigations are the industry-standard minimum for Playwright automation on LinkedIn. No guarantee of 100% evasion but significantly reduces detection risk.
