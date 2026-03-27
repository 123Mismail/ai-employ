#!/usr/bin/env bash
# Odoo daily backup — pg_dump + filestore tar + 7-day rotation
# Add to cron: 0 2 * * * /home/ubuntu/odoo-deploy/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
COMPOSE_DIR="${COMPOSE_DIR:-$(dirname "$0")}"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

echo "[backup] Stopping Odoo..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" stop odoo

echo "[backup] Dumping PostgreSQL..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
    pg_dump -U odoo -d odoo_db -F c \
    | gzip > "$BACKUP_DIR/odoo_${DATE}.dump.gz"

echo "[backup] Archiving filestore..."
docker run --rm \
    -v odoo_filestore:/filestore:ro \
    -v "$BACKUP_DIR":/out \
    alpine tar -czf "/out/odoo_filestore_${DATE}.tar.gz" /filestore

echo "[backup] Starting Odoo..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" start odoo

echo "[backup] Pruning backups older than 7 days..."
find "$BACKUP_DIR" -name "odoo_*.dump.gz" -mtime +6 -delete
find "$BACKUP_DIR" -name "odoo_filestore_*.tar.gz" -mtime +6 -delete

echo "[backup] Done — $(ls -lh "$BACKUP_DIR" | tail -4)"
