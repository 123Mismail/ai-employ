# Tasks: LinkedIn Advanced Engagement

**Input**: Design documents from `specs/005-linkedin-engagement/`
**Branch**: `005-linkedin-engagement`
**Prerequisites**: plan.md ✓ | spec.md ✓ | research.md ✓ | data-model.md ✓ | contracts/file-contracts.md ✓

**Organization**: Tasks grouped by user story — each phase is independently testable and deliverable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: User story this task belongs to (US1/US2/US3)
- All paths relative to `B:/hackathone0-ai-employee/ai-employ/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment config and deduplication registries — no code yet, just wiring.

- [x] T001 Add LinkedIn engagement env vars to `.env`: `LINKEDIN_KEYWORDS`, `LINKEDIN_CONNECT_KEYWORDS`, `LINKEDIN_POLL_INTERVAL=120`, `LINKEDIN_COMMENT_LIMIT=10`, `LINKEDIN_CONNECTION_LIMIT=5`
- [x] T002 [P] Create empty deduplication registry files in repo root: `processed_linkedin_comments.txt`, `processed_linkedin_posts.txt`, `processed_linkedin_profiles.txt`
- [x] T003 [P] Create `AI_Employee_Vault/Logs/linkedin_rate_state.json` with default values: `{"date":"","comments_today":0,"connections_today":0,"comment_limit":10,"connection_limit":5,"account_paused":false,"pause_reason":"","last_action_at":""}`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `linkedin_rate_limiter.py` shared utility must exist before ANY handler or watcher can be built. All later phases depend on it.

**⚠️ CRITICAL**: Complete all tasks in this phase before moving to Phase 3.

- [x] T004 Create `PlatinumTier/scripts/linkedin_rate_limiter.py` with `RateLimitState` dataclass: fields `date`, `comments_today`, `connections_today`, `comment_limit`, `connection_limit`, `account_paused`, `pause_reason`, `last_action_at` — with `load()` classmethod reading `AI_Employee_Vault/Logs/linkedin_rate_state.json` (create with defaults if missing), `save()` atomically writing via `.tmp` rename, and `reset_if_new_day()` setting counters to 0 when `date != today`
- [x] T005 Add `RateLimiter` class to `PlatinumTier/scripts/linkedin_rate_limiter.py`: methods `can_execute(action_type: str) -> bool` (checks `account_paused`, resets if new day, checks counter vs limit), `record_action(action_type: str)` (increments counter, updates `last_action_at`, saves), `pause_account(reason: str)` (sets `account_paused=True`, saves, logs CRITICAL) — `action_type` values: `"comment"`, `"connect"` (replies are unlimited)
- [x] T006 Add `SessionLock` class to `PlatinumTier/scripts/linkedin_rate_limiter.py`: context manager with `acquire(timeout=60)` writing `linkedin_session/browser.lock` as JSON with current PID, holder name, acquired_at — checking existing lock PID liveness via `os.kill(pid, 0)`, waiting up to `timeout` seconds polling every 5s, force-acquiring on timeout or dead PID — `release()` deletes lock file in `finally`
- [x] T007 [P] Add `get_vault_path() -> Path` helper to `PlatinumTier/scripts/linkedin_rate_limiter.py` returning `REPO_ROOT / "AI_Employee_Vault"` — used by all handlers to locate rate state file without circular imports

**Checkpoint**: `linkedin_rate_limiter.py` complete — import it in a Python shell and verify `RateLimiter`, `SessionLock` classes are importable with no errors.

---

## Phase 3: User Story 1 — Reply to Comments on Own Posts (Priority: P1) 🎯 MVP

**Goal**: Detect new comments on own posts → cloud drafts reply → human approves → local agent replies on LinkedIn.

**Independent Test**: Post a comment on your own LinkedIn post from another account. Within 2 minutes a `LINKEDIN_REPLY_*.md` appears in `Needs_Action/`. Cloud agent drafts `APPROVE_REPLY_LINKEDIN_*.md` in `Pending_Approval/`. Drag to `Approved/` → reply appears on the LinkedIn post.

### Watcher (Perception)

- [x] T008 [US1] Create `SilverTier/scripts/watchers/linkedin.py` with `REPO_ROOT` detection and `sys.path.insert(0, str(REPO_ROOT))` before all project imports — class `LinkedInEngagementWatcher` with `__init__` loading env vars (`LINKEDIN_POLL_INTERVAL`, deduplication file paths), `load_processed_ids(filepath)` returning a `set`, `save_processed_id(filepath, id)` appending to file
- [x] T009 [US1] Add `_acquire_session_lock()` and `_release_session_lock()` wrappers to `LinkedInEngagementWatcher` using `SessionLock` from `linkedin_rate_limiter.py` — watcher skips entire poll cycle (logs WARNING) if lock cannot be acquired within 60s
- [x] T010 [US1] Add `_check_security_challenge(page)` method to `LinkedInEngagementWatcher`: uses `page.evaluate()` to check if current URL contains `checkpoint`, `challenge`, or `authwall` — if detected, calls `RateLimiter.pause_account("security_challenge_detected")` and raises exception to abort cycle
- [x] T011 [US1] Add `_poll_notifications(page)` method to `LinkedInEngagementWatcher`: navigates to `https://www.linkedin.com/notifications/` using `page.goto()`, waits for load, calls `_check_security_challenge()`, then uses `page.evaluate()` with 3-selector JS fallback strategy to extract notification items where text contains "commented on your post" — returns list of dicts with `notification_id`, `commenter_name`, `comment_snippet`, `post_url`
- [x] T012 [US1] Add `_create_reply_task(notification)` method to `LinkedInEngagementWatcher`: skips if `notification_id` in `processed_linkedin_comments` set, writes `Needs_Action/LINKEDIN_REPLY_{notification_id}_{ts}.md` with full YAML frontmatter per data-model contract, calls `save_processed_id()`, logs `INFO "Created reply task for: {commenter_name}"`
- [x] T013 [US1] Add `run()` loop to `LinkedInEngagementWatcher`: launches `playwright.sync_api` with `launch_persistent_context(linkedin_session_path, headless=False, user_agent=...)`, acquires session lock, calls `_poll_notifications()`, creates tasks, releases lock in `finally`, sleeps `LINKEDIN_POLL_INTERVAL` seconds — detects login redirect (URL contains `linkedin.com/login`) and logs ERROR without crashing

