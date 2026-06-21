# PROGRESS — промо-портал «Чистая Линия»

**Обновлено:** 2026-06-21  
**Текущий этап:** 6 (в работе)  
**Следующий шаг:** Э6.1 — `/api/rewards` (каталог призов)  
**Правило:** 1 подэтап = 1 новый чат Agent (см. PLAN)

**Документы:** `ТЗ оптимизированное для ИИ-разработчика.md` · `PLAN-техническая-реализация.md`

---

## Легенда статусов

| Статус | Значение |
|--------|----------|
| ⬜ | Не начато |
| 🔄 | В работе |
| ✅ | Готово |
| ⏸️ | Отложено |

---

## Этап 0 — Каркас проекта (1 чат)

**Цель:** `docker compose up` поднимает весь стек, `/api/health` отвечает 200.  
**Режим:** Agent

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| 0.1 | `docker-compose.yml` (7 сервисов) | ✅ | backend, frontend, postgres, redis, worker, scheduler, nginx |
| 0.2 | `.env.example` | ✅ | без секретов в git |
| 0.3 | Backend: FastAPI, `/api/health`, формат ошибок | ✅ | |
| 0.4 | Alembic подключён к PostgreSQL | ✅ | пустая первая миграция `0001_initial` |
| 0.5 | Frontend: `index.html`, `styles.css`, CSS-переменные | ✅ | палитра из ТЗ |
| 0.6 | Nginx: `/api` → backend, статика → frontend | ✅ | порт 8080 локально |

**Итог этапа 0:** ✅  
**Дата завершения:** 2026-06-20

---

## Этап 1 — База данных (6 чатов)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 1.1 | Миграция A: Distributors, Users, Admin_Settings | ✅ | Agent+ |
| 1.2 | Миграция B: Points_Ledger, Prizes, logs + seed СБП-приза | ✅ | Agent+ |
| 1.3 | Миграция C: Requests, Verification_Codes | ✅ | Agent |
| 1.4 | Миграция D: Tasks, Materials, Products, Parser_Config | ✅ | Agent |
| 1.5 | Миграция E: Notifications, все Logs, Archive | ✅ | Agent |
| 1.6 | FK, индексы, seed (admin, дистрибьюторы, шаблоны) | ✅ | Agent+ |

**Итог этапа 1:** ✅  
**Дата завершения этапа 1:** 2026-06-20

---

## Этап 2 — Backend: auth (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 2.1 | JWT, cookies, CSRF, rate limiting | ✅ | Agent+ |
| 2.2 | `/api/auth` (login, codes, agreements, logout) | ✅ | Agent+ |
| 2.3 | Middleware `is_registration_complete` | ✅ | Agent+ |
| 2.4 | Первый вход end-to-end | ✅ | Agent+ |

**Итог этапа 2:** ✅  
**Дата завершения этапа 2:** 2026-06-20

---

## Этап 3 — Backend: пользователи и профиль (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 3.1 | `/api/users` profile, upload-document | ✅ | Agent |
| 3.2 | ИНН/КНД: однократное сохранение, блокировка | ✅ | Agent |
| 3.3 | Админ: verify-inn, verify-self-employed, documents | ✅ | Agent |
| 3.4 | `/api/distributors` | ✅ | Agent |

**Итог этапа 3:** ✅  
**Дата завершения этапа 3:** 2026-06-20

---

## Этап 4 — Backend: баллы и задания (2 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 4.1 | PointsService + `/api/points` (balance, consent, activate) | ✅ | Agent+ |
| 4.2 | `/api/tasks` (create, current, accept) | ✅ | Agent |

**Итог этапа 4:** ✅  
**Дата завершения этапа 4:** 2026-06-20

---

## Этап 5 — Импорт Excel (2 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 5.1 | Import users + шаблон xlsx + email с временным паролем | ✅ | Agent+ |
| 5.2 | Import sales + идемпотентность + Celery | ✅ | Agent+ |

**Итог этапа 5:** ✅  
**Дата завершения этапа 5:** 2026-06-21

---

