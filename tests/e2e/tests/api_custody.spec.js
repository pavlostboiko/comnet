/**
 * v2 custody ledger — рухи склад→склад + баланси.
 *
 * Covers plan §8: receipt increases balance, transfer moves it, insufficient
 * rejected, serial move updates current_warehouse, wrong-location serial rejected,
 * державне/волонтерське — окремі лінії балансу.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('v2 custody API', () => {
  let api
  let cleanup

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    cleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  })

  // Seed a service (+ its warehouse), two units (+ their warehouses), a nomenclature.
  async function seed(tag, { serialized = false } = {}) {
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    const u1 = await postJson(api, '/api/structure/units', { name: `Рота A ${tag}` })
    const u2 = await postJson(api, '/api/structure/units', { name: `Рота Б ${tag}` })
    cleanup.push(`/api/structure/units/${u1.id}`, `/api/structure/units/${u2.id}`,
                 `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const wh1 = whs.find(w => w.unit_id === u1.id)
    const wh2 = whs.find(w => w.unit_id === u2.id)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `${serialized ? 'АК' : 'Бушлат'} ${tag}`, service_id: svc.id,
      is_serialized: serialized, unit_of_measure: 'шт', price: 100,
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    return { svc, svcWh, wh1, wh2, nom }
  }

  test('receipt increases balance; transfer moves it; sending side drops', async () => {
    const tag = `c-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag)

    // Receipt 10 into service warehouse
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: s.nom.id,
      to_warehouse_id: s.svcWh.id, quantity: 10, is_official: true,
    })
    let bal = await api.get(`/api/custody/balances?warehouse_id=${s.svcWh.id}`).then(r => r.json())
    expect(Number(bal.find(b => b.nomenclature_id === s.nom.id).qty)).toBe(10)

    // Transfer 4 → unit A
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-02', type: 'transfer', nomenclature_id: s.nom.id,
      from_warehouse_id: s.svcWh.id, to_warehouse_id: s.wh1.id, quantity: 4, is_official: true,
    })
    bal = await api.get(`/api/custody/balances?warehouse_id=${s.svcWh.id}`).then(r => r.json())
    expect(Number(bal.find(b => b.nomenclature_id === s.nom.id).qty)).toBe(6)
    const balA = await api.get(`/api/custody/balances?warehouse_id=${s.wh1.id}`).then(r => r.json())
    expect(Number(balA.find(b => b.nomenclature_id === s.nom.id).qty)).toBe(4)
  })

  test('insufficient balance rejected', async () => {
    const tag = `ins-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag)
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: s.nom.id,
      to_warehouse_id: s.svcWh.id, quantity: 3, is_official: true,
    })
    const resp = await api.post('/api/custody/movements', {
      data: { date: '2026-07-02', type: 'transfer', nomenclature_id: s.nom.id,
              from_warehouse_id: s.svcWh.id, to_warehouse_id: s.wh1.id, quantity: 5, is_official: true },
    })
    expect(resp.status()).toBe(400)
  })

  test('державне і волонтерське — окремі лінії балансу', async () => {
    const tag = `off-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag)
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: s.nom.id,
      to_warehouse_id: s.svcWh.id, quantity: 5, is_official: true,
    })
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: s.nom.id,
      to_warehouse_id: s.svcWh.id, quantity: 3, is_official: false,
    })
    const bal = await api.get(`/api/custody/balances?warehouse_id=${s.svcWh.id}`).then(r => r.json())
    const lines = bal.filter(b => b.nomenclature_id === s.nom.id)
    expect(lines).toHaveLength(2)
    expect(Number(lines.find(l => l.is_official).qty)).toBe(5)
    expect(Number(lines.find(l => !l.is_official).qty)).toBe(3)
  })

  test('serial: receipt places instance, transfer updates current_warehouse, wrong-location rejected', async () => {
    const tag = `ser-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { serialized: true })
    const inst = await postJson(api, `/api/nomenclature/${s.nom.id}/instances`, { serial_no: `AK-${tag}` })

    // Receipt into service warehouse
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: s.nom.id,
      instance_id: inst.id, to_warehouse_id: s.svcWh.id,
    })
    let serial = await api.get(`/api/custody/serial?warehouse_id=${s.svcWh.id}`).then(r => r.json())
    expect(serial.find(x => x.instance_id === inst.id)).toBeTruthy()

    // Wrong-location transfer (from unit A where it is NOT) → 400
    const bad = await api.post('/api/custody/movements', {
      data: { date: '2026-07-02', type: 'transfer', nomenclature_id: s.nom.id,
              instance_id: inst.id, from_warehouse_id: s.wh1.id, to_warehouse_id: s.wh2.id },
    })
    expect(bad.status()).toBe(400)

    // Correct transfer service → unit A
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-02', type: 'transfer', nomenclature_id: s.nom.id,
      instance_id: inst.id, from_warehouse_id: s.svcWh.id, to_warehouse_id: s.wh1.id,
    })
    serial = await api.get(`/api/custody/serial?warehouse_id=${s.wh1.id}`).then(r => r.json())
    expect(serial.find(x => x.instance_id === inst.id)).toBeTruthy()
    const svcSerial = await api.get(`/api/custody/serial?warehouse_id=${s.svcWh.id}`).then(r => r.json())
    expect(svcSerial.find(x => x.instance_id === inst.id)).toBeFalsy()
  })
})
