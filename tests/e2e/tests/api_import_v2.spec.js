/**
 * v2 Items import — POST /api/admin/v2/import/items.
 *
 * The fixture uses disjoint names (ImpSvcA/ImpUnitA/…) so it can't collide with
 * other tests. The main test asserts DELTAS (this import's contribution), never
 * absolute balances, so re-runs are safe. The destructive wipe+idempotency test
 * is opt-in (RUN_WIPE_TEST=1) so a global wipe never clobbers parallel tests.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson } = require('./helpers/seed')

function importFixture(api) {
  return api.post('/api/admin/v2/import/items', {
    multipart: {
      file: { name: 'import_v2_items.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        buffer: fs.readFileSync(path.join(__dirname, 'fixtures/import_v2_items.xlsx')) },
    },
  })
}
const qtyOf = (rows, name) => Number(rows.find(b => b.name === name)?.qty || 0)

test('v2 import: nomenclature + custody + assignment (delta-safe)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Pre-create the unit so «ImpUnitA Петренко» splits into unit + person
    // (never the whole-string fallback).
    let unit = (await api.get('/api/structure/units').then(r => r.json())).find(u => u.name === 'ImpUnitA')
    if (!unit) unit = await postJson(api, '/api/structure/units', { name: 'ImpUnitA' })
    let whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const unitWh = whs.find(w => w.type === 'unit' && w.unit_id === unit.id)

    const before = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    const bushBefore = qtyOf(before, 'БушлатA')

    const resp = await importFixture(api)
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.rows).toBe(3)
    expect(body.movements).toBe(3)
    // Items import no longer issues to people — видача is a later step.
    expect(body.assignments).toBe(0)

    // БушлатA contributed exactly +5 to the unit warehouse (placement only)
    const after = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(qtyOf(after, 'БушлатA') - bushBefore).toBe(5)

    // No assignment created at the unit warehouse from the import
    const asg = await api.get(`/api/assignments?warehouse_id=${unitWh.id}&active=true`).then(r => r.json())
    const bushId = after.find(b => b.name === 'БушлатA').nomenclature_id
    expect(asg.some(a => a.nomenclature_id === bushId)).toBe(false)

    // АК-A serial at the unit warehouse; ПатрониA (empty «Де») at the ImpRaoA service warehouse
    const serial = await api.get(`/api/custody/serial?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(serial.some(s => s.serial_no === 'AK-IMP-A')).toBe(true)
    whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const raoWh = whs.find(w => w.type === 'service' && w.name === 'Склад ImpRaoA')
    const raoBal = await api.get(`/api/custody/balances?warehouse_id=${raoWh.id}`).then(r => r.json())
    expect(raoBal.some(b => b.name === 'ПатрониA')).toBe(true)
  } finally {
    await api.dispose()
  }
})

// Destructive: clears ALL v2 inventory. Opt-in so it can't race parallel tests.
test('v2 wipe + re-import is idempotent (balances do not accumulate)', async ({ request }) => {
  test.skip(!process.env.RUN_WIPE_TEST, 'destructive — set RUN_WIPE_TEST=1')
  const api = await loginApi(request)
  try {
    let unit = (await api.get('/api/structure/units').then(r => r.json())).find(u => u.name === 'ImpUnitA')
    if (!unit) unit = await postJson(api, '/api/structure/units', { name: 'ImpUnitA' })
    await api.post('/api/admin/v2/wipe')
    await importFixture(api)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const unitWh = whs.find(w => w.type === 'unit' && w.unit_id === unit.id)
    let bal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(qtyOf(bal, 'БушлатA')).toBe(5)
    await api.post('/api/admin/v2/wipe')
    await importFixture(api)
    bal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(qtyOf(bal, 'БушлатA')).toBe(5)
  } finally {
    await api.dispose()
  }
})
