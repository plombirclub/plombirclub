# Э11 — деплой на Timeweb (пошагово)

Этот файл закрывает подэтап Э11: VPS, DNS, HTTPS и безопасный деплой.

## 1) Что делаем на вашей стороне (владелец)

1. Создайте VPS в Timeweb Cloud: Ubuntu 24.04, 2 CPU, 4 GB RAM, 40 GB SSD.  
2. В панели Beget добавьте A-запись:
   - `@` -> IP вашего VPS
   - `www` -> IP вашего VPS
3. Подождите распространение DNS (обычно 5-60 минут, иногда дольше).

Термин: **DNS** — это "телефонная книга интернета", где домен связывается с IP сервера.

## 2) Подготовка сервера

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install git curl ca-certificates
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Перезайдите по SSH, чтобы применились права группы `docker`.

## 3) Клонирование проекта и `.env`

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> /opt/plombirclub
cd /opt/plombirclub
cp .env.example .env
```

Обязательно в `.env` для прода:
- `APP_ENV=production`
- `APP_DEBUG=false`
- `APP_URL=https://plombirclub.ru`
- `COOKIE_SECURE=true`
- `POSTGRES_PASSWORD`, `SECRET_KEY`, `CSRF_SECRET_KEY`, `JWT_SECRET_KEY` — заменить на длинные случайные значения.

## 4) Первичный запуск контейнеров (без HTTPS)

```bash
docker compose --env-file .env up -d --build
docker compose --env-file .env run --rm backend alembic upgrade head
```

## 5) HTTPS (Let's Encrypt)

```bash
chmod +x scripts/setup-https.sh
LETSENCRYPT_EMAIL=you@example.com ./scripts/setup-https.sh
```

После этого переключаемся на прод-конфиг nginx (80/443):

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml up -d nginx
```

Проверка:

```bash
curl -I https://plombirclub.ru
curl -fsS https://plombirclub.ru/api/health
```

## 6) Рабочий деплой одной командой

```bash
chmod +x scripts/deploy.sh
HEALTHCHECK_URL=https://plombirclub.ru/api/health ./scripts/deploy.sh
```

`deploy.sh` делает автоматически:
1. Бэкап БД перед релизом.
2. `git pull` выбранной ветки.
3. Сборку контейнеров.
4. Миграции Alembic.
5. Перезапуск сервисов.
6. Проверку `/api/health`.

## 7) Автопродление сертификата (рекомендовано)

```bash
sudo crontab -e
```

Добавьте строку:

```cron
0 4 * * * docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot certbot/certbot renew --webroot -w /var/www/certbot --quiet && cd /opt/plombirclub && docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

## 8) Полезные команды диагностики

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml logs --tail=200 nginx backend worker scheduler
docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select now();"
```
