const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

test('Переміщення page loads with a warehouse filter and log table', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/custody`)
  await expect(page.locator('.tile-title')).toContainText('Переміщення')
  await expect(page.locator('.wh-select')).toBeVisible()
  // The log table header is present
  await expect(page.locator('thead th', { hasText: 'Звідки → Куди' })).toBeVisible()
})

// Загальна історія: видача особі показується поряд із рухами складів (задача 12).
test('Переміщення shows issues next to warehouse movements', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `FeedUISvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `FeedUIРота ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const person = await j('/api/settings/persons', { last_name: `Боєць${ts}`, first_name: 'І', unit_id: unit.id })
  const nom = await j('/api/nomenclature', { name: `Ліхтар ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-04-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 5 })
  await j('/api/custody/movements', { date: '2026-04-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 3 })
  await j('/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 1, issued_date: '2026-04-03' })

  await uiLogin(page)
  await page.goto(`${URL}/custody`)
  await page.locator('.wh-select').selectOption(String(unitWh.id))

  const issued = page.locator('tbody tr', { hasText: `Ліхтар ${ts}` }).filter({ hasText: 'видано' })
  await expect(issued.first()).toContainText(`Боєць${ts}`)          // кому видано
  await expect(page.locator('tbody tr', { hasText: `Ліхтар ${ts}` }).filter({ hasText: 'переміщення' }).first()).toBeVisible()

  // Фільтр подій: лишаємо тільки видачі — рух зникає
  await page.locator('.f-chip', { hasText: 'Видано' }).click()
  await expect(page.locator('tbody tr', { hasText: `Ліхтар ${ts}` }).filter({ hasText: 'переміщення' })).toHaveCount(0)
  await expect(issued.first()).toBeVisible()

  // Зміна точки — теж подія стрічки
  const point = await j('/api/structure/storage-points', { name: `Бокс ${ts}`, warehouse_id: unitWh.id })
  await api.put('/api/custody/stock-point', { data: {
    nomenclature_id: nom.id, warehouse_id: unitWh.id, storage_point_id: point.id } })
  await page.reload()
  await page.locator('.wh-select').selectOption(String(unitWh.id))
  await page.locator('.f-chip', { hasText: 'Точка' }).click()
  const pointRow = page.locator('tbody tr', { hasText: `Ліхтар ${ts}` }).first()
  await expect(pointRow).toContainText('точка')
  await expect(pointRow).toContainText(`Бокс ${ts}`)

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/settings/persons/${person.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
