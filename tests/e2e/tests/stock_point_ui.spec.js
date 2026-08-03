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
  await row.locator('.point-sel').selectOption({ label: `Бокс ${ts}` })

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
