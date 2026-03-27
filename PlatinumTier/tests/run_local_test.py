"""
Automated local integration test for the Platinum tier.
Runs both agents in-process (not as separate OS processes) to verify the full
email flow end-to-end without real credentials.

Usage:
    ENV_FILE=.env.test python -m PlatinumTier.tests.run_local_test

What it tests:
    1. Vault structure bootstrapped correctly
    2. Cloud Agent claims and processes an email task
    3. Approval file appears in Pending_Approval/
    4. Simulated human approval (moves file to Approved/)
    5. Local Agent executes the approval (DRY_RUN)
    6. Task reaches Done/
    7. Audit log written
    8. Health files written by both agents
    9. Stale task recovery (reap task with old claimed_at)
"""
import os
import sys
import time
import shutil
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE", ".env.test"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TEST] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("test")

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./test_vault")).resolve()
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((status, name))
    msg = f"  {status}  {name}"
    if detail:
        msg += f"  ({detail})"
    log.info(msg)
    return condition


def _force_remove(path: Path):
    """Remove read-only files on Windows."""
    import stat
    def _on_error(func, fpath, _exc):
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)
    shutil.rmtree(path, onerror=_on_error)


def setup_vault():
    """Fresh test vault each run."""
    if VAULT_PATH.exists():
        _force_remove(VAULT_PATH)
    import subprocess
    from PlatinumTier.tests.setup_test_vault import setup
    os.environ["VAULT_PATH"] = str(VAULT_PATH)
    setup()


# ---------------------------------------------------------------------------
# Test 1: Vault structure
# ---------------------------------------------------------------------------
def test_vault_structure():
    log.info("\n=== Test 1: Vault Structure ===")
    from PlatinumTier.scripts.task_manager import ensure_vault_structure
    ensure_vault_structure(VAULT_PATH)

    required = [
        "Needs_Action", "In_Progress/cloud", "In_Progress/local",
        "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs",
    ]
    for folder in required:
        check(f"folder exists: {folder}", (VAULT_PATH / folder).is_dir())


# ---------------------------------------------------------------------------
# Test 2: Cloud Agent email flow
# ---------------------------------------------------------------------------
def test_cloud_email_flow():
    log.info("\n=== Test 2: Cloud Agent — Email Draft ===")
    from PlatinumTier.tests.drop_task import drop_email
    task_path = drop_email()
    check("email task dropped in Needs_Action/", task_path.exists())

    from PlatinumTier.scripts.task_manager import claim_task, read_frontmatter
    claimed = claim_task(task_path, "cloud", VAULT_PATH)
    check("cloud claimed the task", claimed)

    in_progress = VAULT_PATH / "In_Progress" / "cloud" / task_path.name
    check("task moved to In_Progress/cloud/", in_progress.exists())
    fm = read_frontmatter(in_progress)
    check("claimed_by=cloud in frontmatter", fm.get("claimed_by") == "cloud")
    check("claimed_at set", bool(fm.get("claimed_at")))

    from PlatinumTier.scripts.handlers.cloud_email_handler import handle
    from openai import OpenAI
    client = OpenAI(api_key="sk-dry-run-stub")
    success = handle(in_progress, VAULT_PATH, client)
    check("cloud_email_handler returned True", success)

    approvals = list((VAULT_PATH / "Pending_Approval").glob("APPROVE_REPLY_EMAIL_*.md"))
    check("approval file created in Pending_Approval/", len(approvals) == 1,
          detail=approvals[0].name if approvals else "none")

    if approvals:
        fm = read_frontmatter(approvals[0])
        check("approval type=email_approval", fm.get("type") == "email_approval")
        check("approval has recipient", bool(fm.get("recipient")))
        check("approval has expires", bool(fm.get("expires")))
        check("approval has message_body", bool(fm.get("message_body")))
        return approvals[0]
    return None


# ---------------------------------------------------------------------------
# Test 3: Local Agent approval execution
# ---------------------------------------------------------------------------
def test_local_approval_flow(approval_path: Path):
    log.info("\n=== Test 3: Local Agent — Email Approval Execution ===")
    if approval_path is None:
        check("approval path available", False, detail="skipped — no approval from Test 2")
        return

    # Simulate human: move approval to Approved/
    approved_path = VAULT_PATH / "Approved" / approval_path.name
    shutil.move(str(approval_path), str(approved_path))
    check("approval moved to Approved/ (simulated human)", approved_path.exists())

    from PlatinumTier.scripts.handlers.local_email_handler import execute
    success = execute(approved_path, VAULT_PATH, gmail_service=None)
    check("local_email_handler returned True", success)

    done_files = list((VAULT_PATH / "Done").glob("APPROVE_REPLY_EMAIL_*.md"))
    check("approval file moved to Done/", len(done_files) >= 1)


# ---------------------------------------------------------------------------
# Test 4: Social post flow
# ---------------------------------------------------------------------------
def test_social_flow():
    log.info("\n=== Test 4: Cloud Agent — Social Post Draft ===")
    from PlatinumTier.tests.drop_task import drop_social
    task_path = drop_social()

    from PlatinumTier.scripts.task_manager import claim_task
    claim_task(task_path, "cloud", VAULT_PATH)
    in_progress = VAULT_PATH / "In_Progress" / "cloud" / task_path.name

    from PlatinumTier.scripts.handlers.cloud_social_handler import handle
    from openai import OpenAI
    success = handle(in_progress, VAULT_PATH, OpenAI(api_key="sk-dry-run-stub"))
    check("cloud_social_handler returned True", success)

    approvals = list((VAULT_PATH / "Pending_Approval").glob("APPROVE_POST_LINKEDIN_*.md"))
    check("LinkedIn approval file created", len(approvals) >= 1)

    if approvals:
        from PlatinumTier.scripts.task_manager import read_frontmatter
        fm = read_frontmatter(approvals[0])
        check("approval has post_content", bool(fm.get("post_content")))
        check("approval target=linkedin", fm.get("target") == "linkedin")

        # Approve it
        approved_path = VAULT_PATH / "Approved" / approvals[0].name
        shutil.move(str(approvals[0]), str(approved_path))
        from PlatinumTier.scripts.handlers.local_social_handler import execute
        success = execute(approved_path, VAULT_PATH)
        check("local_social_handler executed (DRY_RUN)", success)