### Cloud Handler (Reasoning)

- [x] T014 [US1] Create `PlatinumTier/scripts/handlers/cloud_linkedin_reply_handler.py`: `handle(task_path, vault_path, openai_client) -> bool` reading frontmatter fields `commenter_name`, `comment_snippet`, `post_url` — raises `ValueError` if any missing
- [x] T015 [US1] Add `_draft_reply(openai_client, commenter_name, comment_snippet, goals_context) -> str` to `cloud_linkedin_reply_handler.py`: reads `AI_Employee_Vault/Business_Goals.md` for brand context, builds prompt instructing model to reply to `commenter_name`'s comment (`comment_snippet`) in brand voice — `max_tokens=200`, `temperature=0.7`, `DRY_RUN` guard returning placeholder text
- [x] T016 [US1] Add approval file writer to `cloud_linkedin_reply_handler.py`: creates `Pending_Approval/APPROVE_REPLY_LINKEDIN_{notification_id}_{ts}.md` with YAML frontmatter per contract (type=`linkedin_reply_approval`, expires 24h, commenter_name, post_url, reply_body), moves task to `Plans/`, logs `email_draft_created`-style audit entry as `linkedin_reply_draft_created`

### Route Wiring — Cloud

- [x] T017 [US1] Add `linkedin_reply` task type route to `PlatinumTier/scripts/cloud_agent.py`: import `cloud_linkedin_reply_handler`, add `elif task_type == "linkedin_reply": return cloud_linkedin_reply_handler.handle(task_path, vault_path, openai_client)` in the task type dispatch block

### Local Handler (Action)

