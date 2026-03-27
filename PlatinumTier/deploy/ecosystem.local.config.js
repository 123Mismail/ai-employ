module.exports = {
  apps: [
    {
      name: "local-agent",
      script: "${HOME}/ai-employ/.venv/bin/python",
      args: "-m PlatinumTier.scripts.local_agent",
      cwd: "${HOME}/ai-employ",
      env: {
        PYTHONUNBUFFERED: "1",
        ENV_FILE: "${HOME}/ai-employ/.env.local",
      },
      exec_mode: "fork",
      restart_delay: 5000,
      max_restarts: 10,
      log_file: "${HOME}/logs/local-agent.log",
      error_file: "${HOME}/logs/local-agent-error.log",
      time: true,
    },
  ],
};
