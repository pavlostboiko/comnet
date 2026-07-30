# ComNet — Стан і що робити далі

**Стартова точка нової сесії.** Огляд: де ми, що зроблено, що далі.

**Оновлено:** 2026-07-30 · **HEAD:** `a53e2c1` (гілка `main`, запушено).
Ядро v2 у `main`. **Кожна зміна — через гілку → `merge --no-ff` у `main` → push.**

---

## ⚠️ Головне для нової сесії

- Робочий процес: гілка на кожну зміну → `merge --no-ff` у **`main`** ([[feedback_feature_branch]]).
- **E2E — лише на ізольованому стеку** `scripts/e2e.sh` (окремий Postgres у tmpfs, проєкт `comnet_test`). **НЕ ганяти по dev-стеку/dev-БД** ([[feedback_no_db_access]]).
- **НЕ звертатись напряму до dev/prod БД** користувача. Діагностика — код+тести. Міграції застосовуються при старті бекенда.
- На **питання** — спершу відповідь/пропозиція + дозвіл, потім код ([[feedback_answer_before_coding]]).
- Робота через **`tasks.md`** (по 1 задачі; у «Готово» — з коротким описом) ([[feedback_tasks_workflow]]).
- Прод — **новий сервер `jawa`** (Debian 13, системний nginx-проксі, HTTP поки; сабдомен). Деплой/ре-імпорт виконує КОРИСТУВАЧ (**ssh з агента не працює**). Деплой оновлень: `git pull` → `docker compose up -d --build` (міграції самі).

---

## Модель v2 (коротко)
- **Custody** (`custody_movements` між `warehouses`) — хто *відповідає* (склад).
- **Assignment** (`assignments` на `persons`) — хто *тримає*. Видача **не рухає** баланс складу.
- Двохосьовий доступ (служба × склад × admin); серійне → `instances`; несерійне → к-сть із рухів.
- **Документ** (`custody_documents`) — шар паперу над рухами (рухи проводяться одразу; **unsign НЕ видаляє рухи**).
- **облік/ндм** = `is_official`, властивість **картки** (nomenclature); успадковується рухами/екземплярами/видачами; **заморожена**, якщо по картці вже є рухи/видачі (інакше — можна змінити + каскад на екземпляри).

## v2-схема (міграції 012-025)
Ключові таблиці: `services, units(+is_external), groups, warehouses(service|unit), mvo, nomenclature(is_official,is_serialized,price), instances(serial_no,card_number,current_warehouse,is_official,note), custody_movements(type,qty,is_official,card_number,doc_number,document_id), assignments(warehouse,person,nom/instance,qty,issued/returned+returned_by), users(role,scope), persons(unit_id,callsign,group_id,ipn,position/rank), audit_log, custody_documents`.

**Нові міграції цієї сесії:**
- **023** `audit_log` — журнал усіх ORM-змін.
- **024** `mvo.kind` ('warehouse'|'fin'), `warehouse_id` nullable — глобальний фін-МВО.
- **025** drop `custody_documents.sender_id/receiver_id/fin_id` — підписанти тепер із журналу МВО.

## МВО (важливо — багато змінилось)
- Журнал `mvo`: `kind='warehouse'` (на склад служби/внутр.підрозділу; **не** зовнішній) або `kind='fin'` (**глобальна фінслужба**, 1 діюча, без складу, видима всім). Записи мають `from_date/to_date` (історичні).
- **Підписанти документа резолвляться з журналу за `doc_date`** (не FK): Здав=МВО from-складу, Прийняв=МВО to-складу, Фін=глоб.фін; приймання ззовні Здав=контрагент. При **підписанні** ПІБ+посада/звання **заморожуються текстом** у `extra_data` (snap) і друкуються — стара накладна стабільна, історичний резолв стабільний.
- Керування: Довідники → МВО (форма «Тип», пошуковий пікер особи, повне **редагування** особи/дат + **видалення**).
- «Очистити людей» **зберігає** осіб-МВО (∪ user-linked), щоб журнал не осипався.

## Backend роутери
`structure` (units/groups/warehouses/mvo +edit/delete +kind), `nomenclature` (+instances, note; is_official-lock+cascade; scope для service), `custody` (movements/balances/serial/where/totals/history + document batch + **DELETE movement=відкликати**), `custody_documents` (CRUD+sign/unsign+XLSX Дод.25+/receive +form «без документа»/НДМ), `assignments` (issue/return; **issue_row** shared; НДМ-видача зі служби будь-кому), `import_v2` (persons/items/movements/assignments/wipe/wipe-persons), **`audit`** (`GET /api/audit` +/meta).
Модулі: `custody_snapshot.py` (snap+`mvo_person_at`+`doc_sort_key`), `custody_export.py`, `audit.py` (after_flush-хук).

