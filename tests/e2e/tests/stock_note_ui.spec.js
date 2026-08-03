const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// Примітка екземпляра редагується в його «Картці» на Залишках і зберігається.
test('serial instance note editable via the instance card on Залишки', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `NtSvc ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const nom = await j('/api/nomenclature', { name: `Рація ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const inst = await j(`/api/nomenclature/${nom.id}/instances`, { serial_no: `SN-${ts}` })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, instance_id: inst.id, to_warehouse_id: svcWh.id })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()

  const row = page.locator('tbody tr', { hasText: `SN-${ts}` }).first()
  await row.locator('.btn-card').click()
  const card = page.locator('.modal', { hasText: 'Картка:' })
  await expect(card).toContainText(`SN-${ts}`)          // серійний видно в картці
  await card.locator('textarea').fill('загублено ремінь')
  await card.locator('.btn-pri', { hasText: 'Зберегти' }).click()
  await expect(page.locator('.modal', { hasText: 'Картка:' })).toHaveCount(0)
  await expect(row).toContainText('загублено ремінь')   // видно в колонці «Примітка»

  // persists after reload
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await page.locator('tbody tr', { hasText: `SN-${ts}` }).first()
    .locator('.btn-card').click()
  await expect(page.locator('.modal textarea')).toHaveValue('загублено ремінь')

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
