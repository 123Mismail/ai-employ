# Feature Specification: LinkedIn Advanced Engagement

**Feature Branch**: `005-linkedin-engagement`
**Created**: 2026-03-26
**Status**: Draft
**Input**: LinkedIn Advanced Engagement Features — Auto-comment on AI posts, reply to comments on own posts, auto-connect with AI startup and tech people. All features safe, rate-limited, and through existing HITL approval flow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Reply to Comments on Own Posts (Priority: P1)

The AI Employee monitors new comments appearing on the user's own LinkedIn posts. When someone comments, the watcher detects it, the cloud agent drafts a thoughtful, on-brand reply, and an approval file lands in Obsidian. The user drags it to Approved and the local agent posts the reply — growing engagement without the user typing a single word.

**Why this priority**: Replying to comments is the single highest-ROI engagement action on LinkedIn. It boosts reach via the algorithm, builds relationships, and carries zero risk of account restriction since the user is acting on their own content.

**Independent Test**: Drop a comment on one of the user's own posts manually. Verify that within 5 minutes an approval file appears in `Pending_Approval/LINKEDIN_REPLY_*.md`. Approve it and confirm the reply appears under the post.

**Acceptance Scenarios**:

1. **Given** a new comment appears on the user's LinkedIn post, **When** the watcher polls notifications/activity, **Then** a `LINKEDIN_REPLY_*.md` task is created in `Needs_Action/` within one poll cycle.
2. **Given** a `LINKEDIN_REPLY_*.md` task exists, **When** the cloud agent processes it, **Then** an approval file with a brand-aligned reply draft appears in `Pending_Approval/` within 60 seconds.
3. **Given** the approval file is moved to `Approved/`, **When** the local agent executes, **Then** the reply is posted under the correct comment on LinkedIn and the file moves to `Done/`.
4. **Given** the same comment has already been replied to, **When** the watcher polls again, **Then** no duplicate reply task is created.
5. **Given** the LinkedIn session is unavailable, **When** the local agent attempts to post, **Then** the file moves to `Rejected/` with an error note and the account is not flagged.

---

### User Story 2 — Comment on Others' AI Posts (Priority: P2)

The AI Employee scans the LinkedIn feed for posts related to AI agents, LLMs, Digital FTEs, and autonomous systems. For each relevant post it hasn't commented on, it creates a task. The cloud agent drafts a value-adding, non-generic comment tied to the user's brand positioning. After HITL approval the local agent posts it — building the user's visibility in the AI niche.

**Why this priority**: Commenting on others' posts is the primary growth lever for building authority in a niche. Higher risk than replying (outbound action) but high reward. Rate-limiting is critical here.

**Independent Test**: Manually trigger a feed scan. Verify that 1–3 posts matching AI keywords appear as tasks in `Needs_Action/LINKEDIN_COMMENT_*.md`. Approve one and confirm the comment appears on the target post.

**Acceptance Scenarios**:

1. **Given** the watcher scans the LinkedIn feed, **When** it finds posts containing target keywords (AI agents, LLM, autonomous, Digital FTE, Claude, OpenAI), **Then** a `LINKEDIN_COMMENT_*.md` task is created for each unseen relevant post.
2. **Given** a `LINKEDIN_COMMENT_*.md` task exists, **When** the cloud agent processes it, **Then** an approval file with a specific, non-generic, brand-aligned comment appears in `Pending_Approval/`.
3. **Given** the daily comment limit (10 comments/day) has been reached, **When** new comment tasks are created, **Then** the watcher pauses creating new comment tasks until the next day and logs a rate-limit notice.
4. **Given** a post has already been commented on by the user, **When** the watcher detects it again, **Then** no duplicate comment task is created.
5. **Given** the approval file is moved to `Approved/`, **When** the local agent executes, **Then** the comment is posted on the correct post with a human-like delay before submission.

---

### User Story 3 — Auto-Connect with AI Startup & Tech People (Priority: P3)

The AI Employee searches LinkedIn for people with AI-related titles and companies (AI founders, ML engineers, agent builders, LLM researchers) and drafts personalized connection requests referencing the person's specific work. After HITL approval, the local agent sends the request with the note — growing a targeted professional network on autopilot.

