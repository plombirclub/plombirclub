#!/bin/sh
set -e

echo "Ожидание PostgreSQL..."
until python -c "
import os, sys
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL_SYNC'])
    conn.close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  sleep 2
done

echo "Применение миграций Alembic..."
alembic upgrade head

exec "$@"