- [x] T018 [US1] Create `PlatinumTier/scripts/handlers/local_linkedin_reply_handler.py`: `execute(approval_path, vault_path) -> bool` reading frontmatter `post_url`, `commenter_name`, `reply_body` — check `RateLimiter().is_paused()` (return False if paused), claim file to `In_Progress/local/`
- [x] T019 [US1] Add `_post_reply(page, post_url, commenter_name, reply_body)` to `local_linkedin_reply_handler.py`: navigate to `post_url`, wait for load + `_check_security_challenge()`, use `page.evaluate()` to find the comment by `commenter_name`, click Reply button, sleep random 3–8s, use `page.type()` character-by-character for `reply_body`, sleep 1–2s, click submit — return `True` on success
- [x] T020 [US1] Complete `local_linkedin_reply_handler.execute()`: acquire `SessionLock`, call `_post_reply()` inside try/finally releasing lock, on success update frontmatter + `move_task(claimed_path, vault_path/"Done")` + `log_action(..., "linkedin_reply_sent", ...)`, on failure `move_task(claimed_path, vault_path/"Rejected")` + `log_action(..., result="error")`

### Route Wiring — Local

- [x] T021 [US1] Add `linkedin_reply_approval` type route to `PlatinumTier/scripts/local_agent.py`: import `local_linkedin_reply_handler`, add dispatch for `type == "linkedin_reply_approval"` calling `local_linkedin_reply_handler.execute(approval_path, vault_path)`

### PM2 Registration

- [x] T022 [US1] Add `silver-linkedin-watcher` entry to `ecosystem.config.js`: `script: "SilverTier/scripts/watchers/linkedin.py"`, `interpreter: "uv run python"`, `env: { DRY_RUN: "false" }`, `restart_delay: 10000`, `max_restarts: 10`

**Phase 3 done when**: Drop a comment on your LinkedIn post → `LINKEDIN_REPLY_*.md` appears → approve → reply posts. Audit log shows `linkedin_reply_sent result=success`.

---

## Phase 4: User Story 2 — Comment on Others' AI Posts (Priority: P2)

**Goal**: Scan LinkedIn feed for AI-related posts → cloud drafts comment → human approves → local agent comments.

**Independent Test**: Run `pm2 logs silver-linkedin-watcher` — verify `LINKEDIN_COMMENT_*.md` files appear in `Needs_Action/` for AI-keyword posts. Approve one → comment appears on the LinkedIn post. `linkedin_rate_state.json` shows `comments_today` incremented.

### Watcher Extension

- [x] T023 [US2] Add `_scan_feed(page)` method to `LinkedInEngagementWatcher` in `SilverTier/scripts/watchers/linkedin.py`: navigate to `https://www.linkedin.com/feed/`, wait for load + security check, use `page.evaluate()` with multi-selector JS fallback to extract up to 5 post cards (post_url, author name + headline, first 300 chars of post text) — filter by keyword match against `LINKEDIN_KEYWORDS` env var (split on comma)
- [x] T024 [US2] Add `_create_comment_task(post)` method to `LinkedInEngagementWatcher`: skip if `post_url` in `processed_linkedin_posts` set OR if `RateLimiter().comments_today >= comment_limit`, write `Needs_Action/LINKEDIN_COMMENT_{post_id}_{ts}.md` per contract, call `save_processed_id(processed_linkedin_posts_file, post_url)`, log INFO
- [x] T025 [US2] Extend `run()` loop in `LinkedInEngagementWatcher`: after `_poll_notifications()`, call `_scan_feed()` then `_create_comment_task()` for each result — all within the same session lock acquisition

### Cloud Handler

- [x] T026 [P] [US2] Create `PlatinumTier/scripts/handlers/cloud_linkedin_comment_handler.py`: `handle(task_path, vault_path, openai_client) -> bool` reading `post_author`, `post_snippet`, `post_url` from frontmatter
- [x] T027 [US2] Add `_draft_comment(openai_client, post_author, post_snippet, goals_context) -> str` to `cloud_linkedin_comment_handler.py`: prompt explicitly includes post text, instructs model to write a specific insightful comment, includes banned-phrase list `["Great post!", "So true!", "Love this!", "Amazing!", "Totally agree!"]` in prompt, `max_tokens=150`, `temperature=0.75`
- [x] T028 [US2] Add approval file writer to `cloud_linkedin_comment_handler.py`: creates `APPROVE_COMMENT_LINKEDIN_{post_id}_{ts}.md` per contract, moves task to `Plans/`, logs `linkedin_comment_draft_created` audit entry

