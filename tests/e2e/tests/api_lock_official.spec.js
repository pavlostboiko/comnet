/**
 * is_official (облік/ндм) is a CARD property. While the card is unused it may be
 * changed and cascades to its instances; once there are movements/assignments
 * the type is frozen (changing it would split balances). Source of truth = card.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('is_official: changeable+cascades while unused, frozen once in circulation', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const svcWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.service_id === svc.id && w.type === 'service')
    // serial card as облік + an unplaced instance (no movement yet)
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: true, is_official: true, unit_of_measure: 'шт' } }).then(r => r.json())
    const inst = await api.post(`/api/nomenclature/${nom.id}/instances`, { data: { serial_no: `${S}-1` } }).then(r => r.json())
    expect(inst.is_official).toBe(true)

    // Unused → can flip to НДМ; cascades to the instance
    const upd = await api.put(`/api/nomenclature/${nom.id}`, { data: { is_official: false } })
    expect(upd.ok()).toBe(true)
    expect((await upd.json()).is_official).toBe(false)
    const insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts.find(i => i.id === inst.id).is_official).toBe(false)   // cascaded

    // Put it into circulation (receipt movement places the instance)
    await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: svcWh.id, nomenclature_id: nom.id, instance_id: inst.id, date: '2026-07-10' } })

    // Now the type is frozen
    const frozen = await api.put(`/api/nomenclature/${nom.id}`, { data: { is_official: true } })
    expect(frozen.status()).toBe(400)
    expect((await frozen.json()).detail).toContain('рухи')
    // unchanged
    expect((await api.get('/api/nomenclature').then(r => r.json())).find(n => n.id === nom.id).is_official).toBe(false)

    // Non-official edits (e.g. price) still work while in circulation
    const ok = await api.put(`/api/nomenclature/${nom.id}`, { data: { price: '123.45' } })
    expect(ok.ok()).toBe(true)
  } finally {
    await api.dispose()
  }
})
