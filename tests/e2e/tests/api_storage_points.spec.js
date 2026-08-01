/**
 * Точки зберігання: фізичне розміщення всередині складу. Довідкова вісь —
 * баланси й документи не змінюються. Серійне — точка на екземплярі, несерійне —
 * позначка на (картка, склад). Переїзд на інший склад точку скидає.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('storage points: assign to serial + non-serial, reset on transfer, guards', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `sp-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `SPSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `SPРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)

    // Довідник: дві точки на складі служби + одна на складі підрозділу
    const box1 = await postJson(api, '/api/structure/storage-points', { name: 'Бокс 1', warehouse_id: svcWh.id })
    const box2 = await postJson(api, '/api/structure/storage-points', { name: 'Бокс 2', warehouse_id: svcWh.id })
    const garage = await postJson(api, '/api/structure/storage-points', { name: 'Гараж', warehouse_id: unitWh.id })
    expect(box1.warehouse_id).toBe(svcWh.id)

    // Назва унікальна в межах складу; на іншому складі така сама — можна
    const dup = await api.post('/api/structure/storage-points', { data: { name: 'Бокс 1', warehouse_id: svcWh.id } })
    expect(dup.status()).toBe(409)
    const sameNameElsewhere = await api.post('/api/structure/storage-points', { data: { name: 'Бокс 1', warehouse_id: unitWh.id } })
    expect(sameNameElsewhere.status()).toBe(201)
    await api.delete(`/api/structure/storage-points/${(await sameNameElsewhere.json()).id}`)

    // Список фільтрується за складом
    const svcPoints = await api.get(`/api/structure/storage-points?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(svcPoints.map(p => p.name).sort()).toEqual(['Бокс 1', 'Бокс 2'])

    // ── Серійне ───────────────────────────────────────────────────────────
    const serNom = await postJson(api, '/api/nomenclature',
      { name: `SPСер ${tag}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${serNom.id}`)
    const inst = await postJson(api, `/api/nomenclature/${serNom.id}/instances`, { serial_no: `SPSN-${tag}` })
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt',
      nomenclature_id: serNom.id, instance_id: inst.id, to_warehouse_id: svcWh.id, quantity: 1 })

    await api.put(`/api/nomenclature/${serNom.id}/instances/${inst.id}`, { data: { storage_point_id: box1.id } })
    let serial = await api.get(`/api/custody/serial?warehouse_id=${svcWh.id}`).then(r => r.json())
    let row = serial.find(s => s.serial_no === `SPSN-${tag}`)
    expect(row.storage_point).toBe('Бокс 1')

    // Точку з ЧУЖОГО складу поставити не можна
    const wrong = await api.put(`/api/nomenclature/${serNom.id}/instances/${inst.id}`,
      { data: { storage_point_id: garage.id } })
    expect(wrong.status()).toBe(400)

    // Переїзд на інший склад скидає точку (вона належала старому складу)
    await postJson(api, '/api/custody/movements', { date: '2026-07-05', type: 'transfer',
      nomenclature_id: serNom.id, instance_id: inst.id,
      from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 1 })
    serial = await api.get(`/api/custody/serial?warehouse_id=${unitWh.id}`).then(r => r.json())
    row = serial.find(s => s.serial_no === `SPSN-${tag}`)
    expect(row.storage_point_id).toBeNull()

    // ── Несерійне: позначка на (картка, склад) ───────────────────────────
    const nom = await postJson(api, '/api/nomenclature',
      { name: `SPНС ${tag}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt',
      nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 8 })
    await api.put('/api/custody/stock-point', { data: {
      nomenclature_id: nom.id, warehouse_id: svcWh.id, storage_point_id: box2.id } })
    let bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    let line = bal.find(b => b.nomenclature_id === nom.id)
    expect(line.storage_point).toBe('Бокс 2')
    expect(line.qty).toBe('8.0000')                    // баланс не змінився

    // Чужа точка — 400; серійній картці позначку не ставимо
    const badWh = await api.put('/api/custody/stock-point', { data: {
      nomenclature_id: nom.id, warehouse_id: svcWh.id, storage_point_id: garage.id } })
    expect(badWh.status()).toBe(400)
    const badKind = await api.put('/api/custody/stock-point', { data: {
      nomenclature_id: serNom.id, warehouse_id: svcWh.id, storage_point_id: box1.id } })
    expect(badKind.status()).toBe(400)

    // null прибирає позначку
    await api.put('/api/custody/stock-point', { data: {
      nomenclature_id: nom.id, warehouse_id: svcWh.id, storage_point_id: null } })
    bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(bal.find(b => b.nomenclature_id === nom.id).storage_point_id).toBeNull()

    // service-юзер не ставить точку чужій службі (як і для точки на екземплярі)
    const otherSvc = await postJson(api, '/api/settings/services', { name: `SPSvcB ${tag}` })
    cleanup.push(`/api/settings/services/${otherSvc.id}`)
    const uname = `spuser-${tag}`
    await postJson(api, '/api/users', { username: uname, password: 'test1234',
                                        role: 'service', service_id: otherSvc.id })
    const svcApi = await loginApi(request, { user: uname, pass: 'test1234' })
    const foreign = await svcApi.put('/api/custody/stock-point', { data: {
      nomenclature_id: nom.id, warehouse_id: svcWh.id, storage_point_id: box2.id } })
    expect(foreign.status()).toBe(403)
    await svcApi.dispose()

    // Видалення точки не чіпає майно
    await api.put('/api/custody/stock-point', { data: {
      nomenclature_id: nom.id, warehouse_id: svcWh.id, storage_point_id: box2.id } })
    await api.delete(`/api/structure/storage-points/${box2.id}`)
    bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    line = bal.find(b => b.nomenclature_id === nom.id)
    expect(line.qty).toBe('8.0000')
    expect(line.storage_point_id).toBeNull()
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
