# PROGRESS — промо-портал «Чистая Линия»

**Обновлено:** 2026-06-21 (Э10 — Фоновые задачи: scheduler, Celery, бэкапы, просрочка баллов)  
**Текущий этап:** 10 ✅  
**Следующий шаг:** Э11 — Деплой (VPS Timeweb, DNS, HTTPS)
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
| 1.6 | FK, индексы, seed (admin, дистрибьюторы, шаблоны) | ✅ | Agent+; доп. миграция `0010` — обложка заданий, демо-задачи |

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
| 4.2 | `/api/tasks` (list, current, get, create, create-with-cover, accept) | ✅ | Agent; расширено в миграции `0010` |

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
| 6.1 | `/api/rewards` | ✅ | Agent+ |
| 6.2 | Заявка на сертификат | ✅ | Agent+ |
| 6.3 | Заявка СБП + verification_pending | ✅ | Agent+ |
| 6.4 | Админ: status, fulfill, возврат баллов | ✅ | Agent+ |

**Итог этапа 6:** ✅  
**Дата завершения этапа 6:** 2026-06-21

---

## Этап 7 — Backend: контент, аналитика, парсер (3 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 7.1 | Materials + progress, Content (FAQ, instructions, support) | ✅ | Agent |
| 7.2 | Analytics + reports (CRM), Notifications + templates | ✅ | Agent |
| 7.3 | Parser omoloko.ru | ✅ | Agent+ |

**Итог этапа 7:** ✅  
**Дата завершения этапа 7:** 2026-06-21

---

## Этап 8 — Frontend: личный кабинет (6 чатов)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 8.1 | Layout + login, forgot-password, first-login | ✅ | Agent |
| 8.2 | Profile + Мои заявки | ✅ | Agent |
| 8.3 | Каталог призов + модалки заявок | ✅ | Agent+ |
| 8.4a | Задания, FAQ, instructions, notifications | ✅ | Agent; условия акции: сетка Froneri, «Все периоды» |
| 8.4b | Analytics, materials, products | ✅ | Agent; визуал как Froneri, API `/api/products` |
| 8.5 | Адаптив 320–1920 px | ✅ | Agent; сборка Autoprefixer + Babel, FAB поддержки, mobile-first |

**Итог этапа 8:** ✅  
**Дата завершения этапа 8:** 2026-06-21

---

## Этап 9 — Frontend: админ-панель (4 чата)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 9.1 | Users, Import, Points, Orders | ✅ | Agent |
| 9.2 | Prizes, Tasks, Materials | ✅ | Agent |
| 9.3 | Content, Support, Products | ✅ | Agent |
| 9.4 | Reports (CRM), Logs, Notifications | ✅ | Agent |

**Итог этапа 9:** ✅  
**Дата завершения этапа 9:** 2026-06-21

---

## Этап 10 — Фоновые задачи (1 чат)

| # | Задача | Статус | Режим |
|---|--------|--------|-------|
| 10.1 | Scheduler: дедлайны баллов (00:01), бэкапы (03:00) | ✅ | Agent |
| 10.2 | Парсер по расписанию | ✅ | Agent |
| 10.3 | Истечение кодов верификации | ✅ | Agent |
| 10.4 | Celery: import_excel_async, send_notification_batch | ✅ | Agent |

**Итог этапа 10:** ✅  
**Дата завершения этапа 10:** 2026-06-21

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

