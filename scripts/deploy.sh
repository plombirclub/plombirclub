#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR="${PROJECT_DIR:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_PROD_FILE="${COMPOSE_PROD_FILE:-docker-compose.prod.yml}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://localhost/api/health}"
HEALTHCHECK_ATTEMPTS="${HEALTHCHECK_ATTEMPTS:-20}"
HEALTHCHECK_DELAY_SECONDS="${HEALTHCHECK_DELAY_SECONDS:-5}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Ошибка: команда '$1' не найдена." >&2
    exit 1
  }
}

compose() {
  docker compose --env-file .env -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" "$@"
}

echo "==> Проверка окружения"
require_command docker
require_command git
require_command curl

cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
  echo "Ошибка: файл .env не найден в $PROJECT_DIR" >&2
  exit 1
fi

if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
  echo "==> Резервная копия БД перед деплоем"
  compose run --rm worker sh /scripts/backup.sh
fi

echo "==> Обновление кода ветки $DEPLOY_BRANCH"
git fetch origin "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"

echo "==> Сборка образов"
compose build backend frontend worker scheduler

echo "==> Применение миграций"
compose run --rm backend alembic upgrade head

echo "==> Запуск сервисов"
compose up -d

echo "==> Проверка здоровья API: $HEALTHCHECK_URL"
attempt=1
while [ "$attempt" -le "$HEALTHCHECK_ATTEMPTS" ]; do
  if curl -fsS "$HEALTHCHECK_URL" >/dev/null 2>&1; then
    echo "✅ Деплой завершен: API отвечает"
    exit 0
  fi

  echo "Попытка $attempt/$HEALTHCHECK_ATTEMPTS: API пока недоступен, ждем ${HEALTHCHECK_DELAY_SECONDS}с..."
  attempt=$((attempt + 1))
  sleep "$HEALTHCHECK_DELAY_SECONDS"
done

echo "Ошибка: health-check не прошел. Проверьте логи: docker compose logs --tail=200" >&2
exit 1
