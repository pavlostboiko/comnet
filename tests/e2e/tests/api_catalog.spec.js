/**
 * Nomenclature облік/ндм type flows to movements; /custody/totals aggregates.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('nomenclature is_official (ндм) flows to movement; totals aggregate', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `cat-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `CatSvc ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)

    // Card marked as ндм (is_official=false)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `Дрон ${tag}`, service_id: svc.id, unit_of_measure: 'шт', is_official: false,
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    expect(nom.is_official).toBe(false)

    // Receipt 5 — movement inherits ндм from the card (payload is_official ignored)
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id,
      to_warehouse_id: svcWh.id, quantity: 5, is_official: true,  // should be overridden
    })
    const bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    const line = bal.find(b => b.nomenclature_id === nom.id)
    expect(line).toBeTruthy()
    expect(line.is_official).toBe(false)   // came from the card, not the payload

    // Totals show 5 for this nomenclature
    const totals = await api.get('/api/custody/totals').then(r => r.json())
    expect(Number(totals[String(nom.id)])).toBe(5)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})

test('totals count майно that entered via transfer only (no receipt)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Pre-create unit so «склад РотаТ» ... actually «РотаТ» becomes a unit via import.
    const resp = await api.post('/api/admin/v2/import/movements', {
      multipart: {
        file: { name: 'to.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: fs.readFileSync(path.join(__dirname, 'fixtures/import_v2_transfer_only.xlsx')) },
      },
    }).then(r => r.json())
    expect(resp.movements).toBe(1)

    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const nom = noms.find(n => n.name === 'МайноТ')
    expect(nom).toBeTruthy()

    // Entered via transfer (no receipt) → old logic gave 0; now = destination balance
    const totals = await api.get('/api/custody/totals').then(r => r.json())
    expect(Number(totals[String(nom.id)] || 0)).toBeGreaterThanOrEqual(7)
  } finally {
    await api.dispose()
  }
})
