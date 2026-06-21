#!/bin/sh
# Начальные данные применяются миграцией Alembic 0007_migration_f при старте backend.
# Этот скрипт — для ручной проверки после `docker compose up`.
set -e

echo "Seed встроен в миграцию 0007_migration_f (admin, дистрибьюторы, шаблоны, контакты)."
echo "Проверка: docker compose exec backend alembic current"
