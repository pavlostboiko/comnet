# Система обліку майна — технічне завдання

Версія 1.0. Мінімальна робоча версія (MVP).

---

## 1. Загальна модель

Система веде облік майна на **двох незалежних шарах**:

| Шар | Таблиця | Що описує | Хто веде |
|---|---|---|---|
| **Custody** (подотчіт) | `movements` | Формальна передача відповідальності між обліковими точками: склад служби → склад підрозділу | Працівник служби |
| **Assignment** (фізичне тримання) | `assignments` | Хто з особового складу фактично тримає майно, в межах подотчіту МВО | МВО |

**Ключовий принцип:** видача майна бійцю **не знімає майно з подотчіту МВО**. Воно лишається на балансі складу підрозділу; змінюється лише те, хто фізично його тримає. Тому видача бійцю — це запис в `assignments`, а не рух в `movements`.

Наслідок: боєць **не є** обліковою точкою. Обліковими точками (`warehouses`) є тільки склади служб і склади підрозділів.

### Дві гілки обліку номенклатури

| | Несерійне (`is_serialized = false`) | Серійне (`is_serialized = true`) |
|---|---|---|
| Одиниця обліку | кількість | конкретний екземпляр |
| Де живе | `quantity` в рухах | окремий запис в `instances` |
| Залишок | сума рухів (`balances`) | фільтр `instances` по `current_warehouse` |
| Кількість у русі | будь-яка | завжди 1 |
| Приклад | бушлат, ЗІП | АК-74, радіостанція |

---

## 2. Схема таблиць

### 2.1 `services` — служби

