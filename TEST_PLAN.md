# Test Plan — ComNet

Документ покриття: що тестується автоматично, що — лише мануально, де прогалини. Оновлювати при додаванні фічі.

**Остання актуалізація:** 2026-05-23

---

## Як запускати

### Backend pure-logic (pytest)
```bash
docker compose exec backend pytest -v
# або локально (треба pytest + deps):
cd backend && pytest tests/ -v
```

### Інтеграційні + UI smoke (Playwright)
```bash
docker compose --profile test up --build playwright --abort-on-container-exit
# HTML-репорт: tests/e2e/results/index.html
```
**Важливо:** обов'язково з `--build`, інакше Docker візьме закешований образ з попередніми тестами і зміни в `.spec.js` НЕ підхопляться.

Підставка облікового запису: `TEST_USER`/`TEST_PASS` беруться з `.env` (default `admin`/`admin123`).

---

## Покриття автоматичними тестами

| Категорія | Розташування | К-сть | DB? |
|-----------|--------------|-------|-----|
| Pure-logic (UA пропис, XLSX shift) | `backend/tests/` | 31 | ні |
| Інтеграційні + UI smoke (Playwright) | `tests/e2e/tests/` | 14 (13✓ + 1 skip) | так — dev-DB через `--profile test` |

### `tests/e2e/tests/api_documents.spec.js` — інтеграційні (HTTP)

API-тести через Playwright `request` (без браузера). Покривають критичні гарантії snapshot-архітектури — це **протекція перед рефакторингом** `documents.py`.

| Тест | Що перевіряє |
|------|--------------|
| `sign creates movements; unsign removes them` | POST /sign → status=signed + N movements; POST /unsign → status=draft + movements deleted |
| `signed doc snap immune to person edits (TZ §8.4)` | Підписаний доc → мутувати Person + Item напряму через /api/settings/persons → snap фрозен, не змінюється |
| `auto-numbering generates sequential by prefix` | Док з порожнім `doc_number` отримує `prefix + (MAX+1)`; явний номер не перезаписується; наступний авто = MAX+1 |
| `export-xlsx returns 200 with spreadsheet body` | Відповідь 200, `content-type: spreadsheetml`, body починається з ZIP magic `PK`. Skipped якщо `unit_settings.name` порожній |

### `tests/e2e/tests/auth/documents/items/settings.spec.js` — UI smoke (Playwright + browser)

| Spec | Тести |
|------|-------|
| `auth.spec.js` | login+logout, redirect не-авторизованих |
| `items.spec.js` | сторінка вантажиться, пошук не крешить |
| `documents.spec.js` | список вантажиться, створення Надходження, створення Переміщення (накладна_25), видалення чернетки |
| `settings.spec.js` | таби видимі (Підрозділ/Особи/Типи/Служби), додавання особи, редагування особи |

### `tests/e2e/tests/helpers/`

- `login.js` — спільний `uiLogin(page)` + `loginApi(request)` (повертає `request.newContext` з Bearer-токеном)
- `seed.js` — `seedNakladnaContext(api, label)` створює унікально-iменовані opType (з `number_prefix`), service, sender, receiver, fin, item; повертає масив `cleanup` шляхів для безпечного видалення в afterEach

### `backend/tests/test_uk_num2words.py` (24 тести)
UA-пропис для XLSX-експорту накладної (TZ §7.5–§7.6, §8.7, §8.9).

| Тест | Що перевіряє |
|------|--------------|
| `test_qty_to_words[N]` × 9 | Кількість прописом, фемінін: 0→«нуль», 1→«одна», 2→«дві», 5→«п'ять», 7→«сім», 11/21/100/1000 |
| `test_qty_to_words_no_latin` | Жодної латинки в українських словах |
| `test_amount_tz_reference` | Еталон TZ: `76453.20 → "сімдесят шість тисяч чотириста п'ятдесят три гривні 20 копійок"` |
| `test_amount_cases[X]` × 11 | Узгодження «гривня/гривні/гривень» + «копійка/копійки/копійок» для 0/1/2/5/21/100/1000 + копійки 01/50/11 |
| `test_amount_no_latin_contamination` | Жодної латинки в сумі прописом |
| `test_amount_rounding_half_up` | `0.005 → "01 копійка"` (ROUND_HALF_UP) |

