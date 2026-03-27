import subprocess
import time
import sys
import os
from pathlib import Path

# Root detection
REPO_ROOT = Path(__file__).parent
VAULT_PATH = REPO_ROOT / "AI_Employee_Vault"

def launch_process(name, command):
    print(f"🚀 Launching {name}...")
    return subprocess.Popen(command, shell=True)

def main():
    processes = []
    
    # 1. Master Orchestrator (Core)
    processes.append(launch_process("Master Orchestrator", f"python Core/scripts/orchestrator.py"))
    
    # 2. Filesystem Watcher (Bronze)
    processes.append(launch_process("Filesystem Watcher", f"python BronzeTier/scripts/watchers/filesystem.py"))
    
    # 3. Gmail Watcher (Silver)
    processes.append(launch_process("Gmail Watcher", f"python SilverTier/scripts/watchers/gmail.py"))
    
    processes.append(launch_process("WhatsApp Watcher", f"python SilverTier/scripts/watchers/whatsapp.py"))

    # 4. Business Auditor (Gold)
    processes.append(launch_process("Business Auditor", f"python GoldTier/scripts/skills/business_auditor.py"))

    print("\n✅ AI Employee System is now RUNNING.")
    print("Press Ctrl+C to stop all components.\n")

    try:
        while True:
            time.sleep(10)
            # Check if processes are still running
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ Warning: A process has stopped (Exit code: {p.poll()})")
    except KeyboardInterrupt:
        print("\n🛑 Stopping AI Employee System...")
        for p in processes:
            p.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
