/**
 * POST /api/custody/document — накладна на переміщення (N позицій одним номером).
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('batch document: 5 positions service → unit under one doc number', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `doc-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `DocSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `DocРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)

    // 5 non-serial nomenclatures, each received 10 into the service warehouse
    const noms = []
    for (let k = 0; k < 5; k++) {
      const n = await postJson(api, '/api/nomenclature', { name: `Поз${k} ${tag}`, service_id: svc.id, unit_of_measure: 'шт' })
      cleanup.push(`/api/nomenclature/${n.id}`)
      await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: n.id, to_warehouse_id: svcWh.id, quantity: 10 })
      noms.push(n)
    }

    // One document: transfer 2 of each to the unit
    const resp = await api.post('/api/custody/document', {
      data: {
        date: '2026-07-05', from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, doc_number: `Н-${tag}`,
        items: noms.map(n => ({ nomenclature_id: n.id, quantity: 2 })),
      },
    })
    expect(resp.status()).toBe(201)
    const body = await resp.json()
    expect(body.created).toBe(5)

    // Unit warehouse now has 2 of each; all under one doc_number
    const bal = await api.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(bal.filter(b => noms.some(n => n.id === b.nomenclature_id))).toHaveLength(5)
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    expect(movements.filter(m => m.doc_number === `Н-${tag}`)).toHaveLength(5)

    // Insufficient position → whole document rejected (atomic)
    const bad = await api.post('/api/custody/document', {
      data: {
        date: '2026-07-06', from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, doc_number: `Н2-${tag}`,
        items: [{ nomenclature_id: noms[0].id, quantity: 999 }],
      },
    })
    expect(bad.status()).toBe(400)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