# ---------------------------------------------------------------------------
# Test 5: Stale recovery
# ---------------------------------------------------------------------------
def test_stale_recovery():
    log.info("\n=== Test 5: Stale Task Recovery ===")
    from PlatinumTier.tests.drop_task import drop_stale
    stale_path = drop_stale()
    check("stale task placed in In_Progress/cloud/", stale_path.exists())

    from PlatinumTier.scripts.stale_reaper import reap_stale
    recovered = reap_stale(VAULT_PATH, timeout_minutes=2)
    check("stale_reaper recovered 1 task", recovered == 1, detail=f"recovered={recovered}")

    recovered_tasks = list((VAULT_PATH / "Needs_Action").glob("EMAIL_stale_*.md"))
    check("stale task returned to Needs_Action/", len(recovered_tasks) >= 1)

    if recovered_tasks:
        from PlatinumTier.scripts.task_manager import read_frontmatter
        fm = read_frontmatter(recovered_tasks[0])
        check("stale_recovery_count=1", fm.get("stale_recovery_count") == 1)
        check("status=stale_recovered", fm.get("status") == "stale_recovered")


# ---------------------------------------------------------------------------
# Test 6: Audit log
# ---------------------------------------------------------------------------
def test_audit_log():
    log.info("\n=== Test 6: Audit Log ===")
    today = datetime.now(timezone.utc).date()
    log_file = VAULT_PATH / "Logs" / f"{today}.json"
    check("audit log file exists", log_file.exists())

    if log_file.exists():
        lines = [l.strip() for l in log_file.read_text().splitlines() if l.strip()]
        check("audit log has entries", len(lines) > 0, detail=f"{len(lines)} entries")
        import json
        for line in lines[:3]:
            try:
                entry = json.loads(line)
                required_fields = {"timestamp", "action_type", "actor", "target"}
                check(f"log entry has required fields", required_fields.issubset(entry.keys()))
                break
            except json.JSONDecodeError:
                check("audit log entry is valid JSON", False)


# ---------------------------------------------------------------------------
# Test 7: Health files
# ---------------------------------------------------------------------------
def test_health_files():
    log.info("\n=== Test 7: Health Files ===")
    from PlatinumTier.scripts.health_writer import write_health
    write_health(VAULT_PATH, "cloud", status="running", last_task="test")
    write_health(VAULT_PATH, "local", status="running", last_task="test")

    for agent in ("cloud", "local"):
        hf = VAULT_PATH / "Logs" / f"health_{agent}.json"
        check(f"health_{agent}.json exists", hf.exists())
        if hf.exists():
            import json
            data = json.loads(hf.read_text())
            check(f"health_{agent} has pid", "pid" in data)
            check(f"health_{agent} status=running", data.get("status") == "running")


# ---------------------------------------------------------------------------
# Test 8: Expiry rejection
# ---------------------------------------------------------------------------
def test_expiry_rejection():
    log.info("\n=== Test 8: Expired Approval Rejection ===")
    import yaml
    # Write an expired approval file
    expired_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    fm = {
        "type": "email_approval",
        "status": "pending_approval",
        "created_at": expired_ts,
        "expires": expired_ts,
        "claimed_by": "cloud",
        "approved_by": "",
        "approved_at": "",
        "recipient": "test@example.com",
        "subject": "Expired Test",
        "message_body": "This should not be sent.",
    }
    name = f"APPROVE_REPLY_EMAIL_expired_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    approved_dir = VAULT_PATH / "Approved"
    approved_dir.mkdir(exist_ok=True)
    approval_path = approved_dir / name
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    approval_path.write_text(f"---\n{header}---\n\nExpired draft.\n")

    from PlatinumTier.scripts.handlers.local_email_handler import execute
    from PlatinumTier.scripts.exceptions import ApprovalExpiredError
    try:
        execute(approval_path, VAULT_PATH, gmail_service=None)
        check("expired approval raises ApprovalExpiredError", False, detail="no exception raised")
    except ApprovalExpiredError:
        check("expired approval raises ApprovalExpiredError", True)

    rejected = list((VAULT_PATH / "Rejected").glob(f"*expired*.md"))
    check("expired approval moved to Rejected/", len(rejected) >= 1)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("PLATINUM TIER — LOCAL INTEGRATION TEST")
    log.info(f"Vault: {VAULT_PATH}")
    log.info(f"DRY_RUN: {os.getenv('DRY_RUN')}")
    log.info("=" * 60)

    setup_vault()
    test_vault_structure()
    approval = test_cloud_email_flow()
    test_local_approval_flow(approval)
    test_social_flow()
    test_stale_recovery()
    test_audit_log()
    test_health_files()
    test_expiry_rejection()

    # Summary
    passed = sum(1 for s, _ in results if s == PASS)
    failed = sum(1 for s, _ in results if s == FAIL)
    log.info("\n" + "=" * 60)
    log.info(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} checks")
    log.info("=" * 60)

    if failed:
        for status, name in results:
            if status == FAIL:
                log.info(f"  FAILED: {name}")
        sys.exit(1)
    else:
        log.info("All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
