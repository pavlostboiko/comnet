/**
 * Начальник служби — третій вид запису в журналі підписантів (kind='service_chief',
 * прив'язка до служби). Snap документа бере його з журналу НА ДАТУ документа;
 * поки службу в журнал не завели — фолбек на вільний текст services.chief_*.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('service chief is journaled per service and snapped by document date', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: {
      name: `ChiefSvc${S}`, chief_name: `Старий текст${S}`, chief_position: 'Стара посада' } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkWh = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      return (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
    }
    const whA = await mkWh('A'), whB = await mkWh('B')
    const mkPerson = (ln) => api.post('/api/settings/persons', { data: { last_name: ln, first_name: 'Ів' } }).then(r => r.json())

    await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, quantity: 9, date: '2026-01-01' } })
    const mkDoc = async (dateStr) => {
      const mv = await api.post('/api/custody/movements', { data: {
        type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id,
        nomenclature_id: nom.id, quantity: 1, date: dateStr } }).then(r => r.json())
      return api.post('/api/custody/documents', { data: {
        operation: 'transfer', form: 'накладна', doc_number: `NKC-${S}-${dateStr}`,
        doc_date: dateStr, movement_ids: [mv.id] } }).then(r => r.json())
    }

    // Журналу ще нема → фолбек на вільний текст картки служби
    const before = await mkDoc('2026-03-01')
    expect(before.extra_data.snap_service_chief_name).toBe(`Старий текст${S}`)
    expect(before.extra_data.snap_service_chief_post).toBe('Стара посада')

    // Двоє начальників по черзі: перший до 2026-05-31, другий з 2026-06-01
    const p1 = await mkPerson(`Начальник1${S}`)
    const p2 = await mkPerson(`Начальник2${S}`)
    const first = await api.post('/api/structure/mvo', { data: {
      kind: 'service_chief', service_id: svc.id, person_id: p1.id,
      position: `Начальник ${S}`, from_date: '2026-04-01', to_date: '2026-05-31' } }).then(r => r.json())
    expect(first.kind).toBe('service_chief')
    expect(first.service_id).toBe(svc.id)
    await api.post('/api/structure/mvo', { data: {
      kind: 'service_chief', service_id: svc.id, person_id: p2.id,
      position: `Начальник ${S}`, from_date: '2026-06-01' } })

    // Кожен документ бере начальника, діючого НА СВОЮ дату
    const inApril = await mkDoc('2026-04-15')
    expect(inApril.extra_data.snap_service_chief_name).toContain(`Начальник1${S}`.toUpperCase())
    expect(inApril.extra_data.snap_service_chief_post).toBe(`Начальник ${S}`)
    const inJuly = await mkDoc('2026-07-15')
    expect(inJuly.extra_data.snap_service_chief_name).toContain(`Начальник2${S}`.toUpperCase())

    // Другий діючий начальник тієї ж служби — 409; іншої служби — можна
    const dup = await api.post('/api/structure/mvo', { data: {
      kind: 'service_chief', service_id: svc.id, person_id: p1.id, from_date: '2026-07-01' } })
    expect(dup.status()).toBe(409)
    const svc2 = await api.post('/api/settings/services', { data: { name: `ChiefSvc2-${S}` } }).then(r => r.json())
    const other = await api.post('/api/structure/mvo', { data: {
      kind: 'service_chief', service_id: svc2.id, person_id: p1.id, from_date: '2026-07-01' } })
    expect(other.status()).toBe(201)

    // Без служби запис не створюється
    const noSvc = await api.post('/api/structure/mvo', { data: {
      kind: 'service_chief', person_id: p1.id, from_date: '2026-07-01' } })
    expect(noSvc.status()).toBe(400)
  } finally {
    await api.dispose()
  }
})
