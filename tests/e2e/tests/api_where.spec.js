/**
 * GET /api/custody/where?nomenclature_id= — «де знаходиться» майно.
 * Non-serial → qty per warehouse; serial → each instance + warehouse + holder.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('where-is: non-serial distribution across warehouses', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `wh-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `WhSvc ${tag}` })
    const u1 = await postJson(api, '/api/structure/units', { name: `WhРота ${tag}` })
    cleanup.push(`/api/structure/units/${u1.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === u1.id)
    const nom = await postJson(api, '/api/nomenclature', { name: `Ноутбук ${tag}`, service_id: svc.id, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    // 10 into service wh, transfer 4 → unit
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    await postJson(api, '/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 4 })

    const where = await api.get(`/api/custody/where?nomenclature_id=${nom.id}`).then(r => r.json())
    expect(where.is_serialized).toBe(false)
    const svcLine = where.nonserial.find(x => x.warehouse_id === svcWh.id)
    const unitLine = where.nonserial.find(x => x.warehouse_id === unitWh.id)
    expect(Number(svcLine.qty)).toBe(6)
    expect(Number(unitLine.qty)).toBe(4)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