### Запись: 2026-06-21 (Э10 — Фоновые задачи)
- **Чат:** Э10 — Scheduler, Celery, бэкапы, просрочка баллов
- **Сделано:** Celery Beat — `check_points_deadlines` (00:01, дни 16–21), `backup_postgres` (03:00, 7 копий), `run_product_parser` (еженедельно пн 04:00), `expire_verification_codes` (каждые 3 мин); Celery tasks — `import_users_task`, `import_sales_task`, `send_notification_batch_task`; `PointsService.expire_overdue_pending_points` с индивидуальными дедлайнами (+5 раб. дней); уведомления `points_activation` при импорте продаж; миграция `0012` — шаблон уведомления; `scripts/backup.sh` для деплоя; папка `/backups/`; admin-import: Celery для users и sales
- **Проверка:** `docker compose build backend worker scheduler frontend`; `compileall app`; миграция `0012`; worker — 6 задач зарегистрированы; ручной `backup_postgres_task` — файл в `backups/`; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э11 — Деплой VPS Timeweb

### Запись: 2026-06-21 (Э9.2–9.4 — Админка: призы, контент, отчёты)
- **Чат:** Э9.2–9.4 — Frontend админ-панель (остальные экраны)
- **Сделано:** страницы `/admin/prizes.html`, `/admin/tasks.html`, `/admin/materials.html`, `/admin/content.html` (FAQ, инструкции, контакты поддержки), `/admin/products.html`, `/admin/reports.html`, `/admin/logs.html`, `/admin/notifications.html`; расширено меню админки; backend: список заданий для admin, CRUD продукции, `GET /logs/admin|system|user-actions`, `GET /rewards/{id}/visibility`
- **Проверка:** `npm run build`; `docker compose build backend frontend`; `compileall app`; новые admin-страницы в `frontend/dist/admin/`
- **Блокеры:** нет
- **Следующий шаг:** Э10 — Scheduler, Celery, expire codes

### Запись: 2026-06-21 (Э9.1 — Админка Users, Import, Points, Orders)
- **Чат:** Э9.1 — Frontend админ-панель (ядро)
- **Сделано:** страницы `/admin/users.html`, `/admin/import.html`, `/admin/points.html`, `/admin/orders.html`; общий layout админки (`admin-layout.js`, `admin.css`); guard `requireAdmin`; редирект admin после login; Users: поиск, фильтры, карточка (ИНН, самозанятость, дистрибьютор, документы, блокировка, ФЗ-152); Import: шаблоны и загрузка users/sales (+ Celery); Points: список pending-activation; Orders: фильтр статусов, смена статуса, fulfill сертификат/СБП; backend: `PUT /users/{id}/distributor`, `PUT /users/{id}/activate-points`, email участника в `/orders/all`
- **Проверка:** `npm run build`; `docker compose build backend frontend`; `compileall app`; `http://localhost:8080/admin/users.html` — 200; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э9.2 — Prizes, Tasks, Materials

### Запись: 2026-06-21 (Э8.5 — Адаптив 320–1920 px)
- **Чат:** Э8.5 — Адаптив и кроссбраузерная сборка фронтенда
- **Сделано:** сборка фронтенда (PostCSS Autoprefixer + Babel/core-js) в Docker; файл `responsive.css` — mobile-first 320–1920 px, кнопки и touch-цели 44×44; мобильная шапка с логотипом «ЧИСТАЯ ЛИНИЯ»; блок пользователя и выход в боковом меню; зелёная FAB-кнопка поддержки с бейджем уведомлений; исправлены мелкие кнопки «Читать»/«Подробнее»; убраны упоминания Froneri из комментариев CSS
- **Проверка:** `npm run build` в frontend; `docker compose build frontend`; `http://localhost:8080/pages/login.html` — 200; CSS с `-webkit-` префиксами
- **Блокеры:** нет
- **Следующий шаг:** Э9.1 — Админка: Users, Import, Points, Orders

### Запись: 2026-06-21 (доработка Э8.4b — аналитика и демо-материалы)
- **Чат:** правки по замечаниям владельца
- **Сделано:** убраны лишние карточки сводки на аналитике; график и подсказки показывают **кол-во коробок** (не баллы); таблица и экспорт Excel — колонки «Кол-во кор» и «Баллы» отдельно; в комментарий импорта продаж добавлены коробки и дата документа; миграция `0011` — 2 тестовых опубликованных материала
- **Проверка:** `docker compose build`; миграция `0011`; страницы analytics/materials — 200
- **Блокеры:** старые начисления до правки импорта не содержат «Кол-во кор» в комментарии — для них в графике будет 0, нужен повторный импорт продаж
- **Следующий шаг:** Э8.5 — Адаптив 320–1920 px

