/**
 * UI smoke: the «Без документа» tab shows a «Відкликати» button per undocumented
 * movement; clicking it (and confirming) removes the movement and the direction
 * group disappears. Self-contained via API (unique names) to avoid collisions.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

const S = 'REVUI'  // unique suffix for this spec

test('«Без документа»: revoke button removes an undocumented transfer', async ({ page, request }) => {
  // Seed via API: serial item placed at A, transferred to uniquely-named B
  const api = await loginApi(request)
  const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Антена${S}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт' } }).then(r => r.json())
  const inst = await api.post(`/api/nomenclature/${nom.id}/instances`, { data: {
    serial_no: `${S}-SER-1`, card_number: `${S}-1` } }).then(r => r.json())
  const uA = await api.post('/api/structure/units', { data: { name: `${S}-A` } }).then(r => r.json())
  const uB = await api.post('/api/structure/units', { data: { name: `${S}-Б` } }).then(r => r.json())
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const whA = whs.find(w => w.unit_id === uA.id)
  const whB = whs.find(w => w.unit_id === uB.id)
  await api.post('/api/custody/movements', { data: {
    type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, instance_id: inst.id, date: '2026-06-01' } })
  await api.post('/api/custody/movements', { data: {
    type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id,
    nomenclature_id: nom.id, instance_id: inst.id, date: '2026-06-02' } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/docs`)
  await page.click('button:has-text("Без документа")')

  const group = page.locator('.free-group', { has: page.locator(`.free-dir:has-text("${S}-Б")`) })
  await expect(group).toBeVisible()

  page.once('dialog', d => d.accept())
  await group.locator('.btn-revoke').first().click()

  // Group disappears once its only movement is revoked
  await expect(page.locator(`.free-dir:has-text("${S}-Б")`)).toHaveCount(0)
})
