/**
 * «Служба забезпечення» документа виводиться з майна документа, а не вибирається
 * користувачем: позиції однієї служби → її і проставляємо (payload ігнорується);
 * позиції кількох служб → єдиної служби нема, поле лишається порожнім.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

async function deleteDocs(api, ids) {
  for (const id of ids) {
    try { await api.post(`/api/custody/documents/${id}/unsign`) } catch (_e) { /* draft */ }
    try { await api.delete(`/api/custody/documents/${id}`) } catch (_e) { /* swallow */ }
  }
}

test('document service comes from its items, not from the payload', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  const docIds = []
  try {
    const tag = `dsvc-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svcA = await postJson(api, '/api/settings/services', { name: `DSvcA ${tag}` })
    const svcB = await postJson(api, '/api/settings/services', { name: `DSvcB ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `DSvcРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`,
                 `/api/settings/services/${svcA.id}`, `/api/settings/services/${svcB.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svcA.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)

    // Дві картки служби A і одна служби B — усі лежать на складі служби A
    const mkNom = async (name, serviceId) => {
      const n = await postJson(api, '/api/nomenclature',
        { name: `${name} ${tag}`, service_id: serviceId, unit_of_measure: 'шт', price: 10 })
      cleanup.push(`/api/nomenclature/${n.id}`)
      await postJson(api, '/api/custody/movements',
        { date: '2026-07-01', type: 'receipt', nomenclature_id: n.id, to_warehouse_id: svcWh.id, quantity: 20 })
      return n
    }
    const nomA1 = await mkNom('DA1', svcA.id)
    const nomA2 = await mkNom('DA2', svcA.id)
    const nomB1 = await mkNom('DB1', svcB.id)

    const mkMove = (nomId) => postJson(api, '/api/custody/movements',
      { date: '2026-07-05', type: 'transfer', nomenclature_id: nomId,
        from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 2 })
    const mvA1 = await mkMove(nomA1.id)
    const mvA2 = await mkMove(nomA2.id)
    const mvA3 = await mkMove(nomA1.id)
    const mvB1 = await mkMove(nomB1.id)

    // Одна служба в позиціях → проставляється вона, навіть якщо в payload інша
    const doc = await postJson(api, '/api/custody/documents', {
      operation: 'transfer', form: 'накладна', doc_date: '2026-07-05',
      service_id: svcB.id, movement_ids: [mvA1.id, mvA2.id],
    })
    docIds.push(doc.id)
    expect(doc.service_id).toBe(svcA.id)
    expect(doc.extra_data.snap_service_name).toBe(`DSvcA ${tag}`)
    expect(doc.lines.map(l => l.service_id)).toEqual([svcA.id, svcA.id])   // для UI-мітки
    expect(doc.extra_data.total_qty_words).toBeTruthy()   // snap бачить свіжі позиції

    // Позиції різних служб → єдиної служби нема, поле лишається порожнім (не 500)
    const mixed = await postJson(api, '/api/custody/documents', {
      operation: 'transfer', form: 'накладна', doc_date: '2026-07-05',
      movement_ids: [mvA3.id, mvB1.id],
    })
    docIds.push(mixed.id)
    expect(mixed.service_id).toBeNull()
    expect(mixed.extra_data.snap_service_name).toBeUndefined()

    // Прибрали чужу позицію → служба з'явилась сама
    const fixed = await api.put(`/api/custody/documents/${mixed.id}`, {
      data: { operation: 'transfer', form: 'накладна', doc_date: '2026-07-05',
              movement_ids: [mvA3.id] },
    }).then(r => r.json())
    expect(fixed.service_id).toBe(svcA.id)

    // Приймання ззовні: служба теж із картки, а не зі складу/payload
    const recv = await postJson(api, '/api/custody/documents/receive', {
      to_warehouse_id: unitWh.id, form: 'накладна', doc_date: '2026-07-06',
      counterparty: `Постачальник ${tag}`, service_id: svcB.id,
      items: [{ nomenclature_id: nomA1.id, quantity: 3 }],
    })
    docIds.push(recv.id)
    expect(recv.service_id).toBe(svcA.id)
  } finally {
    await deleteDocs(api, docIds)
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