### Запись: 2026-06-21 (Э8.4b — Analytics, materials, products)
- **Чат:** Э8.4b — Frontend аналитика, материалы, продукция
- **Сделано:** страницы `/pages/analytics.html` (график продаж, фильтры дат/периода, экспорт Excel), `/pages/materials.html` (кольца прогресса, сетка карточек, просмотр PDF/видео/изображений, статусы изучения), `/pages/products.html` (каталог по группам, карточка SKU); стили `analytics.css`, `materials.css`, `products.css`; JS-модули; добавлен backend `GET /api/products`, `/groups`, `/{id}` для каталога продукции; метод скачивания файлов в `api.js`
- **Проверка:** `docker compose build frontend backend`; `compileall` products API; `http://localhost:8080/pages/analytics.html`, `materials.html`, `products.html` — 200; `/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э8.5 — Адаптив 320–1920 px

### Запись: 2026-06-21 (синхронизация PROGRESS + PLAN после доработки Э8.4a)
- **Чат:** документы — без изменений кода
- **Сделано:** обновлены PROGRESS и PLAN: актуальный API заданий (Э4.2), миграция `0010`, итог Э8.4a (сетка + фильтр); пометки для будущих Э9.1 (дистрибьютор) и Э9.2 (админка заданий)
- **Проверка:** только чтение файлов
- **Блокеры:** нет
- **Следующий шаг:** Э8.4b — Analytics, materials, products

### Запись: 2026-06-21 (доработка Э8.4a — Условия акции как Froneri)
- **Чат:** доработка Условия акции + дистрибьютор тестового пользователя
- **Сделано:** сетка карточек условий акции как на референсе (обложка, заголовок, период, «Читать», дата); детальная страница с «Назад» и «Согласен, хочу участвовать»; фильтр «Период» с пунктом «Все периоды» по умолчанию; backend: `cover_image_path`, `GET /api/tasks`, `GET /api/tasks/{id}`, `POST /api/tasks/create-with-cover`; nginx раздаёт `/uploads/`; миграция `0010`: обложка, демо-задачи, дистрибьютор для `testuser@plombirclub.ru`; обновлены ТЗ (разделы 11, 14.10, 15.7) и PLAN Э8.4a
- **Проверка:** `docker compose build backend frontend`; миграция `0010`; `http://localhost:8080/pages/news.html` под `testuser@plombirclub.ru`
- **Блокеры:** нет
- **Следующий шаг:** Э8.4b — Analytics, materials, products

### Запись: 2026-06-21 (Э8.4a — Задания, FAQ, инструкции, уведомления) — **заменено доработкой выше**
- **Чат:** Э8.4a — Frontend задания, FAQ, instructions, notifications
- **Сделано:** первый вариант `/pages/news.html` через `GET /api/tasks/current` (без сетки карточек); FAQ, инструкции, уведомления — без изменений в доработке
- **Примечание:** актуальный UI условий акции — в записи «доработка Э8.4a — Условия акции как Froneri»

### Запись: 2026-06-21 (Э8.3 — Каталог призов + модалки заявок)
- **Чат:** Э8.3 — Frontend каталог призов и заявки
- **Сделано:** добавлена страница `/pages/catalog.html` с карточками призов из `GET /api/rewards` и блоком текущего баланса из `GET /api/points/balance`; реализованы модалки заявок на сертификат и СБП по ТЗ (номинал 1000–10000, шаг 1000, проверки ИНН/КНД/самозанятости/баланса, окно подтверждения «Да/Нет»); реализован сценарий `verification_pending` для СБП (выбор способа подтверждения SMS/email, отправка кода и проверка через `POST /api/orders/confirm-code`); добавлены стили `catalog.css` и логика `catalog.js`; обновлён текст на главной странице ЛК о доступности каталога
- **Проверка:** `docker compose build frontend`; `docker compose up -d`; `http://localhost:8080/pages/catalog.html` — 200; создание заявок с ветками `placed` и `verification_pending` проверяется через UI каталога
- **Блокеры:** нет
- **Следующий шаг:** Э8.4a — Задания, FAQ, instructions, notifications

