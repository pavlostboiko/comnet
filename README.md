# ComNet

Веб-система обліку майна підрозділу: **FastAPI + PostgreSQL + Vue 3**, у Docker Compose.

Модель обліку (v2): **custody** (відповідальність складу, `custody_movements` між
`warehouses`) окремо від **assignment** (фізичне тримання особою — не рухає баланс).
Серійне майно — через `instances`; несерійне — кількість із рухів. **Документи**
(накладна/акт) — шар над рухами. Двохосьовий доступ: admin / служба / МВО-склад.

## Стек

- Backend: FastAPI 0.111 (Python 3.12), SQLAlchemy 2.0, Alembic, PostgreSQL 16.
- Frontend: Vue 3 + Vite, Nginx (проксить `/api` → backend).
- Тести: Playwright (e2e), pytest (чиста логіка).

---

## Розгортання на чистому сервері

Потрібні лише **Docker Engine + Docker Compose plugin** і **git** (Node/Python — у контейнерах).

```bash
# 1. Код
git clone <repo-url> /var/www/comnet     # або будь-яка тека, якою володіє юзер
cd /var/www/comnet
# якщо тека під root: sudo mkdir -p … && sudo chown -R $USER:$USER …

# 2. Конфіг (секрети; .env у .gitignore)
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
#   у .env заповни:
#   POSTGRES_PASSWORD — надійний;
#   DATABASE_URL — той самий пароль/юзер/БД, хост «postgres»:
#     postgresql://comnet:<пароль>@postgres:5432/comnet
#   SECRET_KEY — згенерований; FIRST_ADMIN_PASSWORD — пароль адміна;
#   FRONTEND_PORT — хост-порт (типово 3000);
#   VITE_BASE_URL — базовий шлях фронта (BUILD-TIME!): «/» у корені або «/comnet/» за проксі.

# 3. Білд і запуск (docker має працювати без sudo — юзер у групі `docker`)
docker compose up -d --build
#   backend на старті сам: alembic upgrade head (створить усі таблиці) + первинний admin.
#   Сервіс `playwright` не стартує (профіль test).

# 4. Перевірка
docker compose ps                                        # postgres/backend/frontend Up/healthy
docker compose logs backend | grep "Running upgrade"     # міграції пройшли
#   http://<сервер>:<FRONTEND_PORT> → логін admin / FIRST_ADMIN_PASSWORD
```

### Заливка даних (БД порожня)

UI → **Імпорт**, по черзі: **1. Каталог (Items)** → **2. Переміщення** → **3. Видачі**
(усі три — з файлів Excel; «Видачі» беруть особу з колонки «Де» файлу Items).

### Мережа / доступ

- Назовні достатньо відкрити лише **FRONTEND_PORT**; `backend`/`postgres` — внутрішні.
- Домен/HTTPS/підшлях — reverse-proxy (nginx/caddy/Tailscale serve) перед фронтом.
  За підшляхом `VITE_BASE_URL` має збігатися (інакше фронт не підтягне асети).

### Бекап / відновлення

```bash
docker compose exec -T postgres pg_dump -U comnet -d comnet -Fc > backup-$(date +%F).dump
docker compose exec -T postgres pg_restore -U comnet -d comnet --clean backup-YYYY-MM-DD.dump
```
Дані живуть у docker-томі `pgdata` (переживає рестарти).

---

## Локальна розробка

```bash
docker compose up -d --build backend frontend    # dev-стек
docker compose exec -T backend python -m pytest -q
scripts/e2e.sh                                    # e2e на ІЗОЛЬОВАНОМУ стеку (ефемерна БД)
scripts/e2e.sh --down
```

> ⚠️ E2E ганяти лише через `scripts/e2e.sh` (окремий Postgres, проєкт `comnet_test`) —
> НЕ по dev-стеку, щоб не чіпати реальні дані.

Поточний стан і план — див. `STATE.md` та `database_v2_plan.md`.
