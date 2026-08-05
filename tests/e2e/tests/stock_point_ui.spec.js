/**
 * UI smoke: точку зберігання видно й можна поставити прямо на «Залишках»
 * (колонка «Точка»), фільтр за точкою працює; вкладка «Точки зберігання» в
 * Довідниках створює точку для складу.
 */
const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

test('storage point: create in Довідники, set on Залишки, filter by it', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `PtSvc ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const nom = await j('/api/nomenclature', { name: `Рація ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const inst = await j(`/api/nomenclature/${nom.id}/instances`, { serial_no: `PT-${ts}` })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, instance_id: inst.id, to_warehouse_id: svcWh.id })
  const other = await j('/api/nomenclature', { name: `Бушлат ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: other.id, to_warehouse_id: svcWh.id, quantity: 4 })

  // Довідники → Точки зберігання: створюємо точку для цього складу
  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Точки зберігання' }).click()
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()
  await page.locator('.modal input').first().fill(`Бокс ${ts}`)
  await page.locator('.modal select').first().selectOption({ label: svcWh.name })
  await page.locator('.btn-pri').click()
  await expect(page.locator('tbody tr', { hasText: `Бокс ${ts}` }).first()).toBeVisible()

  // Залишки: ставимо точку серійному рядку — зберігається після перезавантаження
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  const row = page.locator('tbody tr', { hasText: `PT-${ts}` }).first()
  await Promise.all([
    page.waitForResponse(r => r.url().includes(`/instances/${inst.id}`)
      && r.request().method() === 'PUT' && r.status() === 200),
    row.locator('.point-sel').selectOption({ label: `Бокс ${ts}` }),
  ])

  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await expect(page.locator('tbody tr', { hasText: `PT-${ts}` }).first().locator('.point-sel'))
    .toHaveValue(String((await api.get(`/api/structure/storage-points?warehouse_id=${svcWh.id}`).then(r => r.json()))[0].id))

  // Картка екземпляра показує ту саму точку (там її теж можна змінити)
  await page.locator('tbody tr', { hasText: `PT-${ts}` }).first()
    .locator('.btn-card').click()
  await expect(page.locator('.modal', { hasText: 'Картка:' }).locator('select'))
    .toHaveValue(String((await api.get(`/api/structure/storage-points?warehouse_id=${svcWh.id}`).then(r => r.json()))[0].id))
  await page.locator('.modal .btn-sec', { hasText: 'Скасувати' }).click()

  // Фільтр «Без точки» ховає рядок із точкою, лишає несерійний без неї
  await page.locator('.point-filter').selectOption('none')
  await expect(page.locator('tbody tr', { hasText: `PT-${ts}` })).toHaveCount(0)
  await expect(page.locator('tbody tr', { hasText: `Бушлат ${ts}` }).first()).toBeVisible()

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/nomenclature/${other.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})

// Точку можна завести прямо на «Залишках» — на складі підрозділу, де точок ще нема
// (раніше пікер там не показувався взагалі, тож поле виглядало нередагованим).
test('storage point can be created inline on a unit warehouse', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `InlSvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `InlРота ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const nom = await j('/api/nomenclature', { name: `Бушлат ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 6 })
  await j('/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 4 })

  page.on('dialog', d => d.accept(`Намет ${ts}`))   // prompt: назва нової точки
  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: unitWh.name }).click()

  const row = page.locator('tbody tr', { hasText: `Бушлат ${ts}` }).first()
  await row.locator('.point-sel').selectOption('__new__')
  await expect(row.locator('.point-sel')).toHaveValue(/\d+/)          // нова точка обрана

  // Точка справді створена для СКЛАДУ ПІДРОЗДІЛУ і проставлена картці
  const points = await api.get(`/api/structure/storage-points?warehouse_id=${unitWh.id}`).then(r => r.json())
  expect(points.map(p => p.name)).toContain(`Намет ${ts}`)
  const bal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
  expect(bal.find(b => b.nomenclature_id === nom.id).storage_point).toBe(`Намет ${ts}`)

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})

// Точку можна поставити й виданому майну — воно фізично десь лежить.
test('storage point can be set on issued goods', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `IssPtSvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `IssPtРота ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const person = await j('/api/settings/persons', { last_name: `Боєць${ts}`, first_name: 'І', unit_id: unit.id })
  const point = await j('/api/structure/storage-points', { name: `Намет ${ts}`, warehouse_id: unitWh.id })
  const nom = await j('/api/nomenclature', { name: `Спальник ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 8 })
  await j('/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 5 })
  const asg = await j('/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 2, issued_date: '2026-07-03' })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: unitWh.name }).click()
  await page.locator('.f-chip', { hasText: 'Видане' }).click()

  // Рядок видачі, а не залишку: до застосування фільтра в таблиці є обидва.
  const row = page.locator('tbody tr')
    .filter({ hasText: `Спальник ${ts}` }).filter({ hasText: `Боєць${ts}` }).first()
  await expect(row).toBeVisible()
  // Чекаємо саме на відповідь: `toHaveValue` після selectOption проходить одразу
  // (DOM уже змінений) і нічого не синхронізує.
  await Promise.all([
    page.waitForResponse(r => r.url().includes(`/api/assignments/${asg.id}/point`)
      && r.request().method() === 'PUT' && r.status() === 200),
    row.locator('.point-sel').selectOption(String(point.id)),
  ])

  // Точка лягла на ВИДАЧУ, а не на залишок картки
  const listed = await api.get(`/api/assignments?warehouse_id=${unitWh.id}`).then(r => r.json())
  expect(listed.find(a => a.id === asg.id).storage_point).toBe(`Намет ${ts}`)
  const bal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
  expect(bal.find(b => b.nomenclature_id === nom.id).storage_point_id).toBeNull()

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