### Route Wiring — Cloud

- [x] T029 [US2] Add `linkedin_comment` route to `PlatinumTier/scripts/cloud_agent.py` dispatch block importing and calling `cloud_linkedin_comment_handler.handle()`

### Local Handler

- [x] T030 [P] [US2] Create `PlatinumTier/scripts/handlers/local_linkedin_comment_handler.py`: `execute(approval_path, vault_path) -> bool` — check `RateLimiter().can_execute("comment")` (return False + log if limit hit, leaving file in `Approved/` for next day), claim file, acquire `SessionLock`
- [x] T031 [US2] Add `_post_comment(page, post_url, comment_body)` to `local_linkedin_comment_handler.py`: navigate to `post_url`, security check, use `page.evaluate()` to locate comment input field, click it, sleep 3–8s, `page.type()` the comment body, sleep 1–2s, submit — return bool success
- [x] T032 [US2] Complete `local_linkedin_comment_handler.execute()`: call `_post_comment()` in try/finally releasing lock, on success call `RateLimiter().record_action("comment")` + move to `Done/` + audit log `linkedin_comment_posted`, on failure move to `Rejected/` + audit log with error

### Route Wiring — Local

- [x] T033 [US2] Add `linkedin_comment_approval` route to `PlatinumTier/scripts/local_agent.py` dispatch block calling `local_linkedin_comment_handler.execute()`

**Phase 4 done when**: Feed scan creates comment tasks → approve → comment posts → `comments_today` increments → halts at 10.

---

## Phase 5: User Story 3 — Auto-Connect with AI People (Priority: P3)

**Goal**: Search LinkedIn for AI startup/tech people → cloud drafts personalised note → human approves → local agent sends connection request.

**Independent Test**: Run watcher, verify `LINKEDIN_CONNECT_*.md` appears with candidate name/headline/company. Approve → connection request visible in LinkedIn "Sent". `connections_today` increments. Halts at 5 for the day.

### Watcher Extension

- [x] T034 [US3] Add `_search_people(page)` method to `LinkedInEngagementWatcher` in `SilverTier/scripts/watchers/linkedin.py`: navigate to LinkedIn people search URL with `LINKEDIN_CONNECT_KEYWORDS` URL-encoded + `network=%5B%22S%22%5D` (2nd-degree filter), use `page.evaluate()` to extract up to 3 profile cards (name, headline, company, profile_url) — filter: headline must contain at least one AI keyword
- [x] T035 [US3] Add `_create_connect_task(candidate)` method to `LinkedInEngagementWatcher`: skip if `profile_url` in `processed_linkedin_profiles` set OR if `RateLimiter().connections_today >= connection_limit`, write `Needs_Action/LINKEDIN_CONNECT_{profile_id}_{ts}.md` per contract, `save_processed_id()`, log INFO
- [x] T036 [US3] Extend `run()` loop: after feed scan, call `_search_people()` then `_create_connect_task()` for each result — still within same session lock

### Cloud Handler

- [x] T037 [P] [US3] Create `PlatinumTier/scripts/handlers/cloud_linkedin_connect_handler.py`: `handle(task_path, vault_path, openai_client) -> bool` reading `candidate_name`, `candidate_headline`, `candidate_company`, `profile_url` from frontmatter
- [x] T038 [US3] Add `_draft_connection_note(openai_client, candidate_name, candidate_headline, candidate_company, goals_context) -> str` to `cloud_linkedin_connect_handler.py`: prompt instructs model to write a personalised note referencing candidate's specific role/company, `max_tokens=80`, `temperature=0.6` — validate output length ≤ 300 chars (LinkedIn hard limit), truncate at last sentence boundary if needed
- [x] T039 [US3] Add approval file writer to `cloud_linkedin_connect_handler.py`: creates `APPROVE_CONNECT_LINKEDIN_{profile_id}_{ts}.md` per contract with `connection_note` field, moves task to `Plans/`, logs `linkedin_connect_draft_created`

### Route Wiring — Cloud

