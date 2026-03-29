module.exports = {
  apps: [
    {
      name: "cloud-agent",
      script: "/home/opc/ai-employ/.venv/bin/python",
      args: "-m PlatinumTier.scripts.cloud_agent",
      cwd: "/home/opc/ai-employ",
      env: {
        PYTHONUNBUFFERED: "1",
        VAULT_PATH: "/home/opc/ai-employ/AI_Employee_Vault",
      },
      exec_mode: "fork",
      restart_delay: 5000,
      max_restarts: 10,
    },
    {
      name: "gmail-watcher",
      script: "/home/opc/ai-employ/.venv/bin/python",
      args: "-m SilverTier.scripts.watchers.gmail",
      cwd: "/home/opc/ai-employ",
      env: {
        PYTHONUNBUFFERED: "1",
        VAULT_PATH: "/home/opc/ai-employ/AI_Employee_Vault",
        GMAIL_QUERY: "subject:(testing OR invoice) is:unread",
        GMAIL_POLL_INTERVAL: "60",
      },
      exec_mode: "fork",
      restart_delay: 5000,
      max_restarts: 10,
    },
    {
      name: "linkedin-scheduler",
      script: "/home/opc/ai-employ/.venv/bin/python",
      args: "-m PlatinumTier.scripts.linkedin_scheduler",
      cwd: "/home/opc/ai-employ",
      env: {
        PYTHONUNBUFFERED: "1",
        VAULT_PATH: "/home/opc/ai-employ/AI_Employee_Vault",
        LINKEDIN_POST_HOUR: "4",
        LINKEDIN_POST_MINUTE: "0",
        LINKEDIN_CHECK_INTERVAL: "1800",
      },
      exec_mode: "fork",
      restart_delay: 5000,
      max_restarts: 10,
    },
  ],
};