### Запись: 2026-06-21 (Э8.2 — Profile + Мои заявки)
- **Чат:** Э8.2 — Frontend профиль и мои заявки
- **Сделано:** страница `/pages/profile.html` с вкладками «Основные данные» и «Мои заявки»; форма профиля (ФИО, email/телефон read-only, ИНН и КНД с однократным сохранением, загрузка документов, статус самозанятого под аватаром, смена пароля); список заявок из `GET /api/orders/my` со статусами, номиналом, комментариями и данными выдачи (промокод/ссылка/файл для сертификатов, телефон и номер операции для СБП); стили `profile.css`, логика `profile.js`; обновлена заметка на главной странице ЛК
- **Проверка:** `docker compose build frontend`; `docker compose up -d`; `http://localhost:8080/pages/profile.html` — 200; `http://localhost:8080/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э8.3 — Каталог призов + модалки заявок

### Запись: 2026-06-21 (Э8.1 — Layout + login, forgot-password, first-login)
- **Чат:** Э8.1 — Frontend каркас ЛК и вход
- **Сделано:** создан общий layout ЛК (шапка, боковое меню без «Рейтинг участников», блок поддержки из API); страницы `/pages/login.html`, `/pages/forgot-password.html`, `/pages/first-login.html`, `/pages/home.html`; JS-модули `api.js`, `auth.js`, `layout.js` с cookies и CSRF; пошаговый мастер первого входа (телефон SMS/email, смена пароля, согласия); редиректы по статусу регистрации; обновлён `frontend/Dockerfile` (копирование `pages/`); мелкая правка backend: сохранение телефона при отправке SMS-кода (для ветки email-подтверждения)
- **Проверка:** `docker compose build frontend backend`; `docker compose up -d`; `http://localhost:8080/api/health` — 200; `http://localhost:8080/pages/login.html` — 200; `compileall app/api/auth.py` в контейнере backend
- **Блокеры:** нет
- **Следующий шаг:** Э8.2 — Profile + Мои заявки

### Запись: 2026-06-21 (Э7.3 — Parser omoloko.ru)
- **Чат:** Э7.3 — `/api/parser`
- **Сделано:** добавлены `ParserService` и API `GET/PUT /api/parser/config`, `POST /api/parser/run`, `GET /api/parser/logs`; реализовано автосоздание конфигурации парсера (URL донора + JSON-селекторы), ручной запуск парсинга `omoloko.ru` с ограничением количества карточек и выбором полей для обновления; реализована защита ручных правок: при обновлении существующих товаров парсер не затирает поля, отмеченные в `manual_overrides`; добавлено логирование запусков и ошибок в `System_Logs` (`source=parser`) и `Admin_Logs`; роутер подключён в `main.py`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app` (компилируются `app/api/parser.py`, `app/services/parser.py`, `app/main.py`)
- **Блокеры:** на хосте команда `python` не установлена (проверка выполняется внутри Docker, это штатно)
- **Следующий шаг:** Э8.1 — Layout + login, forgot-password, first-login

### Запись: 2026-06-21 (Э7.2 — Analytics + Reports + Notifications)
- **Чат:** Э7.2 — `/api/analytics`, `/api/reports`, `/api/notifications`
- **Сделано:** добавлены `AnalyticsService`, `ReportsService`, `NotificationService`; реализован `/api/analytics`: сводка продаж пользователя (`/my`), детальные строки (`/my-raw`), баланс (`/balance`), экспорт Excel (`/export`), админ-дашборд (`/dashboard`), аналитика участника (`/users/{id}`); реализован `/api/reports`: CRM-отчёт пользователей с настраиваемыми колонками из `Admin_Settings` (`crm_report_layout`), скачивание Excel, отчёт ошибок импорта (`/sync-errors` + download), GET/PUT `/layout` для CRM-конструктора; реализован `/api/notifications`: список с счётчиком непрочитанных, отметка прочитанным, CRUD шаблонов админом; уведомления подключены к заявкам, подтверждению ИНН/самозанятости и публикации заданий; роутеры подключены в `main.py`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall` (новые модули компилируются); `docker compose up -d backend`; `http://localhost:8080/api/health` — 200
- **Блокеры:** нет
- **Следующий шаг:** Э7.3 — Parser omoloko.ru