### `backend/tests/test_invoice_export.py` (7 тестів)
Логіка зсуву рядків у XLSX-шаблоні (TZ §8.1–§8.3, §9).

| Тест | Що перевіряє |
|------|--------------|
| `test_template_baseline` | «Всього» @ A25, merge A41:C43 (fin-post), print_area A1:J44 |
| `test_no_defined_names_leak` | Шаблон без VBA-defined-names (інакше Excel: «We found a problem») |
| `test_n_equals_5_no_shift` | N=5 → δ=0, layout не змінюється |
| `test_n_equals_12_inserts_7_rows` | N=12 → +7 рядків, «Всього» @ A32, fin merge A48:C50 |
| `test_n_equals_1_deletes_4_rows` | N=1 → −4 рядки, «Всього» @ A21, fin merge A37:C39 |
| `test_inserted_rows_inherit_item_row_style` | Border-quirks col A (no left) + col C (no bottom) зберігаються |
| `test_template_last_row_constant` | `TEMPLATE_LAST_ROW=44`, `TEMPLATE_SLOTS=5` синхронні з шаблоном |

---

## Покриття вручну (smoke checklists)

### 🔐 Авторизація — `/login`
**API:** `POST /api/auth/login`, `GET /api/auth/me`

- [ ] Login `admin` / `admin123` → редирект на `/items`
- [ ] Невірний пароль → toast/повідомлення про помилку, юзер не логіниться
- [ ] Закінчення токену або 401 з захищеного endpoint → редирект на `/login`
- [ ] Logout (якщо є) → токен видалений, доступ заблоковано

**Прогалини в автотестах:** немає інтеграційного тесту login flow.

---

### ⚙️ Налаштування — `/settings`
**API:** `/api/settings/unit`, `/op-types`, `/op-types-detail`, `/persons`, `/services`

**Tab «Підрозділ»:**
- [ ] Відкрити → бачимо поточні `name/short_name/edrpou/location`
- [ ] Редагувати → зберегти → refresh → значення зберіглись

**Tab «Типи операцій»:**
- [ ] Додати тип «видача» з `number_prefix = "85/635-"` → бачимо в списку з бейджем префіксу
- [ ] Редагувати тип → міняти name та `number_prefix` → зберегти
- [ ] Додати підтип (op_type_detail) до існуючого
- [ ] Видалити тип → CASCADE видаляє підтипи

**Tab «Особи»:**
- [ ] Додати особу з усіма полями (включно з родовими відмінками)
- [ ] Toggle `is_active=false` → особа НЕ зникає з усіх існуючих документів, але не доступна в нових select-ах
- [ ] Видалити → не видаляє пов'язані документи (FK SET NULL)

**Tab «Служби»:**
- [ ] CRUD: name + chief_name + chief_position

**Прогалини:** жодного API-теста для CRUD будь-якого з ресурсів.

---

### 📦 Довідник майна — `/items`
**API:** `GET /api/items`, `POST/PUT/DELETE /api/items/{id}`

- [ ] Завантажується список; сортування по `number` **натуральне** (1, 2, …, 9, 10, 11, … 100 — а не «1, 10, 100, 11»)
- [ ] Таби «Всі / Серійні / Несерійні» фільтрують
- [ ] Фільтр по `item_type` працює
- [ ] Пошук по name / number / serial_number — case-insensitive
- [ ] Колонки: № картки, Найменування, Тип, Серійний №, Категорія, Од., К-сть, Вартість, **Примітки** (новa), Дії
- [ ] Створити нове майно (серійне і несерійне) з документами (asset_documents)
- [ ] Редагувати → `_sync_documents` оновлює список документів коректно
- [ ] Видалити → FK у `movements` стає SET NULL (не блокує видалення)
- [ ] Картка майна (modal) показує всі поля + примітки
- [ ] Чек: волонтерське (is_official=false) → бейдж «волонтерське»

**Прогалини:** натурального сортування немає в тестах (можна додати pytest для `_natural_key`). _sync_documents не тестовано.