- [x] T040 [US3] Add `linkedin_connect` route to `PlatinumTier/scripts/cloud_agent.py` dispatch block importing and calling `cloud_linkedin_connect_handler.handle()`

### Local Handler

- [x] T041 [P] [US3] Create `PlatinumTier/scripts/handlers/local_linkedin_connect_handler.py`: `execute(approval_path, vault_path) -> bool` — check `RateLimiter().can_execute("connect")` (return False + log if daily limit reached, leaving file in `Approved/`), claim file, acquire `SessionLock`
- [x] T042 [US3] Add `_send_connection_request(page, profile_url, connection_note)` to `local_linkedin_connect_handler.py`: navigate to `profile_url`, security check, sleep 30s (minimum wait for connect actions per spec FR-005), use `page.evaluate()` with fallback selectors to click Connect button → "Add a note" → type `connection_note` via `page.type()` → Send — return bool success
- [x] T043 [US3] Complete `local_linkedin_connect_handler.execute()`: call `_send_connection_request()` in try/finally releasing lock, on success call `RateLimiter().record_action("connect")` + move to `Done/` + audit log `linkedin_connect_sent`, on failure move to `Rejected/` + audit log with error

### Route Wiring — Local

- [x] T044 [US3] Add `linkedin_connect_approval` route to `PlatinumTier/scripts/local_agent.py` dispatch block calling `local_linkedin_connect_handler.execute()`

**Phase 5 done when**: People search creates connect tasks → approve → request sent with note → `connections_today` increments → halts at 5.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T045 [P] Add `linkedin_rate_state` fields (`comments_today`, `connections_today`, `account_paused`) to `AI_Employee_Vault/Logs/health_local.json` update logic in `PlatinumTier/scripts/local_agent.py` health check — visible in Obsidian dashboard
- [x] T046 [P] Add `silver-linkedin-watcher` to PM2 save state: run `pm2 save` after confirming watcher starts cleanly, verify `pm2 startup` includes it for auto-start on reboot
- [ ] T047 Verify session lock releases correctly on PM2 restart: run `pm2 restart silver-linkedin-watcher`, confirm `linkedin_session/browser.lock` is deleted (not left stale), confirm next cycle acquires fresh lock
- [ ] T048 [P] Update `AI_Employee_Vault/Dashboard.md` to include LinkedIn engagement section: shows `comments_today`, `connections_today`, `account_paused` status, last 3 engagement actions from audit log
- [ ] T049 End-to-end smoke test all 3 flows in sequence: reply (P1) → comment (P2) → connect (P3). Verify audit log has 3 entries, rate counters are correct, all approval files in `Done/`, no stale lock files.

---

## Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundation: linkedin_rate_limiter.py)
            ├── Phase 3 (US1: Reply) ← MVP — deliver first
            │       └── Phase 4 (US2: Comment) ← depends on watcher from US1
            │               └── Phase 5 (US3: Connect) ← depends on watcher from US2
            └── Phase 6 (Polish) ← after all 3 US complete
```

**Parallel opportunities within phases**:
- Phase 3: T014+T018 can start in parallel after T013 (cloud and local handlers independent)
- Phase 4: T026+T030 can start in parallel after T025
- Phase 5: T037+T041 can start in parallel after T036

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1 only)**
- 22 tasks
- Delivers: reply-to-comments flow end-to-end
- Zero rate-limit risk (replies on own content)
- Validates watcher → cloud → local → LinkedIn pipeline before adding riskier features

**Full delivery order**: Phase 1 → 2 → 3 → 4 → 5 → 6

**Start here**: T001, T002, T003 (can all run in parallel — just file creation)

---

## Summary

| Phase | Tasks | Story | Parallel Tasks |
|---|---|---|---|
| Phase 1: Setup | T001–T003 | — | T002, T003 |
| Phase 2: Foundation | T004–T007 | — | T007 |
| Phase 3: US1 Reply | T008–T022 | US1 | T014+T018 |
| Phase 4: US2 Comment | T023–T033 | US2 | T026+T030 |
| Phase 5: US3 Connect | T034–T044 | US3 | T037+T041 |
| Phase 6: Polish | T045–T049 | — | T045, T046, T048 |
| **Total** | **49 tasks** | | |
