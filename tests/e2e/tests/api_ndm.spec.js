/**
 * НДМ (не облікове майно):
 *  - «без документа» receipt → receipt movements without a custody_document;
 *  - issue НДМ directly from a SERVICE warehouse to ANY person (no unit binding);
 *  - облік (is_official) may NOT be issued from a service warehouse.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('НДМ receipt without document + direct issue from service warehouse', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: { name: `SvcNDM-${S}` } }).then(r => r.json())
    const svcWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.service_id === svc.id && w.type === 'service')
    const mkNom = (official, tag) => api.post('/api/nomenclature', { data: {
      name: `${tag}-${S}`, service_id: svc.id, is_serialized: false, is_official: official, unit_of_measure: 'шт' } }).then(r => r.json())
    const nomNdm = await mkNom(false, 'НДМ')
    const nomOff = await mkNom(true, 'Облік')
    // person in some unit — НДМ can go to anyone regardless of unit
    const unit = await api.post('/api/structure/units', { data: { name: `U-${S}` } }).then(r => r.json())
    const person = await api.post('/api/settings/persons', { data: { last_name: `Особа-${S}`, unit_id: unit.id } }).then(r => r.json())

    // Receipt without document (НДМ) + also stock some облік the same informal way
    const rec = await api.post('/api/custody/documents/receive', { data: {
      to_warehouse_id: svcWh.id, form: 'без документа', doc_date: '2026-07-10',
      items: [{ nomenclature_id: nomNdm.id, quantity: 4 }, { nomenclature_id: nomOff.id, quantity: 3 }] } }).then(r => r.json())
    expect(rec.no_document).toBe(true)

    // No custody_document created; movements exist with document_id = null
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    const ndmMv = movements.find(m => m.nomenclature_id === nomNdm.id && m.type === 'receipt')
    expect(ndmMv).toBeTruthy()
    expect(ndmMv.document_id ?? null).toBeNull()

    // Balance rose on the service warehouse
    const bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(Number(bal.find(b => b.nomenclature_id === nomNdm.id).qty)).toBe(4)

    // Issue НДМ from the SERVICE warehouse to a person of another unit → OK
    const asg = await api.post('/api/assignments', { data: {
      warehouse_id: svcWh.id, person_id: person.id, nomenclature_id: nomNdm.id, quantity: 2 } })
    expect(asg.status()).toBe(201)
    const asgRow = await asg.json()

    // Surfaces in the person's holdings (the «Видане на особу» report source)
    const held = await api.get(`/api/assignments?person_id=${person.id}`).then(r => r.json())
    expect(held.some(x => x.id === asgRow.id)).toBe(true)

    // Return it → returned_date set; no longer active for the person
    const ret = await api.post(`/api/assignments/${asgRow.id}/return`)
    expect(ret.ok()).toBe(true)
    expect((await ret.json()).returned_date).toBeTruthy()
    const heldAfter = await api.get(`/api/assignments?person_id=${person.id}`).then(r => r.json())
    expect(heldAfter.some(x => x.id === asgRow.id)).toBe(false)

    // облік may NOT be issued from a service warehouse
    const bad = await api.post('/api/assignments', { data: {
      warehouse_id: svcWh.id, person_id: person.id, nomenclature_id: nomOff.id, quantity: 1 } })
    expect(bad.status()).toBe(400)
    expect((await bad.json()).detail).toContain('підрозділу')
  } finally {
    await api.dispose()
  }
})
