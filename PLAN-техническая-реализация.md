# Технический план реализации — промо-портал «Чистая Линия»

**Главный источник требований:** `ТЗ оптимизированное для ИИ-разработчика.md`  
**Детали и история:** `ТЗ Курсор чат 2.md`  
**Визуальный референс:** `reference_site фронери/_cursor_reference_*.md` (только UI, не бизнес-логика)

**Статус:** в разработке (этапы 0–7 ✅, этап 8 🔄)  
**Домен:** `plombirclub.ru` | **Стек:** FastAPI + PostgreSQL + Redis/Celery + HTML/CSS/JS + Docker Compose  
**Объём:** полноценный сайт по ТЗ (раздел 20 приёмки), **31 подэтап = 31 чат Agent**

---

## Правило чатов

| Правило | Значение |
|---------|----------|
| 1 подэтап | 1 новый чат Agent |
| В начале чата | Читать `PROGRESS.md` + раздел текущего подэтапа в этом PLAN |
| ТЗ целиком | Только если не хватает деталей для текущего подэтапа |
| Режим Plan | Только планирование, **без кода** |
| Agent+ | Тяжёлая модель — см. таблицу режимов ниже |

### Режимы по подэтапам

| Режим | Подэтапы |
|-------|----------|
| **Agent** | Э0, Э1.3–1.5, Э3, Э4.2, Э7.1–7.2, Э8.1–8.2, Э8.4a–8.5, Э9.1–9.4, Э10, Э11, Э12.2 |
| **Agent+** | Э1.1–1.2, Э1.6, Э2, Э4.1, Э5.1–5.2, Э6, Э7.3, Э8.3, Э12.1 |

---

## 1. Архитектура

```
plombirclub.ru (HTTPS)
        │
    nginx ──► frontend (статика HTML/CSS/JS)
        │
        └──► backend (FastAPI /api/*)
                  │
         ┌────────┼────────┐
         ▼        ▼        ▼
    postgres   redis   ./uploads
                  │
            worker + scheduler (Celery)
```

| Компонент | Технология |
|-----------|------------|
| API | FastAPI, Python 3.11+ |
| БД | PostgreSQL 16, SQLAlchemy async, Alembic |
| Очередь | Redis + Celery |
| Auth | JWT в HTTP-only cookies, bcrypt cost 12 |
| Frontend | HTML + CSS + JS (отдельные файлы), Mobile-first. **Tailwind не использовать** |
| Деплой | Docker Compose, Timeweb VPS |

**Структура репозитория:**

```
/backend/app/{api,models,services,tasks,middleware,core}
/frontend/{pages,assets,css,js,components}
/uploads
/scripts/{backup.sh,deploy.sh,seed.sh}
/docker/{nginx,postgres}
docker-compose.yml
.env.example
```

---

## Рекомендуемый календарь (5–6 дней)

| День | Подэтапы | Фокус |
|------|----------|-------|
| 1 | Э0, Э1.1–1.6 | Каркас + вся БД |
| 2 | Э2, Э3, Э4.1, Э4.2, Э5.1 | Вход, профиль, баллы, задания, импорт людей |
| 3 | Э5.2, Э6, Э7.1, Э7.2, Э7.3 | Импорт продаж, заявки, backend-контент |
| 4 | Э8.1, Э8.2, Э8.3, Э8.4a | ЛК: вход, профиль, каталог, FAQ |
| 5 | Э8.4b, Э8.5, Э9.1, Э9.2 | ЛК остальное + половина админки |
| 6 | Э9.3, Э9.4, Э10, Э11, Э12.1, Э12.2 | Админка, фон, деплой, приёмка |

---

## Этап 0. Каркас проекта (1 чат)

**Цель:** пустой, но запускаемый проект.

| # | Задача | Результат |
|---|--------|-----------|
| 0.1 | `docker-compose.yml` — 7 сервисов | `docker compose up` без ошибок |
| 0.2 | `.env.example` — все переменные | Шаблон без секретов в git |
| 0.3 | Backend: FastAPI, `/api/health`, формат ошибок JSON | API отвечает 200 |
| 0.4 | Alembic: подключение к PostgreSQL | `alembic upgrade head` работает |
| 0.5 | Frontend: `index.html`, `styles.css`, CSS-переменные палитры ТЗ | `--color-primary` и др. |
| 0.6 | Nginx: `/api` → backend, статика → frontend | Один порт локально |

**Критерий:** локально поднимается весь стек, health-check проходит.

---

## Этап 1. База данных (6 чатов: Э1.1–1.6)

**Цель:** полная схема PostgreSQL (раздел 14 ТЗ).

### Э1.1 — Миграция A (Agent+)
- `Distributors`, `Users`, `Admin_Settings`

### Э1.2 — Миграция B (Agent+)
- `Points_Ledger`, `Points_Operations_Log`, `points_overwritten_log`
- `Prizes` + seed системного приза «Платеж на карту банка» (`type=money`, `is_system=true`)