---

### 📋 Документи — `/documents`
**API:** `/api/documents`, `/sign`, `/unsign`, `/export/xlsx`

**Список:**
- [ ] Filter-таби «Всі / Надходження / Переміщення» — таб «Переміщення» ловить ОБА типи (`переміщення` + `накладна_25`)
- [ ] Сортування: спочатку DESC по `doc_date`, потім по id
- [ ] Бейдж типу: однаковий blue (`transfer`) для обох переміщень

**Створення нового:**
- [ ] Кнопка «Новий документ» → dropdown тільки 2 опції: «Надходження», «Переміщення»
- [ ] Створення → redirect на форму, дата = сьогодні, перші опції в усіх dropdown-ах автообрані

---

### 📝 Форма документа — `/documents/:id` (тип `накладна_25`)

**Реквізити:**
- [ ] Найменування / ЄДРПОУ / Місце складання — read-only з `unit_settings`
- [ ] Тип операції — dropdown усіх `op_types`; зміна → змінюється плейсхолдер «авто: <prefix><N>»
- [ ] Номер: якщо порожній і у op_type є `number_prefix` → backend генерує `prefix + (MAX+1)`
- [ ] Дата — за замовч сьогодні; «Дійсна до» = `+3 дні` (CALC, read-only)
- [ ] Підстава — free text

**Сторони (3 колонки):**
- [ ] Звідки/Куди — dropdown показує **тільки `p.unit`** (фільтр на персон з непорожнім unit, сортування по unit)
- [ ] Передає / Приймає / Керівник — read-only auto-fill з обраної персони / служби
- [ ] **Snap invariance:** після підпису, якщо в довіднику змінити ПІБ/посаду, на формі і в XLSX лишається старе значення

**Фінслужба:**
- [ ] Dropdown посадової особи → auto-fill posada + ПІБ

**Позиції:**
- [ ] «+ Рядок» додає порожній
- [ ] Autocomplete: focus без тексту → перші N (через 30 — без капу, з max-height scroll); ввід → фільтр; стрілки + Enter
- [ ] Dropdown autocomplete не обрізається таблицею (teleport до body)
- [ ] Вибір майна → автозаповнення name/code/unit/category/price + qty=qty_received=1 + notes=serial_number
- [ ] Зміна позиції → notes ПЕРЕзаписуються новим serial; quantity лишається що ввів юзер
- [ ] Видалити рядок «×» працює
- [ ] Сума у футері: total qty + total amount

**Пропис (auto):**
- [ ] Після save: «Всього передано <слово> одиниць», «На суму <гривні прописом>»

**Підпис:**
- [ ] Кнопка «Підписати» у draft — клік → save → sign → status=signed, всі поля read-only
- [ ] При signed: snap-поля показуються з extra_data (НЕ live FK)
- [ ] Кнопка «Зняти підпис» → confirm → movements видалено, status=draft
- [ ] При підписі без обов'язкових полів → червоний блок з missing полями

**XLSX:**
- [ ] Завантажується файл з ім'ям `накладна_<number>.xlsx` (UTF-8 у Content-Disposition)
- [ ] Layout відповідає шаблону (рядки 1-44 для N=5; динаміка для інших N)
- [ ] Excel відкриває **без помилок** (немає «We found a problem»)
- [ ] Старі накладні_25 без snap → 400 «потрібна snap» (C-a)

**Прогалини:**
- Жодного API-теста на create/update/sign/unsign flow
- Жодного теста snap-invariance (TZ §8.4-8.5)
- Жодного теста auto-нумерації
- Frontend без автотестів

---

### 📝 Форма документа — `/documents/:id` (типи `надходження`/legacy `переміщення`)
Стара мінімальна форма (тільки number/date/from/to/basis + items).
- [ ] Існуючий документ цього типу відкривається з простою формою
- [ ] Save працює як раніше

---

### 🔄 Рух (переміщення) — `/movements`
**API:** `/api/movements`

- [ ] Завантажується список movements (DESC по `entry_date`)
- [ ] Фільтри: дата від/до, підрозділ, особа, тип операції
- [ ] Сортування колонок
- [ ] CRUD: створення + редагування + видалення (не залежать від документів)
- [ ] Підказка: коли рядок створений з підпису документа — `document_id` заповнений

