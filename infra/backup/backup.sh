#!/bin/bash
# DayCast — PostgreSQL backup with 7-day rotation
set -euo pipefail

BACKUP_DIR="/Users/andrewmaier/daycast/backups"
DB_NAME="daycast"
PG_BIN="/usr/local/opt/postgresql@16/bin"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/daycast_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting backup..."
"$PG_BIN/pg_dump" "$DB_NAME" | gzip > "$BACKUP_FILE"
echo "[$(date)] Backup saved: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Rotate: delete backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "daycast_*.sql.gz" -mtime +"$KEEP_DAYS" -delete
echo "[$(date)] Rotated backups older than $KEEP_DAYS days"

echo "[$(date)] Backup complete."