Довідник служб (РАО, речова, зв'язку тощо).

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | Внутрішній ідентифікатор |
| `name` | text | так | Назва служби |
| `code` | text | ні | Короткий код / абревіатура |

---

### 2.2 `units` — підрозділи

Довідник підрозділів. Структура **плоска** — ієрархії немає (свідоме рішення: спрощує правила доступу до прямого порівняння).

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `name` | text | так | Назва підрозділу |
| `code` | text | ні | Короткий код |

---

### 2.3 `persons` — особи

Особовий склад. Містить **усіх** — і бійців (одержувачі майна), і осіб, що призначаються МВО.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `full_name` | text | так | ПІБ |
| `unit` | FK → `units` | так | Підрозділ особи |
| `rank` | text | ні | Звання |

**Немає прапорця `is_mvo`** — свідомо. «Особа є МВО» визначається наявністю діючого запису в `mvo` (єдине джерело правди, не застаріває).

`persons` ≠ користувачі системи. Користувачі — окремо, в `access_users`. Боєць є в `persons`, але може не бути користувачем.

---

### 2.4 `warehouses` — облікові точки (склади)

Центральна таблиця моделі. Об'єднує склади служб і склади підрозділів — саме тому будь-який рух має уніфіковану форму `from_warehouse → to_warehouse`.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `name` | text | так | Назва («Склад РАО», «Склад 1-ї роти») |
| `type` | enum(`service`, `unit`) | так | Тип точки |
| `service` | FK → `services` | якщо `type=service` | Служба складу |
| `unit` | FK → `units` | якщо `type=unit` | Підрозділ складу |

**Інваріант профілю** — `service` і `unit` взаємовиключні:

| `type` | `service` | `unit` |
|---|---|---|
| `service` | заповнено | порожньо |
| `unit` | порожньо | заповнено |

**Критичний інваріант:** запис `warehouses` є **стабільним і незмінним**. Він прив'язаний до служби/підрозділу, а **не до особи**. Ротація МВО не створює новий склад — змінюється лише запис у `mvo`. Це гарантує, що майно не «зависає» на знятому МВО.

Немає колонки `active` — склад існує, доки існує підрозділ/служба.

---

### 2.5 `mvo` — призначення МВО

Журнал «хто коли відповідав за склад підрозділу». Забезпечує історичність: накладна минулого періоду завжди показує МВО, що діяв на той момент.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `warehouse` | FK → `warehouses` | так | Склад (тільки `type=unit`) |
| `person` | FK → `persons` | так | Хто відповідає |
| `from_date` | date | так | Початок призначення |
| `to_date` | date | ні | Кінець. **Порожньо = діє зараз** |

**Інваріанти:**
- `warehouse.type` має бути `unit` (у складу служби МВО немає — там працівник служби).
- `to_date >= from_date`, якщо заповнено.
- На один `warehouse` може бути **не більше одного** запису з порожнім `to_date`.

**Ротація МВО:** проставити `to_date` діючому запису → створити новий без `to_date`. Склад і всі рухи не змінюються.

Прапорця `active` немає — «діючий» = `to_date IS NULL`.

---

### 2.6 `items` — номенклатура

Тип майна, не фізичний предмет. Один рядок = «АК-74» взагалі, а не конкретний автомат.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `name` | text | так | Назва номенклатури |
| `service` | FK → `services` | так | Служба — вісь розмежування доступу |
| `is_serialized` | bool | так (default `false`) | Гілка обліку |
| `unit_of_measure` | enum | так | `шт`, `компл`, `пара`, `кг`, `м`, `л` |
| `code` | text | ні | Номенклатурний номер / артикул |

`is_serialized` **не пов'язаний** з одиницею виміру: серійним може бути і `шт` (автомат), і `компл` (радіостанція в зборі).

---

### 2.7 `instances` — екземпляри серійного майна

Одна фізична одиниця = один запис. Тільки для номенклатури з `is_serialized = true`.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `item` | FK → `items` | так | Номенклатура (має бути `is_serialized=true`) |
| `serial_no` | text | так | Серійний / інвентарний номер |
| `current_warehouse` | FK → `warehouses` | похідне | Де зараз за custody |

**`current_warehouse` не редагується вручну** — обчислюється як `to_warehouse` останнього руху цього екземпляра:

```sql
SELECT m.to_warehouse
FROM movements m
WHERE m.instance = :instance_id
ORDER BY m.date DESC, m.id DESC
LIMIT 1
```

**Рекомендація щодо реалізації:** зберігати як **денормалізоване поле** (оновлюване тригером/після запису руху), а не обчислювати на льоту. Причина: це поле читається у правилах доступу на кожному рядку при кожному запиті — обчислення на льоту дає навантаження і ускладнює ACL.

**Інваріанти:**
- `serial_no` унікальний у межах `item` (краще — глобально).
- `item.is_serialized` має бути `true`.

---

### 2.8 `movements` — рухи (custody)

Формальні передачі між обліковими точками. Ядро системи.

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `date` | date | так | Дата документа |
| `type` | enum | так | `receipt`, `transfer`, `writeoff` |
| `from_warehouse` | FK → `warehouses` | ні | Звідки. Порожньо для `receipt` |
| `to_warehouse` | FK → `warehouses` | ні | Куди. Порожньо для `writeoff` |
| `item` | FK → `items` | так | Номенклатура (**заповнюється завжди**, у т.ч. для серійних) |
| `instance` | FK → `instances` | якщо серійне | Екземпляр |
| `quantity` | numeric | так | Кількість. Для серійних завжди `1` |
| `doc_number` | text | ні | Номер накладної |
| `signed_by` | FK → `persons` | ні | Снапшот підписанта (МВО на момент створення) |

**Типи рухів:**

| `type` | `from_warehouse` | `to_warehouse` | Хто створює |
|---|---|---|---|
| `receipt` (прихід зовні) | порожньо | склад служби | працівник служби |
| `transfer` (передача) | будь-який | будь-який | працівник служби / МВО |
| `writeoff` (списання) | будь-який | порожньо | працівник служби |

**Критично для реалізації:** `item` має бути **реальною колонкою**, а не обчислюваною з `instance`. Причина: правила доступу перевіряють `item.service` у момент створення запису — якщо `item` обчислюється, на цей момент значення ще немає, і правило падає. Для серійного руху `item` підставляється автоматично з `instance.item`, але зберігається фізично.

**Інваріанти:**
- Хоча б одне з `from_warehouse` / `to_warehouse` заповнене.
- `from_warehouse != to_warehouse`.
- Якщо `item.is_serialized` → `instance` заповнений і `quantity = 1`.
- Якщо не `is_serialized` → `instance` порожній, `quantity > 0`.
- Якщо `instance` заповнений → `instance.item = item`.

---

### 2.9 `assignments` — видача особовому складу

Фізичне тримання в межах подотчіту складу підрозділу. **Не змінює custody.**

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `warehouse` | FK → `warehouses` | так | Склад підрозділу (`type=unit`), з якого видано |
| `person` | FK → `persons` | так | Кому видано |
| `item` | FK → `items` | так | Номенклатура |
| `instance` | FK → `instances` | якщо серійне | Екземпляр |
| `quantity` | numeric | так | Кількість. Для серійних `1` |
| `issued_date` | date | так | Дата видачі |
| `returned_date` | date | ні | Дата повернення. **Порожньо = на руках** |

**Інваріанти:**
- `warehouse.type = 'unit'`.
- `person.unit = warehouse.unit` — видавати можна тільки особі свого підрозділу.
- `returned_date >= issued_date`, якщо заповнено.
- Для серійного: екземпляр не може бути одночасно на руках у двох осіб (не більше одного запису з порожнім `returned_date` на `instance`).
- Для серійного: `instance.current_warehouse = warehouse` — не можна видати те, чого немає на цьому складі.
- Для несерійного: сума активних видач не перевищує залишок складу (див. §4.2).

---

### 2.10 `balances` — залишки несерійного майна

Агрегат по парі `(warehouse, item)`. Тільки для несерійного майна — для серійного залишок є фільтром `instances`.

| Колонка | Тип | Опис |
|---|---|---|
| `warehouse` | FK → `warehouses` | Склад |
| `item` | FK → `items` | Номенклатура |
| `qty` | numeric | Поточний залишок |

**Важливий нюанс реалізації:** це **не проста group-by агрегація**, бо один рух впливає на **два** склади (мінус на `from`, плюс на `to`). Тому:

```sql
SELECT warehouse, item, SUM(qty) AS qty
FROM (
    SELECT to_warehouse   AS warehouse, item,  quantity AS qty
    FROM movements WHERE to_warehouse IS NOT NULL AND instance IS NULL
    UNION ALL
    SELECT from_warehouse AS warehouse, item, -quantity AS qty
    FROM movements WHERE from_warehouse IS NOT NULL AND instance IS NULL
) ledger
GROUP BY warehouse, item
```

**Рекомендація:** реалізувати як **view** (або матеріалізовану view з перерахунком при записі руху). Окрему фізичну таблицю з ручним оновленням не робити — джерелом правди лишаються `movements`.

Альтернативний підхід для реляційної БД: писати рухи одразу як **подвійний запис** (дві рядки-проводки: дебет/кредит) — тоді `balances` стає звичайним `GROUP BY`. Це чистіше архітектурно, але ускладнює редагування документа.

---

### 2.11 `access_users` — користувачі та їхні зони

Мапінг «користувач → роль → зона відповідальності».

| Колонка | Тип | Обов'язк. | Опис |
|---|---|---|---|
| `id` | PK | — | |
| `email` | text | так | Ідентифікатор користувача |
| `role` | enum(`admin`, `service`, `mvo`) | так | Роль |
| `service` | FK → `services` | якщо `role=service` | Своя служба |
| `unit` | FK → `units` | якщо `role=mvo` | Свій підрозділ |
| `warehouse` | FK → `warehouses` | якщо `role=mvo` | Свій склад підрозділу |
| `person` | FK → `persons` | ні | Зв'язок з особою в системі |

**Ротація МВО не змінює `warehouse`** у мапінгу — новий МВО отримує той самий склад підрозділу і одразу бачить усе майно.

---

## 3. Модель доступу

Розмежування йде по **двох ортогональних осях**:

- **Працівник служби** (`role=service`) — бачить майно **своєї служби** в усіх підрозділах (вертикальний зріз).
- **МВО** (`role=mvo`) — бачить майно **свого складу підрозділу** всіх служб (горизонтальний зріз).
- **Admin** — бачить усе.

Осі перетинаються, а не вкладаються: майно служби Б на складі 1-ї роти видиме обом.

### 3.1 Матриця прав

| Таблиця | `service` | `mvo` | `admin` |
|---|---|---|---|
| `services`, `units`, `persons`, `warehouses` | R | R | RW |
| `mvo` | R | R | RW |
| `items` | R усі; CUD своєї служби | R | RW |
| `instances` | R своєї служби; CUD своєї служби | R свого складу | RW |
| `movements` | R своєї служби; C своєї служби | R свого складу; C зі свого складу | RW |
| `assignments` | R своєї служби | RW свого складу | RW |
| `balances` | R своєї служби | R свого складу | RW |

Довідники (`services`, `units`, `persons`, `warehouses`) читають усі — МВО має бачити номенклатуру й підрозділи, щоб працювати. Чутливими є не довідники, а залишки.

### 3.2 Умови (псевдокод)

```
# items
READ:   true
CREATE: role=admin OR (role=service AND new.service = me.service)
UPDATE: role=admin OR (role=service AND row.service = me.service)
DELETE: те саме, що UPDATE

# instances
READ:   role=admin
        OR (role=service AND row.item.service = me.service)
        OR (role=mvo     AND row.current_warehouse = me.warehouse)
CREATE: role=admin OR (role=service AND new.item.service = me.service)
UPDATE: role=admin OR (role=service AND row.item.service = me.service)

# movements
READ:   role=admin
        OR (role=service AND row.item.service = me.service)
        OR (role=mvo     AND (row.from_warehouse = me.warehouse
                           OR row.to_warehouse   = me.warehouse))
CREATE: role=admin
        OR (role=service AND new.item.service = me.service)
        OR (role=mvo     AND new.from_warehouse = me.warehouse)

# assignments
READ:   role=admin
        OR (role=service AND row.item.service = me.service)
        OR (role=mvo     AND row.warehouse = me.warehouse)
CREATE: role=admin
        OR (role=mvo AND new.warehouse = me.warehouse
                     AND new.person.unit = me.unit)
UPDATE: role=admin OR (role=mvo AND row.warehouse = me.warehouse)

# balances
READ:   role=admin
        OR (role=service AND row.item.service = me.service)
        OR (role=mvo     AND row.warehouse = me.warehouse)
```

**Примітка щодо CREATE:** умови мають перевірятися проти **нового** запису (`new.*`), а не наявного. Це стосується всіх правил створення.

**Свідоме послаблення:** працівник служби може створити будь-який рух своєї номенклатури, включно зі складу підрозділу. Це дозволяє йому підстрахувати/виправити МВО. Якщо потрібне жорсткіше розмежування — додати умову `new.from_warehouse.type = 'service'` для ролі `service`.

---

## 4. Бізнес-правила та валідація

### 4.1 Валідація руху (`movements`)

Перевірка виконується **проти стану до цього руху** — тобто з урахуванням усіх рухів, що передують поточному за `(date, id)`.

**Серійний рух** — екземпляр має бути на складі-відправнику:

```
prior_location = to_warehouse останнього руху instance,
                 де (date, id) < (поточний date, id)

IF from_warehouse IS NOT NULL AND prior_location != from_warehouse:
    ERROR "Екземпляр не на цьому складі"
```

**Несерійний рух** — достатність залишку:

```
balance_before = SUM(quantity) рухів TO from_warehouse
               - SUM(quantity) рухів FROM from_warehouse
                 для цього item, де (date, id) < (поточний date, id)

IF from_warehouse IS NOT NULL AND balance_before < quantity:
    ERROR "Недостатньо: є {balance_before}, потрібно {quantity}"
```

Для `type = 'receipt'` (`from_warehouse IS NULL`) перевірка не виконується.

### 4.2 Валідація видачі (`assignments`)

**Серійна видача:**
```
IF instance.current_warehouse != warehouse:
    ERROR "Екземпляр не на цьому складі"
IF існує інший assignment цього instance з returned_date IS NULL:
    ERROR "Екземпляр уже на руках"
```

**Несерійна видача** — сума активних видач не перевищує залишок складу:
```
issued = SUM(quantity) з assignments
         WHERE warehouse = :warehouse AND item = :item
           AND returned_date IS NULL

IF issued + new.quantity > balances(warehouse, item).qty:
    ERROR "Видано більше, ніж є на складі"
```

**Обов'язково для обох:**
```
IF person.unit != warehouse.unit:
    ERROR "Особа з іншого підрозділу"
```

### 4.3 Валідація призначення МВО (`mvo`)

```
IF warehouse.type != 'unit':
    ERROR "МВО призначається лише на склад підрозділу"
IF to_date IS NOT NULL AND to_date < from_date:
    ERROR "Некоректний період"
IF to_date IS NULL AND існує інший запис
   з тим самим warehouse і to_date IS NULL:
    ERROR "Уже є діючий МВО на цьому складі"
```

### 4.4 Рівні застосування

| Рівень | Механізм | Коли |
|---|---|---|
| М'який | Підсвітка помилкових записів, попередження в UI | MVP |
| Жорсткий | Заборона збереження (constraint / ACL / транзакція) | після відкатки схеми |

Для MVP достатньо м'якого — оператор бачить проблему й виправляє. Жорсткий рівень вмикати після того, як схема стабілізувалась.

---

## 5. Ключові запити

**Поточний МВО складу:**
```sql
SELECT p.full_name
FROM mvo m JOIN persons p ON p.id = m.person
WHERE m.warehouse = :warehouse_id AND m.to_date IS NULL
```

**Історія МВО складу:**
```sql
SELECT p.full_name, m.from_date, m.to_date
FROM mvo m JOIN persons p ON p.id = m.person
WHERE m.warehouse = :warehouse_id
ORDER BY m.from_date DESC
```

**Серійні залишки складу (що є на складі):**
```sql
SELECT i.serial_no, it.name
FROM instances i JOIN items it ON it.id = i.item
WHERE i.current_warehouse = :warehouse_id
```

**Що на руках у бійця:**
```sql
SELECT it.name, a.quantity, i.serial_no, a.issued_date
FROM assignments a
     JOIN items it ON it.id = a.item
     LEFT JOIN instances i ON i.id = a.instance
WHERE a.person = :person_id AND a.returned_date IS NULL
```

**Вільний залишок складу (несерійне: є мінус видано):**
```sql
SELECT b.item, b.qty,
       COALESCE(a.issued, 0) AS issued,
       b.qty - COALESCE(a.issued, 0) AS available
FROM balances b
LEFT JOIN (
    SELECT warehouse, item, SUM(quantity) AS issued
    FROM assignments WHERE returned_date IS NULL
    GROUP BY warehouse, item
) a ON a.warehouse = b.warehouse AND a.item = b.item
WHERE b.warehouse = :warehouse_id
```

**Повний подотчіт МВО (усе, за що відповідає):**
```sql
-- несерійне
SELECT it.name, b.qty FROM balances b
JOIN items it ON it.id = b.item
WHERE b.warehouse = :warehouse_id
-- серійне
SELECT it.name, i.serial_no FROM instances i
JOIN items it ON it.id = i.item
WHERE i.current_warehouse = :warehouse_id
```

---

## 6. Порядок реалізації

Створювати в цьому порядку — залежності FK:

1. `services`
2. `units`
3. `persons` → `units`
4. `warehouses` → `services`, `units`
5. `mvo` → `warehouses`, `persons`
6. `items` → `services`
7. `instances` → `items` (поле `current_warehouse` заповнюється після кроку 8)
8. `movements` → `warehouses`, `items`, `instances`
9. `assignments` → `warehouses`, `persons`, `items`, `instances`
10. `balances` (view/агрегат по `movements`)
11. `access_users` → `services`, `units`, `warehouses`

**Циклічна залежність 7 ↔ 8:** `instances.current_warehouse` залежить від `movements`, а `movements.instance` — від `instances`. Створювати `instances` без обчислення `current_warehouse`, вмикати логіку після появи `movements`.

Правила доступу підключати **останніми**, коли всі таблиці й колонки існують.

---

## 7. Свідомо не входить у MVP

- Друковані форми документів (накладні, роздавальні відомості) — ведуться окремо.
- Ієрархія підрозділів (структура плоска).
- Розформування підрозділів / закриття складів.
- Партії, строки зберігання, категорії придатності.
- Вартісний облік, амортизація.
- Інвентаризаційні відомості та звірки.
- Аудит-лог змін.

Кожен із пунктів додається без переробки ядра.

---

## 8. Тестові сценарії для приймання

1. **Прихід:** створити `receipt` на склад служби → залишок збільшився.
2. **Передача:** склад служби → склад 1-ї роти → залишок перемістився; на складі служби зменшився.
3. **Недостатність:** спроба передати більше, ніж є → помилка валідації.
4. **Серійний рух:** передати екземпляр → `current_warehouse` змінився.
5. **Чужий екземпляр:** спроба передати екземпляр з іншого складу → помилка.
6. **Видача бійцю:** створити `assignment` → залишок складу **не змінився**, майно лишилось у подотчіті; вільний залишок зменшився.
7. **Видача чужому:** спроба видати особі іншого підрозділу → помилка.
8. **Ротація МВО:** проставити `to_date`, створити новий запис → усе майно складу лишилось на місці, доступ нового МВО працює.
9. **Доступ служби:** працівник служби А не бачить майна служби Б.
10. **Доступ МВО:** МВО 1-ї роти не бачить майна 2-ї роти, але бачить майно всіх служб на своєму складі.
11. **Видане не зникає:** після видачі бійцю майно лишається видимим для МВО.