**Прогалини:** немає API-тестів.

---

### 📊 Залишки — `/residues`
Поки що `PlaceholderPage`. (Фаза 4 — TODO.)

### 📈 Звіти — `/reports`
Поки що `PlaceholderPage`. (Фаза 5 — TODO.)

---

## Прогалини / куди йти далі (priority)

### 🔴 Високий
1. ~~Snap invariance integration test~~ ✅ зроблено (`api_documents.spec.js`)
2. ~~Sign/unsign flow + movement creation~~ ✅ зроблено
3. ~~Auto-number generation~~ ✅ зроблено
4. **Settings CRUD smoke** — op_types/persons/services/unit базові API-тести. Існує UI smoke для додавання/редагування особи, але не охоплює inkop_types з `number_prefix`, services з chief_*, unit_settings.

### 🟡 Середній
5. Items: натуральне сортування `1, 2, ..., 10` (pytest для SQL CASE або Playwright API)
6. Documents: required fields validation для sign — assert 422 + missing list для накладна без doc_date
7. Items: `_sync_documents` поведінка при PUT з документами
8. **XLSX export** — наразі skip без `unit_settings.name`. Зробити seed unit_settings у beforeEach + cleanup
9. **Дублікат номера накладної** — POST з existing doc_number → response `warnings` непорожній

### 🟢 Низький
- Frontend unit-тести (Vitest)
- Тести `_natural_key` для items.number з мішаними значеннями ("K-1", "1A")

---

## Кандидати на cleanup (мертвий код)

Виявлено під час аудиту. Видаляти **тільки після** того, як буде хоч би smoke-API-тести (щоб видалення нічого не зламало).

### Безпечно видалити (підтверджено dead):
- `backend/app/routers/invoices.py` — не зареєстрований у `main.py`; імпортує `PrintDocument`/`PrintDocumentItem` з `models.py` — їх немає (видалені в міграції 003). Файл зламано, не використовується.
- `backend/app/schemas.py` — класи `InvoiceCreate`, `InvoiceRead`, `InvoiceUpdate`, `InvoiceListRead`, `InvoiceItemCreate`, `InvoiceItemRead`. Використовуються тільки в (мертвому) `invoices.py`.
- `frontend/src/pages/invoices/InvoicesPage.vue` — не в router-і.
- `frontend/src/pages/invoices/InvoiceFormPage.vue` — не в router-і.
- `frontend/src/pages/invoices/components/InvoicePrintView.vue` — import з `DocumentFormPage.vue` прибрано в рев'ю.

### Залишається (використовується):
- `frontend/src/pages/invoices/components/ItemAutocomplete.vue` — імпортується з `DocumentFormPage.vue`. Перемістити в `frontend/src/components/` (бо тепер не invoice-specific).
- `frontend/src/pages/invoices/components/PersonSelect.vue` — перевірити чи використовується.

### Кандидати на рефакторинг (не блокерно):
- **`backend/app/routers/documents.py` (~700 рядків)** — розщепити на:
  - `app/document_snapshot.py` (`_snap_nakladna`, `_next_doc_number`, `_calc_validity`)
  - `app/document_export.py` (вже частково винесено в `invoice_export.py` — допереніс `export_xlsx` функції)
  - роутер лишається тонкий — CRUD + sign/unsign
- **OpTypeDetail** — модель + ендпоінти не використовуються в новій формі накладної. Залишаються «на потім», але вирішити: видалити чи документувати use case.
- **Movement.op_type_detail_id** — те саме.

---

## Конвенції

- Тести pure-logic (без DB) → `tests/test_<module>.py`, без conftest
- Інтеграційні (з DB) → `tests/integration/test_<feature>.py` (TODO: setup `conftest.py` з SQLite/PostgreSQL fixture)
- Імена тестів: `test_<що_перевіряємо>` або `test_<feature>_<scenario>`
- Кожен PR що змінює API/UI повинен оновити цей файл (відмітити нові пункти / закрити чекбокси / додати в Gaps)
