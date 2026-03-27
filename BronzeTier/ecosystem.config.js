module.exports = {
  apps: [
    {
      name: "filesystem-watcher",
      script: "uv",
      args: "run python scripts/watchers/filesystem.py",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "100M"
    },
    {
      name: "gmail-watcher",
      script: "uv",
      args: "run python scripts/watchers/gmail.py",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "150M"
    }
  ]
};