**Why this priority**: Highest growth impact for network building but also highest risk — LinkedIn actively restricts accounts sending mass connection requests. Strict rate limits and mandatory personalised notes are non-negotiable. Built last after the safer features are stable.

**Independent Test**: Trigger a people search for "AI agent founder". Verify a `LINKEDIN_CONNECT_*.md` task is created with the candidate's name, title, and company. Approve it and confirm the connection request is sent with the personalised note visible in LinkedIn's "Sent" section.

**Acceptance Scenarios**:

1. **Given** the watcher runs a LinkedIn people search with AI-related keywords, **When** it finds 2nd-degree connections with matching titles/companies, **Then** a `LINKEDIN_CONNECT_*.md` task is created per candidate with name, title, company, and headline captured.
2. **Given** a `LINKEDIN_CONNECT_*.md` task exists, **When** the cloud agent processes it, **Then** an approval file with a short personalised connection note (referencing the candidate's specific work) appears in `Pending_Approval/`.
3. **Given** the daily connection limit (5 requests/day) has been reached, **When** further connection tasks are queued, **Then** no more requests are sent until the next day regardless of approvals in `Approved/`.
4. **Given** a connection request has already been sent to a person, **When** the watcher finds them again, **Then** no duplicate task is created.
5. **Given** the approval file is moved to `Approved/`, **When** the local agent executes, **Then** the request is sent with a minimum 30-second delay after page load, the connection note is included, and the file moves to `Done/`.

---

### Edge Cases

- What happens when LinkedIn's DOM changes and selectors break? → JS evaluate with multi-strategy fallback selectors; watcher logs a warning and skips the cycle rather than crashing.
- What happens if the LinkedIn session cookie expires mid-operation? → Local agent detects login redirect, moves file back to `Pending_Approval/`, and logs a session expiry warning. No action is taken.
- What happens when two processes try to use the LinkedIn browser session at the same time? → A lock file (`linkedin_session/browser.lock`) prevents concurrent access. The second process waits up to 60 seconds then skips its cycle.
- What happens if the user's account gets a LinkedIn "unusual activity" warning? → All LinkedIn processes pause immediately, log a CRITICAL warning, and require manual user restart after resolving the warning.
- What happens when a post or person disappears between task creation and execution? → Local agent catches the navigation error, moves file to `Rejected/` with reason, and does not retry.

## Requirements *(mandatory)*

### Functional Requirements

**Watcher & Perception**

- **FR-001**: The system MUST poll LinkedIn notifications/activity to detect new comments on the user's own posts.
- **FR-002**: The system MUST scan the LinkedIn feed for posts containing configurable AI-related keywords and create one task per unseen relevant post.
- **FR-003**: The system MUST search LinkedIn for people with AI-related job titles and company names and create one connection task per unseen candidate.
- **FR-004**: The system MUST track processed post IDs and connection candidate profile URLs in persistent deduplification files to prevent duplicate tasks.
- **FR-005**: The system MUST use a single shared LinkedIn browser session across all engagement features, protected by a lock file to prevent concurrent access conflicts.

**Rate Limiting & Safety**

- **FR-006**: The system MUST enforce a daily comment limit of no more than 10 comments per day and halt new comment executions when the limit is reached.
- **FR-007**: The system MUST enforce a daily connection request limit of no more than 5 per day and halt new request executions when the limit is reached.
- **FR-008**: The system MUST introduce a randomised human-like delay of 3–8 seconds between UI interactions within a single LinkedIn session.
- **FR-009**: The system MUST maintain daily action counters in a persistent JSON state file, resetting at midnight local time.
- **FR-010**: The system MUST pause all LinkedIn automation and emit a CRITICAL log if it detects a LinkedIn security challenge, CAPTCHA, or "unusual activity" page.

**HITL Approval Flow**

- **FR-011**: Every engagement action (reply, comment, connection request) MUST go through the existing HITL approval flow: `Needs_Action/` → cloud draft → `Pending_Approval/` → human approves → `Approved/` → local agent executes → `Done/`.
- **FR-012**: Approval files MUST expire after 24 hours; expired files MUST be moved to `Rejected/` automatically without being executed.
- **FR-013**: The local agent MUST claim an approval file to `In_Progress/local/` before executing any LinkedIn action, preventing retry storms on failure.

**Content Quality**

- **FR-014**: AI-drafted comments MUST be specific to the post content — no generic phrases ("Great post!", "So true!"). The prompt MUST reference the original post text.
- **FR-015**: AI-drafted connection notes MUST reference the candidate's specific job title or company — no identical boilerplate notes sent to multiple people.
- **FR-016**: All drafted content MUST follow the brand voice and hashtag strategy defined in `AI_Employee_Vault/Business_Goals.md`.

**Audit & Observability**

- **FR-017**: Every executed LinkedIn action MUST be logged to the vault audit log with action type, target (post URL or profile URL), result, and `approved_by: human`.
- **FR-018**: The daily rate-limit state (comments used, connections sent today) MUST be visible in the vault's health dashboard.

### Key Entities

- **LinkedInEngagementTask**: A Markdown task file in `Needs_Action/` — types: `LINKEDIN_REPLY_`, `LINKEDIN_COMMENT_`, `LINKEDIN_CONNECT_`. Contains post/profile URL, author, snippet, and task metadata.
- **EngagementApproval**: A `Pending_Approval/` file with AI-drafted content, target info, expiry timestamp, and HITL status fields.
- **RateLimitState**: A persistent JSON file (`AI_Employee_Vault/Logs/linkedin_rate_state.json`) tracking daily action counts per engagement type, reset time, and account health status.
- **DeduplicationRegistry**: Flat text files (`processed_linkedin_comments.txt`, `processed_linkedin_posts.txt`, `processed_linkedin_profiles.txt`) storing seen IDs to prevent duplicate tasks.
- **SessionLock**: A lock file (`linkedin_session/browser.lock`) preventing concurrent Playwright sessions on the same profile directory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every new comment on the user's own posts results in an approval draft appearing in Obsidian within 5 minutes of the comment being posted.
- **SC-002**: At least 80% of executed engagement actions (comments, replies, connections) succeed without LinkedIn errors or session failures.
- **SC-003**: Zero duplicate tasks are created for the same post, comment, or profile across any number of watcher poll cycles.
- **SC-004**: The daily rate limits (10 comments, 5 connections) are never exceeded regardless of how many approved items are queued in `Approved/`.
- **SC-005**: No LinkedIn session conflict errors occur when the engagement watcher and the existing LinkedIn poster run in the same time window.
- **SC-006**: All AI-drafted comments and connection notes are specific to the target post or person — measurable by zero use of banned generic phrases in any draft.
- **SC-007**: The user's LinkedIn connection count grows by a minimum of 25 targeted AI-niche connections within 30 days of the feature being live.
- **SC-008**: Every executed action appears in the vault audit log within 30 seconds of execution, with full metadata.

## Assumptions

- The user's LinkedIn account is already authenticated via the existing `linkedin_session/` Playwright persistent context — no re-login required.
- LinkedIn's Terms of Service allow personal automation for moderate engagement (not mass spam). Rate limits are set conservatively to stay within safe thresholds.
- The existing `platinum-cloud-agent` and `platinum-local-agent` PM2 processes will handle the new task types without requiring a separate process.
- A new `silver-linkedin-watcher` PM2 process will be created specifically for LinkedIn perception, separate from the existing poster skill.
- The user will monitor the CRITICAL log alerts for LinkedIn security challenges and resolve them manually.
- `Business_Goals.md` in the vault is the single source of truth for brand voice, content pillars, and hashtag strategy for all drafted content.

## Dependencies

- Existing `linkedin_session/` Playwright persistent session (GoldTier)
- `AI_Employee_Vault/Business_Goals.md` for brand voice
- `platinum-cloud-agent` and `platinum-local-agent` PM2 processes
- OpenAI API key (already configured in `.env`)
- Existing HITL task manager (`PlatinumTier/scripts/task_manager.py`)
- Existing audit logger (`PlatinumTier/scripts/audit_log.py`)

## Out of Scope

- Automatically liking or reacting to posts (no approval mechanism, too risky)
- Posting to LinkedIn Groups
- Sending InMail messages (paid feature, different API surface)
- Twitter/X or other social platforms
- Automatic content scheduling without HITL approval
- Analytics or performance reporting dashboard (separate feature)
