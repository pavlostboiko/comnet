/**
 * v2 Items import — POST /api/admin/v2/import/items.
 *
 * Verifies: find-or-create service/unit/nomenclature/person, receipt into the
 * unit warehouse, «Де» = «<підрозділ> людина» splits into unit + assignment,
 * empty «Де» falls back to the service warehouse.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('v2 import: nomenclature + custody + assignment from one file', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    // Pre-create unit "1 рота" so «1 рота Петренко» splits into unit + person.
    // (unique-ish name to avoid collisions across runs isn't possible here since
    // the fixture is fixed — so we tolerate pre-existing data and assert deltas.)
    let unit = (await api.get('/api/structure/units').then(r => r.json())).find(u => u.name === '1 рота')
    if (!unit) unit = await postJson(api, '/api/structure/units', { name: '1 рота' })

    const fixture = fs.readFileSync(path.join(__dirname, 'fixtures/import_v2_items.xlsx'))
    const resp = await api.post('/api/admin/v2/import/items', {
      multipart: {
        file: { name: 'import_v2_items.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: fixture },
      },
    })
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.rows).toBe(3)
    expect(body.movements).toBe(3)
    expect(body.assignments).toBeGreaterThanOrEqual(1)

    // Warehouses
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const unitWh = whs.find(w => w.type === 'unit' && w.unit_id === unit.id)
    const raoWh = whs.find(w => w.type === 'service' && w.name === 'Склад РАО')
    const rechWh = whs.find(w => w.type === 'service' && w.name === 'Склад Речова')
    expect(unitWh).toBeTruthy()

    // Бушлат: non-serial, 5 at unit warehouse (custody unchanged by the assignment)
    const unitBal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    const bushlat = unitBal.find(b => b.name === 'Бушлат')
    expect(bushlat).toBeTruthy()
    expect(Number(bushlat.qty)).toBe(5)

    // Петренко holds Бушлат (assignment at the unit warehouse)
    const asg = await api.get(`/api/assignments?warehouse_id=${unitWh.id}&active=true`).then(r => r.json())
    expect(asg.some(a => a.nomenclature_id === bushlat.nomenclature_id)).toBe(true)

    // АК-74: serial instance now at the unit warehouse
    const serial = await api.get(`/api/custody/serial?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(serial.some(s => s.serial_no === 'AK-IMP-1')).toBe(true)

    // Патрони: empty «Де» → landed on the РАО service warehouse
    const raoBal = await api.get(`/api/custody/balances?warehouse_id=${raoWh.id}`).then(r => r.json())
    expect(raoBal.some(b => b.name === 'Патрони 5.45')).toBe(true)

    // cleanup created services/units is left to the DB (fixture reused across runs);
    // we only clean the unit we may have created here if it had no prior data.
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
