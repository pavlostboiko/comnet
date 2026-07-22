/**
 * v2 assignments — видача особовому складу.
 *
 * Covers plan §8: issue does NOT change custody balance, issue to wrong unit
 * rejected, serial double-issue rejected, group holdings aggregation.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('v2 assignments API', () => {
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

  // Service + unit (+ warehouses), nomenclature, and place stock in the unit warehouse.
  async function seed(tag, { serialized = false, qty = 10 } = {}) {
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    const otherUnit = await postJson(api, '/api/structure/units', { name: `Рота Інша ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/structure/units/${otherUnit.id}`,
                 `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `${serialized ? 'АК' : 'Бушлат'} ${tag}`, service_id: svc.id,
      is_serialized: serialized, unit_of_measure: 'шт', price: 100,
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    // persons in the unit
    const p1 = await postJson(api, '/api/settings/persons', {
      first_name: 'Боєць', last_name: `Один-${tag}`, unit_id: unit.id,
    })
    const pOther = await postJson(api, '/api/settings/persons', {
      first_name: 'Чужий', last_name: `Боєць-${tag}`, unit_id: otherUnit.id,
    })
    cleanup.push(`/api/settings/persons/${p1.id}`, `/api/settings/persons/${pOther.id}`)

    let instance = null
    if (serialized) {
      instance = await postJson(api, `/api/nomenclature/${nom.id}/instances`, { serial_no: `AK-${tag}` })
      // receipt to service, transfer to unit warehouse
      await postJson(api, '/api/custody/movements', {
        date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id,
        instance_id: instance.id, to_warehouse_id: svcWh.id,
      })
      await postJson(api, '/api/custody/movements', {
        date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id,
        instance_id: instance.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id,
      })
    } else {
      await postJson(api, '/api/custody/movements', {
        date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id,
        to_warehouse_id: svcWh.id, quantity: qty, is_official: true,
      })
      await postJson(api, '/api/custody/movements', {
        date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id,
        from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: qty, is_official: true,
      })
    }
    return { svc, unit, otherUnit, svcWh, unitWh, nom, p1, pOther, instance }
  }

  test('issuing to a person does NOT change the custody balance', async () => {
    const tag = `a-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { qty: 10 })

    const before = await api.get(`/api/custody/balances?warehouse_id=${s.unitWh.id}`).then(r => r.json())
    expect(Number(before.find(b => b.nomenclature_id === s.nom.id).qty)).toBe(10)

    await postJson(api, '/api/assignments', {
      warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id,
      quantity: 3, is_official: true, issued_date: '2026-07-03',
    })

    // custody balance unchanged — майно лишилось у подотчіті складу
    const after = await api.get(`/api/custody/balances?warehouse_id=${s.unitWh.id}`).then(r => r.json())
    expect(Number(after.find(b => b.nomenclature_id === s.nom.id).qty)).toBe(10)
  })

  test('cannot over-issue beyond warehouse balance', async () => {
    const tag = `ov-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { qty: 2 })
    const resp = await api.post('/api/assignments', {
      data: { warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id, quantity: 5 },
    })
    expect(resp.status()).toBe(400)
  })

  test('issue to a person from another unit rejected', async () => {
    const tag = `wu-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { qty: 5 })
    const resp = await api.post('/api/assignments', {
      data: { warehouse_id: s.unitWh.id, person_id: s.pOther.id, nomenclature_id: s.nom.id, quantity: 1 },
    })
    expect(resp.status()).toBe(400)
  })

  test('serial: double-issue rejected; return frees it', async () => {
    const tag = `sd-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { serialized: true })

    const a1 = await postJson(api, '/api/assignments', {
      warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id, instance_id: s.instance.id,
    })
    // second active issue of the same instance → 400
    const dup = await api.post('/api/assignments', {
      data: { warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id, instance_id: s.instance.id },
    })
    expect(dup.status()).toBe(400)

    // return → can issue again
    await api.post(`/api/assignments/${a1.id}/return`, {})
    const a2 = await postJson(api, '/api/assignments', {
      warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id, instance_id: s.instance.id,
    })
    expect(a2.is_active).toBe(true)
  })

  test('group holdings aggregate across members', async () => {
    const tag = `g-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const s = await seed(tag, { qty: 10 })
    // group in the unit with p1 as commander
    const group = await postJson(api, '/api/structure/groups', {
      name: `Група ${tag}`, unit_id: s.unit.id, commander_id: s.p1.id,
    })
    cleanup.push(`/api/structure/groups/${group.id}`)
    // second member in the same unit
    const p2 = await postJson(api, '/api/settings/persons', {
      first_name: 'Боєць', last_name: `Два-${tag}`, unit_id: s.unit.id,
    })
    cleanup.push(`/api/settings/persons/${p2.id}`)
    // both persons join the group
    await api.put(`/api/settings/persons/${s.p1.id}`, { data: { group_id: group.id } })
    await api.put(`/api/settings/persons/${p2.id}`, { data: { group_id: group.id } })

    await postJson(api, '/api/assignments', {
      warehouse_id: s.unitWh.id, person_id: s.p1.id, nomenclature_id: s.nom.id, quantity: 2,
    })
    await postJson(api, '/api/assignments', {
      warehouse_id: s.unitWh.id, person_id: p2.id, nomenclature_id: s.nom.id, quantity: 3,
    })

    const holdings = await api.get(`/api/assignments/group/${group.id}`).then(r => r.json())
    expect(holdings.total_items).toBe(2)
    expect(holdings.members).toHaveLength(2)
    const commander = holdings.members.find(m => m.is_commander)
    expect(commander.person_id).toBe(s.p1.id)
  })
})