## Frontend (меню)
Майно · Залишки · Переміщення · Документи · Звіти · Довідники · Користувачі · Імпорт · **Журнал змін** (admin).
- **Майно** (`catalog`): фільтр служби+**облік/ндм** у шапці (для service-юзера дропдаун служб схований, бачить лише свою).
- **Залишки** (`stock`): кнопки-склади; фільтри стану + **облік/ндм**; «Прийняти майно» (форма накладна/акт/**без документа(НДМ)**, випадайка фільтрується за формою), «Додати переміщення» (пікер майна + **опц. видача особі** на рядок). **«+ Рух» прибрано.** «Історія» на всіх рядках (і несерійне). НДМ видається зі службового складу будь-кому.
- **Документи**: підписанти read-only (з журналу); чернетка — «+ додати позицію»; «Без документа» — «Відкликати рух».
- **Довідники → МВО**: Тип (Склад/Фінслужба загальна), пошуковий пікер, ✎/✕.
- **Імпорт**: **Люди** / 1.Каталог / 2.Переміщення / 3.Видачі + «Очистити інвентар» / «Очистити людей».
- **Журнал змін** (`audit/AuditPage`): фільтри сутність/дія/дата + diff.
Компоненти: `HistoryTimeline`, `NomenclatureModal` (+defaultOfficial), `ItemAutocomplete` (+placeholder).

## Імпорт (порядок: Люди → Каталог → Переміщення → Видачі)
1. **Люди** — ПІБ(одна колонка, пробіл)/ІПН/Позивний, за заголовками. Ключ ІПН: оновити/створити; ІПН у базі без рядка → деактивувати; без ІПН → пропуск. `search_name`=повний ПІБ.
2. **Каталог (Items)** — номенклатура + серійні екземпляри (не розміщує).
3. **Переміщення** — розставляє по складах; тип операції з кол.**Z**, форма з кол.**Y**; **МВО з кол.J(звідки)/K(куди)** → будує журнал МВО діапазонами (особи мають існувати). Серійне матчиться по картці; same-date розміщення детерміноване (`doc_sort_key`).
4. **Видачі** — з файлу Items, кол.**«Де»**=«<підрозділ> <Прізвище>»; **шукає існуючу особу** по прізвищу (не створює), проставляє підрозділ якщо порожній.

## Аудит-лог
`after_flush`-хук пише кожну ORM create/update/delete у `audit_log` (хто/коли/дія/сутність + diff полів); користувач із `session.info`. Bulk `.delete()` (wipe) не логується (свідомо). Сторінка «Журнал змін» (admin).

---

## Що лишилось (`tasks.md`)
**1** Користувачі-edit · **2** Служби-edit · **7** історія видач стійка до видалення особи (assignment.person_name snapshot + FK SET NULL + заборона видалення з активною видачею; міграція) · **9** № картки — текст? · **11** редагувати категорії · **12** список рухів у «Переміщення».

Прод: після повного налаштування — **дроп v1** (таблиці items/movements/documents/residues/splits/recipients + сторінки) окремою міграцією.

---

## Команди
```bash
docker compose up -d --build backend frontend      # dev-стек
scripts/e2e.sh                                      # вся e2e (герметично, ефемерна БД)
scripts/e2e.sh --keep tests/api_x.spec.js          # швидко
scripts/e2e.sh --down                              # прибрати тест-стек
docker compose exec -T backend python -m pytest -q # чиста логіка
# gated деструктивні (wipe): додати -e RUN_WIPE_TEST=1 у прямому `docker compose run playwright`
```

## Правила
Гілка→merge у `main` ([[feedback_feature_branch]]); тест на зміну ([[feedback_tests_per_change]]); e2e на ізол.стеку, не чіпати dev-БД ([[feedback_no_db_access]]); на питання — відповідь+дозвіл ([[feedback_answer_before_coding]]); робота через `tasks.md` ([[feedback_tasks_workflow]]); лише горизонтальні tabs ([[feedback_no_sidebar]]). Деталі — `tasks.md` («Готово» 10-27), `database_v2_plan.md`.