### Э1.3 — Миграция C (Agent)
- `Requests`, `Verification_Codes`

### Э1.4 — Миграция D (Agent)
- `Tasks`, `Task_Distributors`, `User_Tasks_Acceptance`
- `Materials`, `User_Materials_Progress`
- `Products` (+ связь с дистрибьюторами)
- `Parser_Config`

### Э1.5 — Миграция E (Agent)
- `Notification_Templates`, `Notifications`
- `Admin_Logs`, `System_Logs`, `User_Actions_Logs`, `Import_Error_Log`
- `Deleted_Users_Archive`

### Э1.6 — Правила БД + seed (Agent+)
- UUID PK, `created_at` / `updated_at`
- Явные `ON DELETE` / `ON UPDATE` (раздел 14.11 ТЗ)
- **Без CASCADE** на финансовую историю и заявки
- UNIQUE: `(user_id, material_id)`, `(user_id, task_id)`, `(admin_id, setting_key)`
- Seed: 1 admin, 2 дистрибьютора, системный приз СБП, 8 шаблонов уведомлений, пустые контакты поддержки
- **Миграция `0010` (доп.):** `tasks.cover_image_path`, демо-задания, дистрибьютор для `testuser@plombirclub.ru`

**Критерий этапа 1:** миграции + seed на чистой БД.

---

## Этап 2. Backend — auth (1 чат, Agent+)

- JWT, HTTP-only cookies, CSRF, rate limiting (Redis)
- Middleware: `require_auth`, `require_admin`, `require_registration_complete`
- `/api/auth`: login, change_password, sms/email codes, accept_agreements, logout, forgot-password
- `is_registration_complete = phone_verified AND temporary_password_changed AND agreements_accepted`

**Критерий:** первый вход end-to-end через API.

---

## Этап 3. Backend — пользователи и профиль (1 чат, Agent)

- `/api/users`: profile, upload-document, однократное сохранение ИНН/КНД
- Админ: verify-inn, verify-self-employed, documents, deactivate, DELETE (ФЗ-152)
- `/api/distributors`: CRUD

---

## Этап 4. Backend — баллы и задания (2 чата)

### Э4.1 — Баллы (Agent+)
- `PointsService`: ACID + `SELECT FOR UPDATE`, split записей, deadlock retry
- `/api/points`: balance, history, consent, activate

### Э4.2 — Задания (Agent)
- `/api/tasks`: `GET /` (список; без `period_month` = все периоды), `GET /current`, `GET /{id}`, `POST /create`, `POST /create-with-cover` (обложка JPG/PNG), `POST /{id}/accept`
- Поле `cover_image_path` в `Tasks`; файлы в `/uploads/`, nginx раздаёт статику
- **Совместимость:** старые endpoints не удалены; импорт продаж и активация баллов используют одно задание на период (как раньше)

---

## Этап 5. Импорт Excel (2 чата)

### Э5.1 — Импорт пользователей (Agent+)
- `POST /api/import/users` — upsert по email, временный пароль, email
- `GET /template-users` — шаблон xlsx

### Э5.2 — Импорт продаж (Agent+)
- `POST /api/import/sales` — привязка по Код ТП/СВ, идемпотентность, две записи на строку
- `GET /template-sales`, Celery для больших файлов

---

## Этап 6. Backend — заявки и каталог призов (1 чат, Agent+)

- `/api/rewards` — CRUD, защита системного СБП-приза
- `/api/orders` — сертификат и СБП, `verification_pending`, confirm-code, fulfill, возврат баллов при rejected
- Snapshot полей заявки на момент создания

---

## Этап 7. Backend — контент, аналитика, парсер (3 чата)

### Э7.1 — Материалы и контент (Agent)
- `/api/materials` — прогресс изучения
- `/api/content` — FAQ, инструкции, контакты поддержки

### Э7.2 — Аналитика и уведомления (Agent)
- `/api/analytics`, `/api/reports` (CRM layout)
- `/api/notifications` + шаблоны

### Э7.3 — Парсер (Agent+)
- `/api/parser` — omoloko.ru, защита ручных правок

---

## Этап 8. Frontend — личный кабинет (6 чатов)

**Референс:** `reference_site фронери`. **Не делать:** «Рейтинг участников», тексты FRONERI.

Общие JS: `api.js`, `auth.js`, `layout.js`, `modals.js`.  
CSS: Mobile-first, 320–1920 px, touch 44×44 px.

### Э8.1 — Каркас и вход (Agent)
- Layout: шапка, меню
- login, forgot-password, first-login

### Э8.2 — Профиль и заявки (Agent)
- profile, my-orders

### Э8.3 — Каталог призов (Agent+)
- catalog + модалки «Получить» и «Получить по СБП»

