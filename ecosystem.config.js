module.exports = {
  apps: [
    {
      name: "master-orchestrator",
      script: "uv",
      args: "run python Core/scripts/orchestrator.py",
      interpreter: "none",
      autorestart: true,
      windowsHide: true
    },
    {
      name: "bronze-filesystem-watcher",
      script: "uv",
      args: "run python BronzeTier/scripts/watchers/filesystem.py",
      interpreter: "none",
      autorestart: true,
      windowsHide: true
    },
    {
      name: "silver-gmail-watcher",
      script: "uv",
      args: "run python SilverTier/scripts/watchers/gmail.py",
      interpreter: "none",
      autorestart: true,
      windowsHide: true,
      env: {
        GMAIL_QUERY: "subject:testing is:unread"
      }
    },
    {
      name: "silver-whatsapp-watcher",
      script: "uv",
      args: "run python SilverTier/scripts/watchers/whatsapp.py",
      interpreter: "none",
      autorestart: true,
      windowsHide: true,
      env: {
        PYTHONPATH: "B:\\hackathone0-ai-employee\\ai-employ"
      }
    },
    {
      name: "silver-linkedin-watcher",
      script: "uv",
      args: "run python SilverTier/scripts/watchers/linkedin.py",
      interpreter: "none",
      autorestart: true,
      restart_delay: 10000,
      max_restarts: 10,
      windowsHide: true,
      env: {
        DRY_RUN: "false"
      }
    },
    {
      name: "gold-business-auditor",
      script: "uv",
      args: "run python GoldTier/scripts/skills/business_auditor.py",
      interpreter: "none",
      cron_restart: "0 0 * * *",
      autorestart: false,
      windowsHide: true
    },
    {
      name: "platinum-cloud-agent",
      script: "uv",
      args: "run python -m PlatinumTier.scripts.cloud_agent",
      interpreter: "none",
      autorestart: true,
      windowsHide: true,
      env: {
        VAULT_PATH: "AI_Employee_Vault",
        AGENT_ROLE: "cloud",
        DRY_RUN: "false"
      }
    },
    {
      name: "linkedin-scheduler",
      script: "uv",
      args: "run python -m PlatinumTier.scripts.linkedin_scheduler",
      interpreter: "none",
      autorestart: true,
      windowsHide: true,
      env: {
        VAULT_PATH: "AI_Employee_Vault",
        LINKEDIN_POST_HOUR: "9",
        LINKEDIN_POST_MINUTE: "0",
        LINKEDIN_CHECK_INTERVAL: "1800"
      }
    },
    {
      name: "platinum-local-agent",
      script: "uv",
      args: "run python -m PlatinumTier.scripts.local_agent",
      interpreter: "none",
      autorestart: true,
      windowsHide: true,
      env: {
        VAULT_PATH: "AI_Employee_Vault",
        AGENT_ROLE: "local",
        DRY_RUN: "false"
      }
    }
  ]
};
