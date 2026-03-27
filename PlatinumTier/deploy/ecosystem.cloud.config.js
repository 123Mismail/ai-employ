module.exports = {
  apps: [
    {
      name: "cloud-agent",
      script: "/home/ubuntu/ai-employ/.venv/bin/python",
      args: "-m PlatinumTier.scripts.cloud_agent",
      cwd: "/home/ubuntu/ai-employ",
      env: {
        PYTHONUNBUFFERED: "1",
        ENV_FILE: "/home/ubuntu/ai-employ/.env.cloud",
      },
      exec_mode: "fork",
      restart_delay: 5000,
      max_restarts: 10,
      log_file: "/home/ubuntu/logs/cloud-agent.log",
      error_file: "/home/ubuntu/logs/cloud-agent-error.log",
      time: true,
    },
  ],
};