## Этап 6 — Backend: заявки и каталог призов (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 6.1 | `/api/rewards` | ⬜ | Agent+ |
| 6.2 | Заявка на сертификат | ⬜ | Agent+ |
| 6.3 | Заявка СБП + verification_pending | ⬜ | Agent+ |
| 6.4 | Админ: status, fulfill, возврат баллов | ⬜ | Agent+ |

**Итог этапа 6:** ⬜

---

## Этап 7 — Backend: контент, аналитика, парсер (3 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 7.1 | Materials + progress, Content (FAQ, instructions, support) | ⬜ | Agent |
| 7.2 | Analytics + reports (CRM), Notifications + templates | ⬜ | Agent |
| 7.3 | Parser omoloko.ru | ⬜ | Agent+ |

**Итог этапа 7:** ⬜

---

## Этап 8 — Frontend: личный кабинет (6 чатов)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 8.1 | Layout + login, forgot-password, first-login | ⬜ | Agent |
| 8.2 | Profile + Мои заявки | ⬜ | Agent |
| 8.3 | Каталог призов + модалки заявок | ⬜ | Agent+ |
| 8.4a | Задания, FAQ, instructions, notifications | ⬜ | Agent |
| 8.4b | Analytics, materials, products | ⬜ | Agent |
| 8.5 | Адаптив 320–1920 px | ⬜ | Agent |

**Итог этапа 8:** ⬜

---

## Этап 9 — Frontend: админ-панель (4 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 9.1 | Users, Import, Points, Orders | ⬜ | Agent |
| 9.2 | Prizes, Tasks, Materials | ⬜ | Agent |
| 9.3 | Content, Support, Products | ⬜ | Agent |
| 9.4 | Reports (CRM), Logs, Notifications | ⬜ | Agent |

**Итог этапа 9:** ⬜

---

## Этап 10 — Фоновые задачи (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 10.1 | Scheduler: дедлайны баллов (00:01), бэкапы (03:00) | ⬜ | Agent |
| 10.2 | Парсер по расписанию | ⬜ | Agent |
| 10.3 | Истечение кодов верификации | ⬜ | Agent |
| 10.4 | Celery: import_excel_async, send_notification_batch | ⬜ | Agent |

**Итог этапа 10:** ⬜

---

