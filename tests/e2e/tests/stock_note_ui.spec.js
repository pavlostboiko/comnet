const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// A serial row on Залишки has an editable «Примітка» that persists.
test('serial instance note editable on Залишки and persists', async ({ page, request }) => {
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
  await row.locator('.note-inp').fill('загублено ремінь')
  await row.locator('.note-inp').blur()

  // persists after reload
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await expect(page.locator('tbody tr', { hasText: `SN-${ts}` }).first().locator('.note-inp')).toHaveValue('загублено ремінь')

  await api.delete(`/api/nomenclature/${nom.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
