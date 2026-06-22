#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETAIN="${BACKUP_RETAIN_COUNT:-7}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_USER="${POSTGRES_USER:?POSTGRES_USER is required}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
POSTGRES_DB="${POSTGRES_DB:?POSTGRES_DB is required}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/plombirclub_${TIMESTAMP}.sql.gz"

export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$FILE"
unset PGPASSWORD

if [ "$RETAIN" -gt 0 ]; then
  ls -1t "$BACKUP_DIR"/plombirclub_*.sql.gz 2>/dev/null | tail -n +$((RETAIN + 1)) | while IFS= read -r old_file; do
    rm -f "$old_file"
  done
fi

echo "$FILE"