### Запись: 2026-06-21 (Э7.1 — Materials + Content)
- **Чат:** Э7.1 — `/api/materials`, `/api/content`
- **Сделано:** добавлены `MaterialsService` и `ContentService`; реализован `/api/materials`: список опубликованных материалов со статусом изучения (`Не начат` / `Начат` / `Изучен`), счётчик «Изучено материалов: X / Y», просмотр материала, фиксация прогресса (`open`, `view_page`, `view_video` ≥95%), CRUD админа с загрузкой файлов (JPG/PNG/PDF/PPTX/MP4 до 100 МБ), скрытие материала, статистика статусов для админа; реализован `/api/content`: `GET/PUT /{slug}` для `faq`, `instructions`, `support_contacts` через `Admin_Settings` (контакты поддержки не в коде); роутеры подключены в `main.py`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app/api/materials.py app/api/content.py app/services/materials.py app/services/content.py`; `docker compose up -d backend`
- **Блокеры:** нет
- **Следующий шаг:** Э7.2 — Analytics + reports, Notifications + templates

### Запись: 2026-06-21 (исправление статусов и СБП-кода по ТЗ п.8)
- **Чат:** bugfix — `orders.py`, `api/orders.py`
- **Сделано:** переходы статусов заявок приведены к ТЗ 8.2: `verification_pending -> placed/cancelled`, `placed -> confirmed/rejected`, `confirmed -> processing/rejected`, `processing -> rejected` (а `processing -> fulfilled` только через `/fulfill`); в `fulfill_order` добавлено требование статуса `processing`; для СБП-кода добавлен rate limit на отправку и проверку: максимум 5 попыток за 5 минут; срок жизни кода = 5 минут; срок `verification_pending` = 5 минут; при истечении срока заявка автоматически переводится в `cancelled`
- **Проверка:** `docker compose run --rm backend python -m compileall app/services/orders.py app/api/orders.py`; `docker compose run --rm backend python -m compileall app`
- **Блокеры:** нет
- **Следующий шаг:** Э7.1 — Materials + Content

### Запись: 2026-06-21 (исправление ошибок Э4.1 и Э6)
- **Чат:** bugfix — `points.py`, `orders.py`
- **Сделано:** убрано дублирование финансовой логики из `OrdersService`; операции резервирования, возврата и списания баллов переведены в единый `PointsService`; добавлены методы `refund_reserved_points_for_request` и `redeem_reserved_points_for_request`; для финансовых операций добавлен единый параметр `commit` (для атомарности в сценариях заявок)
- **Проверка:** `docker compose run --rm backend python -m compileall app/services/points.py app/services/orders.py`; `docker compose run --rm backend python -m compileall app`
- **Блокеры:** нет
- **Следующий шаг:** Э7.1 — Materials + Content

### Запись: 2026-06-21 (централизация финансовой логики во всех этапах)
- **Чат:** bugfix — `points.py`, `orders.py`, `imports.py`
- **Сделано:** проведен аудит backend на прямые операции с `Points_Ledger`/`Points_Operations_Log`; дополнительно централизован `ImportsService`: логика создания/обновления импортных начислений перенесена в `PointsService` (новый метод `upsert_import_points_entry`), `imports.py` больше не пишет в финансовые таблицы напрямую; теперь `orders` и `imports` используют единый сервис баллов
- **Проверка:** `docker compose run --rm backend python -m compileall app/services/points.py app/services/orders.py app/services/imports.py`; `docker compose run --rm backend python -m compileall app`
- **Блокеры:** нет
- **Следующий шаг:** Э7.1 — Materials + Content

### Запись: 2026-06-21 (Э6 — rewards + orders полностью)
- **Чат:** Э6 — `/api/rewards`, `/api/orders`
- **Сделано:** доработан `/api/rewards`: CRUD каталога + защита системного СБП-приза и новый endpoint `PUT /api/rewards/{id}/visibility` для публикации/скрытия СБП-приза по списку дистрибьюторов; добавлены модель и миграция `prize_distributors` (`0009_migration_h`); полностью реализован `/api/orders`: создание сертификатных и СБП-заявок, ветка `verification_pending`, `POST /api/orders/confirm-code` (отправка/подтверждение кода), `GET /api/orders/my`, `GET /api/orders/all`, `PUT /api/orders/{id}/status`, `PUT /api/orders/{id}/fulfill`; добавлены проверки ИНН/КНД/самозанятости, снимки полей заявки, резерв баллов, возврат при `rejected`, перевод в `redeemed` при `fulfilled`; подключены роутеры `orders` и `rewards` в `main.py`; обновлены требования в ТЗ по endpoint видимости СБП-приза
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app`; `docker compose run --rm backend python -m compileall app/api/orders.py app/services/orders.py app/api/rewards.py app/services/rewards.py` (миграция `0009` применена, файлы компилируются)
- **Блокеры:** нет
- **Следующий шаг:** Э7.1 — Materials + Content

