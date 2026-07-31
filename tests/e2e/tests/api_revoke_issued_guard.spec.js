/**
 * Відкликання руху не має лишати майно «виданим» після повернення на попередній
 * склад: якщо по руху є активна видача — 400, поки її не повернуть. Видача
 * баланс НЕ рухає, тож старий гард «майно розійшлося далі» цього не ловив.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson } = require('./helpers/seed')

test('revoking a movement is blocked while the goods are issued', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await postJson(api, '/api/settings/services', { name: `RevSvc${S}` })
    const unit = await postJson(api, '/api/structure/units', { name: `RevРота${S}` })
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const person = await postJson(api, '/api/settings/persons',
      { last_name: `Боєць${S}`, first_name: 'І', unit_id: unit.id })

    // ── Серійне: рух + видача екземпляра ──────────────────────────────────
    const serNom = await postJson(api, '/api/nomenclature',
      { name: `РевСер${S}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт' })
    const inst = await postJson(api, `/api/nomenclature/${serNom.id}/instances`,
      { serial_no: `SNR-${S}` })
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt',
      nomenclature_id: serNom.id, instance_id: inst.id, to_warehouse_id: svcWh.id, quantity: 1 })
    const serMv = await postJson(api, '/api/custody/movements', { date: '2026-07-05', type: 'transfer',
      nomenclature_id: serNom.id, instance_id: inst.id,
      from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 1 })
    const serAsg = await postJson(api, '/api/assignments', { warehouse_id: unitWh.id,
      person_id: person.id, nomenclature_id: serNom.id, instance_id: inst.id,
      quantity: 1, issued_date: '2026-07-05' })

    const blocked = await api.delete(`/api/custody/movements/${serMv.id}`)
    expect(blocked.status()).toBe(400)
    expect(await blocked.text()).toContain('видане особі')

    // Екземпляр лишився на складі-отримувачі (відкату не було)
    const serial = await api.get(`/api/custody/serial?warehouse_id=${unitWh.id}`).then(r => r.json())
    expect(serial.some(s => s.serial_no === `SNR-${S}`)).toBe(true)

    // Повернули від особи → відкликання проходить
    await postJson(api, `/api/assignments/${serAsg.id}/return`, { returned_date: '2026-07-06' })
    const ok = await api.delete(`/api/custody/movements/${serMv.id}`)
    expect(ok.status()).toBe(200)

    // ── Несерійне: блокує лише те, що реально на руках ────────────────────
    const nom = await postJson(api, '/api/nomenclature',
      { name: `РевНС${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' })
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt',
      nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    const mkTransfer = (qty) => postJson(api, '/api/custody/movements',
      { date: '2026-07-05', type: 'transfer', nomenclature_id: nom.id,
        from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: qty })
    const mvA = await mkTransfer(3)
    const mvB = await mkTransfer(2)          // на складі підрозділу 5
    await postJson(api, '/api/assignments', { warehouse_id: unitWh.id, person_id: person.id,
      nomenclature_id: nom.id, quantity: 3, issued_date: '2026-07-05' })

    // 5 − 2 = 3 ≥ 3 виданих → відкликання дозволене
    const partial = await api.delete(`/api/custody/movements/${mvB.id}`)
    expect(partial.status()).toBe(200)
    // 3 − 3 = 0 < 3 виданих → блокуємо
    const tooMuch = await api.delete(`/api/custody/movements/${mvA.id}`)
    expect(tooMuch.status()).toBe(400)
    expect(await tooMuch.text()).toContain('видане особі')
  } finally {
    await api.dispose()
  }
})
