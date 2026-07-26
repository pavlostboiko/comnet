/** Instance note: update + surfaced in /custody/serial. */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson } = require('./helpers/seed')

test('serial instance note: update + shown in serial list', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `note-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `NoteSvc ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const nom = await postJson(api, '/api/nomenclature', { name: `Рація ${tag}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    const inst = await postJson(api, `/api/nomenclature/${nom.id}/instances`, { serial_no: `SN-${tag}` })
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, instance_id: inst.id, to_warehouse_id: svcWh.id })

    const upd = await api.put(`/api/nomenclature/${nom.id}/instances/${inst.id}`, { data: { note: 'потребує ремонту' } })
    expect(upd.status()).toBe(200)
    expect((await upd.json()).note).toBe('потребує ремонту')

    const insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts[0].note).toBe('потребує ремонту')

    const serial = await api.get(`/api/custody/serial?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(serial.find(s => s.instance_id === inst.id).note).toBe('потребує ремонту')
  } finally {
    const { bestEffortDelete } = require('./helpers/seed')
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