### Запись: 2026-06-21 (Э5.2 — импорт продаж)
- **Чат:** Э5.2 — `POST /api/import/sales`, `GET /api/import/template-sales`
- **Сделано:** добавлен шаблон `template-sales` и загрузка продаж из `.xlsx`; реализована привязка начислений по кодам `ТП`/`СВ` к пользователям и проверка соответствия дистрибьютору; для каждой строки создаются отдельные начисления ТП и СВ (если баллы > 0); добавлена идемпотентность по ключу строки импорта (повтор файла не дублирует баллы), а при изменении сумм выполняется обновление начисления с записью в `Points_Overwritten_Log`; ошибки строк пишутся в `Import_Error_Log`; добавлена подготовка под Celery: `POST /api/import/sales?use_celery=true` ставит импорт в очередь, создана задача `app.tasks.imports.import_sales_task`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app` (компилируются `app/api/imports.py`, `app/services/imports.py`, `app/tasks/imports.py`)
- **Блокеры:** нет
- **Следующий шаг:** Э6.1 — `/api/rewards` (каталог призов)

### Запись: 2026-06-21 (Э6.1 — каталог призов)
- **Чат:** Э6.1 — `GET/POST/PUT/DELETE /api/rewards`
- **Сделано:** добавлены `app/api/rewards.py` и `app/services/rewards.py`; реализован CRUD каталога призов: получение списка с пагинацией, создание, редактирование и скрытие карточек; добавлена защита системного СБП-приза «Платеж на карту банка» (нельзя скрыть/удалить и нельзя менять тип); для обычных призов оставлен тип `certificate`; подключён роутер в `app/main.py`
- **Проверка:** `docker compose build backend`; `docker compose run --rm backend python -m compileall app` (компилируются `app/api/rewards.py`, `app/services/rewards.py`, `app/main.py`)
- **Блокеры:** нет
- **Следующий шаг:** Э6.2 — заявка на сертификат

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
