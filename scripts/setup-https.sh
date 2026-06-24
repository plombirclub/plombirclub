#!/bin/sh
set -eu

DOMAIN="${DOMAIN:-plombirclub.ru}"
EMAIL="${LETSENCRYPT_EMAIL:-}"
PROJECT_DIR="${PROJECT_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_PROD_FILE="${COMPOSE_PROD_FILE:-docker-compose.prod.yml}"

if [ -z "$EMAIL" ] && [ -f "$PROJECT_DIR/.env" ]; then
  EMAIL=$(awk -F= '/^LETSENCRYPT_EMAIL=/{print $2}' "$PROJECT_DIR/.env" | tail -n 1)
fi

if [ -z "$EMAIL" ]; then
  echo "Ошибка: укажите LETSENCRYPT_EMAIL (email для Let's Encrypt)." >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || {
  echo "Ошибка: docker не найден." >&2
  exit 1
}

cd "$PROJECT_DIR"
mkdir -p /var/www/certbot

if [ ! -f ".env" ]; then
  echo "Ошибка: файл .env не найден в $PROJECT_DIR" >&2
  exit 1
fi

echo "==> Останавливаем nginx, чтобы освободить порт 80 для certbot"
docker compose --env-file .env -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" stop nginx >/dev/null 2>&1 || true
docker compose --env-file .env -f "$COMPOSE_FILE" stop nginx >/dev/null 2>&1 || true

echo "==> Получаем SSL-сертификат Let's Encrypt"
docker run --rm \
  -p 80:80 \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone --preferred-challenges http \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" --agree-tos --non-interactive

echo "==> Перезапускаем nginx с SSL"
docker compose --env-file .env -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up -d nginx

echo "✅ HTTPS настроен для $DOMAIN"
