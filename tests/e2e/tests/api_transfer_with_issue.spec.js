/**
 * "Додати переміщення" can optionally issue each line to a person on the
 * destination unit — one atomic transaction with the movement. The person is
 * NOT written to any document (assignment is a separate layer). A person from a
 * different unit rolls back the whole batch (nothing moved, nothing issued).
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

const S = 'TXISS'

test('transfer batch issues to a destination-unit person atomically', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkUnit = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      const whs = await api.get('/api/structure/warehouses').then(r => r.json())
      return { unit: u, wh: whs.find(w => w.unit_id === u.id) }
    }
    const A = await mkUnit('A'), B = await mkUnit('B'), C = await mkUnit('C')
    // Person on B's unit (valid) and on C's unit (wrong for a B transfer)
    const pB = await api.post('/api/settings/persons', { data: { last_name: `Бійць${S}`, unit_id: B.unit.id } }).then(r => r.json())
    const pC = await api.post('/api/settings/persons', { data: { last_name: `Чужий${S}`, unit_id: C.unit.id } }).then(r => r.json())

    // Stock at A
    await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: A.wh.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' } })

    // Atomic rollback: transfer A→B issuing to a person from the WRONG unit → 400, nothing happens
    const bad = await api.post('/api/custody/document', { data: {
      date: '2026-07-02', from_warehouse_id: A.wh.id, to_warehouse_id: B.wh.id,
      items: [{ nomenclature_id: nom.id, quantity: 2, assign_person_id: pC.id }] } })
    expect(bad.status()).toBe(400)
    const balB0 = await api.get(`/api/custody/balances?warehouse_id=${B.wh.id}`).then(r => r.json())
    expect(balB0.find(b => b.nomenclature_id === nom.id)).toBeUndefined()  // nothing moved
    expect(await api.get(`/api/assignments?warehouse_id=${B.wh.id}`).then(r => r.json())).toHaveLength(0)

    // Happy path: transfer A→B and issue to a B-unit person in one call
    const ok = await api.post('/api/custody/document', { data: {
      date: '2026-07-03', from_warehouse_id: A.wh.id, to_warehouse_id: B.wh.id,
      items: [{ nomenclature_id: nom.id, quantity: 2, assign_person_id: pB.id }] } })
    expect(ok.ok()).toBe(true)

    // Moved (B has 2) and issued (assignment to pB, qty 2)
    const balB = await api.get(`/api/custody/balances?warehouse_id=${B.wh.id}`).then(r => r.json())
    expect(Number(balB.find(b => b.nomenclature_id === nom.id).qty)).toBe(2)
    const asg = await api.get(`/api/assignments?warehouse_id=${B.wh.id}`).then(r => r.json())
    expect(asg).toHaveLength(1)
    expect(asg[0].person_id).toBe(pB.id)
    expect(Number(asg[0].quantity)).toBe(2)
  } finally {
    await api.dispose()
  }
})

const S2 = 'TXISM'

test('serial transfer issues the instance to a destination-unit person atomically', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S2}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Рація${S2}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkUnit = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S2}-${n}` } }).then(r => r.json())
      const whs = await api.get('/api/structure/warehouses').then(r => r.json())
      return { unit: u, wh: whs.find(w => w.unit_id === u.id) }
    }
    const A = await mkUnit('A'), B = await mkUnit('B'), C = await mkUnit('C')
    const pB = await api.post('/api/settings/persons', { data: { last_name: `Бійць${S2}`, unit_id: B.unit.id } }).then(r => r.json())
    const pC = await api.post('/api/settings/persons', { data: { last_name: `Чужий${S2}`, unit_id: C.unit.id } }).then(r => r.json())

    const mkInstanceAtA = async (sn) => {
      const inst = await api.post(`/api/nomenclature/${nom.id}/instances`, { data: { serial_no: sn } }).then(r => r.json())
      await api.post('/api/custody/movements', { data: {
        type: 'receipt', to_warehouse_id: A.wh.id, nomenclature_id: nom.id, instance_id: inst.id, date: '2026-07-01' } })
      return inst
    }
    const instAt = (id) => api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
      .then(list => list.find(i => i.id === id).current_warehouse_id)

    // Wrong-unit person rolls back BOTH placement and assignment: instance stays at A
    const bad = await mkInstanceAtA(`${S2}-SER-BAD`)
    const rej = await api.post('/api/custody/document', { data: {
      date: '2026-07-02', from_warehouse_id: A.wh.id, to_warehouse_id: B.wh.id,
      items: [{ nomenclature_id: nom.id, instance_id: bad.id, assign_person_id: pC.id }] } })
    expect(rej.status()).toBe(400)
    expect(await instAt(bad.id)).toBe(A.wh.id)  // not moved
    expect(await api.get(`/api/assignments?warehouse_id=${B.wh.id}`).then(r => r.json())).toHaveLength(0)

    // Happy path: transfer the instance A→B and issue it to a B-unit person
    const good = await mkInstanceAtA(`${S2}-SER-OK`)
    const ok = await api.post('/api/custody/document', { data: {
      date: '2026-07-03', from_warehouse_id: A.wh.id, to_warehouse_id: B.wh.id,
      items: [{ nomenclature_id: nom.id, instance_id: good.id, assign_person_id: pB.id }] } })
    expect(ok.ok()).toBe(true)
    expect(await instAt(good.id)).toBe(B.wh.id)  // placed at destination
    const asg = await api.get(`/api/assignments?warehouse_id=${B.wh.id}`).then(r => r.json())
    expect(asg).toHaveLength(1)
    expect(asg[0].person_id).toBe(pB.id)
    expect(asg[0].instance_id).toBe(good.id)
  } finally {
    await api.dispose()
  }
})
