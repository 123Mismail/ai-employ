"""
Sets up a local test vault with a git repo (no remote needed).
Run once before starting local tests: python -m PlatinumTier.tests.setup_test_vault
"""
import os
import subprocess
import sys
from pathlib import Path

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./test_vault")).resolve()


def setup():
    print(f"Setting up test vault at: {VAULT_PATH}")
    VAULT_PATH.mkdir(parents=True, exist_ok=True)

    # Init git repo
    if not (VAULT_PATH / ".git").exists():
        subprocess.run(["git", "init"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "config", "user.email", "test@local"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "config", "user.name", "Local Test"], cwd=VAULT_PATH, check=True)
        print("  git init OK")
    else:
        print("  git repo already exists")

    # Create folder structure
    folders = [
        "Needs_Action", "In_Progress/cloud", "In_Progress/local",
        "Plans", "Pending_Approval", "Approved", "Rejected", "Done",
        "Logs", "Briefings", "Inbox/drop_zone",
    ]
    for folder in folders:
        (VAULT_PATH / folder).mkdir(parents=True, exist_ok=True)
        (VAULT_PATH / folder / ".gitkeep").touch()

    # Write .gitattributes
    (VAULT_PATH / ".gitattributes").write_text("*.md merge=union\n*.json merge=ours\n")

    # Write .gitignore
    (VAULT_PATH / ".gitignore").write_text(
        ".env\ntoken.json\ncredentials.json\nwhatsapp_session/\nlinkedin_session/\n"
        "processed_emails.txt\nprocessed_chats.txt\nrate_limit_state.json\n"
    )

    # Write starter files
    for fname, content in [
        ("Dashboard.md", "# Dashboard\n"),
        ("Company_Handbook.md", "# Company Handbook\n\nBe professional and helpful.\n"),
        ("Business_Goals.md", "# Business Goals\n\nGrow our AI employee product. Launch by Q2 2026.\n"),
    ]:
        p = VAULT_PATH / fname
        if not p.exists():
            p.write_text(content)

    # Initial git commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=VAULT_PATH, capture_output=True
    )
    subprocess.run(["git", "add", "-A"], cwd=VAULT_PATH, check=True)
    try:
        subprocess.run(
            ["git", "commit", "-m", "init: test vault"],
            cwd=VAULT_PATH, check=True, capture_output=True
        )
        print("  initial commit OK")
    except subprocess.CalledProcessError:
        print("  nothing to commit (already initialized)")

    print(f"\nTest vault ready at: {VAULT_PATH}")
    print("Next: run the agents or drop test tasks with:")
    print("  python -m PlatinumTier.tests.drop_task --type email")


if __name__ == "__main__":
    setup()