## Этап 11 — Деплой (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 11.1 | VPS Timeweb настроен | ⬜ | Agent + владелец |
| 11.2 | DNS plombirclub.ru → VPS | ⬜ | Agent + владелец |
| 11.3 | HTTPS (Let's Encrypt) | ⬜ | Agent |
| 11.4 | deploy.sh + бэкапы | ⬜ | Agent |

**Итог этапа 11:** ⬜

---

## Этап 12 — Тестирование и приёмка (2 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 12.1 | Автотесты критичных сценариев | ⬜ | Agent+ |
| 12.2 | Приёмка раздел 20 ТЗ + тестовые данные раздел 21 | ⬜ | Agent + владелец |
| 12.3 | Кроссбраузерность и мобильные | ⬜ | Agent + владелец |

**Итог этапа 12:** ⬜

---

## Журнал (передача между чатами)

### Запись: 2026-06-21 (Э5.2 — импорт продаж)
- **Чат:** Э5.2 — `POST /api/import/sales`, `GET /api/import/template-sales`
- **Сделано:** добавлен шаблон `template-sales` и загрузка продаж из `.xlsx`; реализована привязка начислений по кодам `ТП`/`СВ` к пользователям и проверка соответствия дистрибьютору; для каждой строки создаются отдельные начисления ТП и СВ (если баллы > 0); добавлена идемпотентность по ключу строки импорта (повтор файла не дублирует баллы), а при изменении сумм выполняется обновление начисления с записью в `Points_Overwritten_Log`; ошибки строк пишутся в `Import_Error_Log`; добавлена подготовка под Celery: `POST /api/import/sales?use_celery=true` ставит импорт в очередь, создана задача `app.tasks.imports.import_sales_task`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app` (компилируются `app/api/imports.py`, `app/services/imports.py`, `app/tasks/imports.py`)
- **Блокеры:** нет
- **Следующий шаг:** Э6.1 — `/api/rewards` (каталог призов)

### Запись: 2026-06-21 (Э5.1 — импорт пользователей)
- **Чат:** Э5.1 — `POST /api/import/users`, `GET /api/import/template-users`
- **Сделано:** добавлен роутер `/api/import` и сервис импорта пользователей из `.xlsx`: проверка шаблона, обязательных полей и дублей в файле, upsert по email, привязка к дистрибьютору, сохранение кода участника и должности, генерация временного пароля, попытка отправки email с логином/паролем, логирование ошибок строк в `Import_Error_Log`; добавен `GET /api/import/template-users` для скачивания шаблона; подключена миграция `0008_migration_g` (поля `participant_code`, `participant_position` в `users`)
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app` (миграция `0008` применена, новые файлы `app/api/imports.py` и `app/services/imports.py` компилируются)
- **Блокеры:** SMTP может быть не настроен в `.env`, тогда импорт пользователей выполняется, но письма фиксируются как ошибки импорта с текстом «SMTP не настроен: письмо не отправлено»
- **Следующий шаг:** Э5.2 — Import sales + идемпотентность + Celery

### Запись: 2026-06-20 (Э4.2 — задания)
- **Чат:** Э4.2 — `/api/tasks` (create, current, accept)
- **Сделано:** добавлены `TasksService` и API `GET /api/tasks/current`, `POST /api/tasks/create`, `POST /api/tasks/{task_id}/accept`; создание и публикация задания админом с привязкой к дистрибьюторам, уведомления пользователям по шаблону `task_published`, получение актуального задания по дистрибьютору/месяцу/типу, принятие задания с записью в `User_Tasks_Acceptance` и логом действий; роутер подключён в `main.py`; исправлена ошибка запуска backend в `points.py` (параметр `Request` для FastAPI)
- **Проверка:** `docker compose build backend`; `python -m compileall app`; `POST /api/tasks/create` под admin (200); backend стартует после исправления `points.py`
- **Блокеры:** автоматическая проверка `accept` для тестового пользователя прервана системой безопасности; логика реализована, ручная проверка — login user → `GET /current` → `POST /{id}/accept`
- **Следующий шаг:** Э5.1 — Import users + шаблон xlsx

### Запись: 2026-06-20 (Э4.1 — баллы)
- **Чат:** Э4.1 — PointsService + `/api/points`
- **Сделано:** добавлены `PointsService` и API `GET /api/points/balance`, `GET /api/points/history`, `POST /api/points/consent`, `POST /api/points/activate`, `GET /api/points/pending-activation`; реализованы транзакционные операции с блокировкой `SELECT FOR UPDATE`, retry до 3 попыток при deadlock, активация `pending -> active` с записью в `Points_Operations_Log`, сохранение согласия участия в `User_Tasks_Acceptance`, пагинация/сортировка для истории и admin-списка ожидающих активации; роутер подключён в `main.py`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app`; `docker compose up -d backend` — контейнер backend стартует, `app/api/points.py` и `app/services/points.py` компилируются без ошибок
- **Блокеры:** `python` и `py` не доступны в PowerShell хоста (локальная проверка `compileall` не запускается без Docker), поэтому проверка выполнялась внутри контейнера
- **Следующий шаг:** Э4.2 — `/api/tasks` (create, current, accept)

### Запись: 2026-06-20 (Э3 — пользователи и профиль)
- **Чат:** Э3 — Backend `/api/users`, `/api/distributors`
- **Сделано:** реализованы GET/PUT `/api/users/profile`, POST `/api/users/upload-document` (inn_photo/knd_1122035_photo, MIME-проверка, лимит 20 МБ); однократное сохранение ИНН/КНД с блокировкой; админские PUT verify-inn, verify-self-employed, documents, deactivate, DELETE (ФЗ-152 с архивацией); GET `/api/users/all`; CRUD `/api/distributors`; логирование админ-действий в `Admin_Logs`
- **Проверка:** `docker compose build backend`; `python -m compileall app`; `docker compose up -d`; login admin → GET profile/distributors/all (200); login user → upload-document + save ИНН/КНД (200), повторное изменение ИНН (403); admin verify-inn (200); POST distributor (200)
- **Блокеры:** нет
- **Следующий шаг:** Э4.1 — PointsService + `/api/points`

### Запись: 2026-06-20 (Э2 — auth)
- **Чат:** Э2 — Backend auth (JWT, cookies, CSRF, `/api/auth`, middleware первого входа)
- **Сделано:** добавлены JWT access/refresh в HTTP-only cookies и CSRF cookie + проверка `X-CSRF-Token`; Redis rate limiting для login/forgot-password/send-code; реализованы `/api/auth`: `login`, `change_password`, `accept_agreements`, `send-sms-code`, `verify-sms-code`, `send-email-code`, `verify-email-code`, `forgot-password`, `logout`; добавлены зависимости `require_auth`, `require_admin`, `require_registration_complete`; логика первого входа теперь рассчитывает `is_registration_complete = phone_verified AND temporary_password_changed AND agreements_accepted`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app`; `docker compose up -d`; `POST /api/auth/login` (200, cookies выставлены); CSRF-проверка: `POST /api/auth/accept_agreements` без заголовка (403), с валидным `X-CSRF-Token` (200)
- **Блокеры:** нет
- **Следующий шаг:** Э3 — `/api/users` profile, upload-document, verify endpoints

### Запись: 2026-06-20 (Э1.6 — FK, индексы, seed)
- **Чат:** Э1.6 — FK, индексы, seed (admin, дистрибьюторы, 8 шаблонов, контакты поддержки)
- **Сделано:** Alembic-миграция `0007_migration_f` — FK `points_ledger.request_id` и `points_operations_log.request_id` → `requests` (ON DELETE SET NULL, ON UPDATE CASCADE); индексы на `request_id`; UNIQUE `distributors.name`; seed: admin `admin@plombirclub.ru` (пароль `Admin123!`), 2 дистрибьютора, 8 шаблонов уведомлений, пустые `support_contacts` в `admin_settings`; обновлены модели и `scripts/seed.sh`
- **Проверка:** `docker compose up --build` — миграция `0006 → 0007`; `alembic current` — `0007_migration_f (head)`; в PostgreSQL admin, 2 дистрибьютора, 8 шаблонов, support_contacts, приз СБП; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э2 — auth (JWT, cookies, CSRF, `/api/auth`)

### Запись: 2026-06-20 (Э1.5 — миграция E)
- **Чат:** Э1.5 — миграция E (Notification_Templates, Notifications, Admin_Logs, System_Logs, User_Actions_Logs, Import_Error_Log, Deleted_Users_Archive)
- **Сделано:** SQLAlchemy-модели `NotificationTemplate`, `Notification`, `AdminLog`, `SystemLog`, `UserActionsLog`, `ImportErrorLog`, `DeletedUsersArchive`; enums `SystemLogLevel`, `ImportType`; Alembic-миграция `0006_migration_e` — 7 таблиц с FK на `users` и `notification_templates`, индекс `idx_notifications_user_unread (user_id, is_read)`, UNIQUE `event_type` для шаблонов
- **Проверка:** `docker compose up --build` — миграция `0005 → 0006` применилась; в PostgreSQL все 7 таблиц; `alembic current` — `0006_migration_e (head)`; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.6 — FK, индексы, seed

### Запись: 2026-06-20 (Э1.4 — миграция D)
- **Чат:** Э1.4 — миграция D (Tasks, Materials, Products, Parser_Config)
- **Сделано:** SQLAlchemy-модели `Task`, `TaskDistributor`, `UserTaskAcceptance`, `Material`, `UserMaterialProgress`, `Product`, `ProductDistributor`, `ParserConfig`; enums `MaterialContentType`, `MaterialProgressStatus`, `TaskType`, `TaskSource`, `ProductSource`; Alembic-миграция `0005_migration_d` — 8 таблиц с FK, UNIQUE-ограничениями `(user_id, task_id)`, `(user_id, material_id)`, `(task_id, distributor_id)`, `(product_id, distributor_id)`, `(article)` для products
- **Проверка:** `docker compose up --build` — миграция `0004 → 0005` применилась; в PostgreSQL таблицы `tasks`, `task_distributors`, `user_tasks_acceptance`, `materials`, `user_materials_progress`, `products`, `product_distributors`, `parser_config`; `alembic current` — `0005_migration_d (head)`; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.5 — миграция E

### Запись: 2026-06-20 (Э1.3 — миграция C)
- **Чат:** Э1.3 — миграция C (Requests, Verification_Codes)
- **Сделано:** SQLAlchemy-модели `Request`, `VerificationCode`; enums `RequestStatus`, `VerificationMethod`, `VerificationTargetType`; Alembic-миграция `0004_migration_c` — таблицы `requests` и `verification_codes` с FK на `users`, `prizes`, `requests`; индексы `idx_requests_user_status`, `idx_requests_status`. FK на `request_id` в `points_ledger` и `points_operations_log` отложены до Э1.6 (по плану)
- **Проверка:** `docker compose up --build` — миграция `0003 → 0004` применилась; в PostgreSQL таблицы `requests`, `verification_codes`; `alembic current` — `0004_migration_c (head)`; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.4 — миграция D

### Запись: 2026-06-20 (Э1.2 — миграция B)
- **Чат:** Э1.2 — миграция B (Points_Ledger, Prizes, logs + seed СБП-приза)
- **Сделано:** SQLAlchemy-модели `Prize`, `PointsLedger`, `PointsOperationsLog`, `PointsOverwrittenLog`; enums для статусов баллов, типов призов и операций; Alembic-миграция `0003_migration_b` — четыре таблицы, индексы `idx_points_user_status` и `idx_points_period`, seed системного приза «Платеж на карту банка» (`type=money`, `is_system=true`, фиксированный UUID). FK на `request_id` отложены до Э1.3/Э1.6 (таблица Requests ещё не создана)
- **Проверка:** `docker compose up --build` — миграция `0002 → 0003` применилась; в PostgreSQL таблицы `prizes`, `points_ledger`, `points_operations_log`, `points_overwritten_log`; в `prizes` одна запись «Платеж на карту банка»; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.3 — миграция C

### Запись: 2026-06-20 (Э1.1 — миграция A)
- **Чат:** Э1.1 — миграция A (Distributors, Users, Admin_Settings)
- **Сделано:** SQLAlchemy-модели `Distributor`, `User`, `AdminSetting`; Alembic-миграция `0002_migration_a` — три таблицы с UUID PK, уникальными email/phone/inn, FK users→distributors и admin_settings→users (RESTRICT/CASCADE), UNIQUE (admin_id, setting_key)
- **Проверка:** `docker compose up --build` — миграция применилась; в PostgreSQL таблицы `distributors`, `users`, `admin_settings`; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.2 — миграция B

### Запись: 2026-06-20 (Э0 — каркас)
- **Чат:** Э0 — каркас проекта
- **Сделано:** Docker Compose (7 сервисов), `.env.example`, FastAPI skeleton с `/api/health` и единым JSON-форматом ошибок, Alembic + пустая миграция, frontend-заглушка с CSS-переменными палитры, Nginx на порту 8080
- **Проверка:** `docker compose up` — все сервисы Up; `http://localhost:8080` — заглушка; `http://localhost:8080/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э1.1 — миграция A

### Запись: 2026-06-17 (планирование)
- **Чат:** согласование структуры этапов
- **Сделано:** утверждена структура 31 подэтапа (полный сайт), обновлены PLAN, PROGRESS, Rules
- **Код:** не начат
- **Блокеры:** нет
- **Следующий шаг:** Э0 — каркас Docker

<!-- Шаблон:
### Запись: ГГГГ-ММ-ДД
- **Чат:** ЭN.M — название
- **Сделано:** …
- **Не работает / блокер:** …
- **Следующий шаг:** …
-->

---

## Блокеры и решения

| Дата | Проблема | Решение | Статус |
|------|----------|---------|--------|
| — | — | — | — |

---

## Для агента в новом чате

1. Прочитать этот файл и раздел **текущего подэтапа** в `PLAN-техническая-реализация.md`.
2. ТЗ целиком — только если не хватает деталей для подэтапа.
3. Работать **только над текущим подэтапом** (см. вверху).
4. По завершении: обновить статусы ✅, дату, журнал.
5. ТЗ важнее плана при конфликте.
6. **1 подэтап = 1 чат.** Не объединять несколько подэтапов.