### Э8.4a — Задания, FAQ, инструкции, уведомления (Agent) ✅
- **Условия акции** (`/pages/news.html`): сетка карточек как Froneri (обложка, заголовок, период, «Читать», дата); детальная страница; фильтр «Период» с **«Все периоды»** по умолчанию; API `GET /api/tasks`, `GET /api/tasks/{id}`
- FAQ, instructions, notifications — отдельные страницы; счётчик непрочитанных уведомлений в меню
- **Не в scope Э8.4a:** счётчик на пункте «Условия акции» в меню (как на Froneri) — опционально позже

### Э8.4b — Аналитика, материалы, продукция (Agent)
- `/pages/analytics.html` — `GET /api/analytics/*` (сводка, экспорт)
- `/pages/materials.html` — список, прогресс «Не начат / Начат / Изучен», счётчик изученных, просмотр PDF/видео
- `/pages/products.html` — каталог продукции ЧИСТАЯ ЛИНИЯ, карточки, фильтры по дистрибьютору
- Референс: `reference_site фронери/_cursor_reference_*.md` (визуал)

### Э8.5 — Адаптив (Agent)
- Проверка 320–1920 px, кнопки 44×44

---

## Этап 9. Frontend — админ-панель (4 чата)

Стиль: табличный, `/admin/*`, без копирования Froneri 1:1.

### Э9.1 — Ядро (Agent)
- Users (включая **назначение дистрибьютора** — без него не работают задания, импорт продаж, каталог), Import, Points, Orders

### Э9.2 — Призы и контент-управление (Agent)
- Prizes, **Tasks** (`POST /create-with-cover`, HTML-контент, обложка; при необходимости админ-список всех заданий), Materials

### Э9.3 — Редакторы контента (Agent)
- FAQ, Instructions, Support, Products

### Э9.4 — Отчёты и логи (Agent)
- Reports (CRM), Logs, Notifications

---

## Этап 10. Фоновые задачи (1 чат, Agent)

| Задача | Расписание |
|--------|------------|
| check_points_deadlines | ежедневно 00:01 с 16 по 21 числокаждого месяца |
| backup_postgres | ежедневно 03:00, 7 копий |
| run_product_parser | еженедельно |
| expire_verification_codes | каждые 1–5 мин |
| import_excel_async, send_notification_batch | по событию |

---

## Этап 11. Деплой (1 чат, Agent + действия владельца)

- Timeweb VPS, Ubuntu 24.04, prod: 2 CPU / 4 GB / 40 GB
- DNS Beget: A → VPS
- Nginx + Let's Encrypt, `.env` только на сервере
- `scripts/deploy.sh`: backup → pull → build → migrate → health-check

---

## Этап 12. Тестирование и приёмка (2 чата)

### Э12.1 — Автотесты (Agent+)
- auth, points transactions, import idempotency, order status machine, **tasks list/detail/accept**

### Э12.2 — Приёмка (Agent + владелец)
- Ручная приёмка: раздел 20 ТЗ
- Тестовые данные: раздел 21 ТЗ
- Кроссбраузерность и мобильные

---

## Граф зависимостей

```
Э0 → Э1.1–1.6 → Э2 → Э3 → Э4.1 → Э4.2 → Э5.1 → Э5.2 → Э6
                                              ↓
Э2 → Э7.1 → Э7.2 → Э7.3
Э2 → Э8.1 → Э8.2 → Э8.3 → Э8.4a → Э8.4b → Э8.5
Э6 + Э7 → Э9.1 → Э9.2 → Э9.3 → Э9.4 → Э10 → Э11 → Э12.1 → Э12.2
```

---

## Чеклист полноценного сайта (раздел 20 ТЗ)

- Первый вход, блокировка ЛК до регистрации
- Импорт users + sales, идемпотентность
- Баллы: баланс, история, активация, просрочка (Э10)
- Каталог как Froneri, сертификаты и СБП, «Мои заявки»
- **Условия акции:** сетка карточек, «Все периоды», «Читать», принятие участия
- Профиль: ИНН/КНД один раз, верификация
- Материалы: не начат / начат / изучен, счётчик
- FAQ, инструкции, контакты из админки
- Продукция: ручное + парсер omoloko.ru
- Аналитика, уведомления, CRM-отчёты
- Админка: все экраны раздела 16 ТЗ
- Дизайн: ЧИСТАЯ ЛИНИЯ, палитра, 320–1920 px
- Деплой plombirclub.ru + приёмка

---

## Важные ограничения из ТЗ

- Раздел «Рейтинг участников» **не реализуется**
- Бренд FRONERI → «Чистая Линия» в UI
- Контакты поддержки **только из админки**, не в коде
- Баллы **только через Excel**, не автоматически
- Курс: 1 балл = 1 рубль, номинал 1000–10000, шаг 1000
- Frontend: HTML + CSS + JS по отдельным файлам (не Tailwind)
