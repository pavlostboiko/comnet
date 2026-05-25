# Стек технологій — ComNet

Система обліку військового майна підрозділу. Веб-додаток (SPA + REST API),
розгортається через Docker Compose.

**Остання актуалізація:** 2026-05-25

---

## Backend (Python)

| Технологія | Версія | Призначення |
|------------|--------|-------------|
| **Python** | 3.12 | Базова мова |
| **FastAPI** | 0.111.0 | Web-framework, REST API |
| **Uvicorn** | 0.29.0 | ASGI-сервер |
| **SQLAlchemy** | 2.0.30 | ORM (synchronous) |
| **PostgreSQL** | 16 (alpine) | СУБД |
| **psycopg2-binary** | 2.9.9 | PostgreSQL-драйвер |
| **Alembic** | 1.13.1 | Версіонування схеми БД (міграції) |
| **Pydantic / pydantic-settings** | 2.2.1 | Валідація схем + `.env`-конфіг |
| **python-jose[cryptography]** | 3.3.0 | JWT-токени |
| **passlib + bcrypt** | 1.7.4 + 4.0.1 (pinned) | Хешування паролів |
| **python-multipart** | 0.0.9 | Парсинг form-data (login) |
| **python-dotenv** | 1.0.1 | Завантаження `.env` |
| **openpyxl** | 3.1.2 | Генерація XLSX (Додаток 25) |
| **num2words** | 0.5.13 | Числа прописом українською |
| **pytest** | 8.2.0 | Юніт-тести |

> **Pin:** `bcrypt==4.0.1` обов'язково — `passlib 1.7.4` несумісний з `bcrypt ≥ 5.x`.

---

## Frontend (Vue 3 SPA)

| Технологія | Версія | Призначення |
|------------|--------|-------------|
| **Node.js** | 20-alpine | Build runtime |
| **Vue.js** | 3.4.27 | UI-фреймворк (Composition API, `<script setup>`) |
| **Vue Router** | 4.3.2 | Маршрутизація, history mode |
| **Pinia** | 2.1.7 | Стан (auth store) |
| **Axios** | 1.7.2 | HTTP-клієнт + JWT interceptor |
| **Vite** | 5.2.11 | Bundler / dev server |
| **@vitejs/plugin-vue** | 5.0.4 | Vue SFC support |
| **Nginx** | alpine | Прод-сервер для збірки + reverse proxy `/api/` → backend |
| **DM Sans + DM Mono** | — | Шрифти (Google Fonts) |

---

## Тестування

| Технологія | Версія | Призначення |
|------------|--------|-------------|
| **pytest** | 8.2.0 | Pure-logic тести (UA пропис, openpyxl shifts) — 31 тест |
| **Playwright** | 1.44.0 | Інтеграційні API + UI smoke тести — 17 (Chromium headless) |
| Playwright `request` context | — | API-only тести (без браузера) |

Деталі покриття + мануальні чеклисти — у [TEST_PLAN.md](TEST_PLAN.md).

---

## Інфраструктура / DevOps

| Технологія | Призначення |
|------------|-------------|
| **Docker** + **Docker Compose** | Контейнеризація 4 сервісів (postgres, backend, frontend, playwright) |
| **GitHub Actions** (`.github/workflows/tests.yml`) | CI: pytest + Playwright на кожен push/PR |
| **Tailscale** | Тунель до прод-сервера `thinkcentre.barracuda-lenok.ts.net` |

---

## Документація

| Файл | Зміст | Гілка репо |
|------|-------|-----------|
| `ПЛАН_ПРОЄКТУ.md` | Огляд, фази, дизайн-система | local (gitignored) |
| `СХЕМА_БД.md` | Повна схема PostgreSQL, snap-поля, міграції | local (gitignored) |
| `API.md` | REST endpoints, payload-shape, обов'язкові поля | local (gitignored) |
| `TEST_PLAN.md` | Покриття + мануальні чеклисти + cleanup-кандидати | committed |
| `TECH_STACK.md` | Цей файл | committed |
| `TZ_nakladna_full.md` | Технічне завдання на накладну Дод. 25 | committed |
| `CLAUDE.md` | Coding standards, workflow rules | committed |

---

## Архітектурні принципи

- **Snapshot pattern** — підписані документи фрозені від змін у довідниках (TZ §1, §8.4)
- **JWT Bearer auth** на всіх API endpoints
- **Двоосьова модель типу документа**: `operation` × `form` (екстенсивно для нових форм)
- **Тонкий роутер + витягнуті модулі:**
  - `backend/app/routers/documents.py` — HTTP layer (CRUD, sign/unsign)
  - `backend/app/document_snapshot.py` — snap-логіка, auto-numbering
  - `backend/app/document_export.py` — XLSX-рендер (читає лише snap)
  - `backend/app/invoice_export.py` — openpyxl row-shift (pure logic)
  - `backend/app/uk_num2words.py` — українські числівники
- **SPA + REST** — frontend і backend через `/api/` префікс, проксі через nginx

---

## Зовнішні шаблони / стандарти

- **Додаток 25** — офіційний XLSX-шаблон військової накладної (`backend/app/nakladna_template.xlsx`)
- **Інструкція з обліку військового майна у ЗСУ** (TZ-референс — `TZ_nakladna_full.md`)
