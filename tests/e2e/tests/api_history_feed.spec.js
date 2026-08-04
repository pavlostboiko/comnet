/**
 * Загальна історія (`/api/custody/feed`): рухи складів і видачі/повернення в
 * одній хронологічній стрічці, з фільтрами склад/дати та скоупом ролі.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('feed merges movements and assignments, filters by warehouse and dates', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `feed-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `FeedSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `FeedРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const person = await postJson(api, '/api/settings/persons',
      { last_name: `Боєць${tag}`, first_name: 'І', unit_id: unit.id })
    const nom = await postJson(api, '/api/nomenclature',
      { name: `FeedРіч ${tag}`, service_id: svc.id, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    await postJson(api, '/api/custody/movements', { date: '2026-03-01', type: 'receipt',
      nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    await postJson(api, '/api/custody/movements', { date: '2026-03-05', type: 'transfer',
      nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 4 })
    const asg = await postJson(api, '/api/assignments', { warehouse_id: unitWh.id, person_id: person.id,
      nomenclature_id: nom.id, quantity: 2, issued_date: '2026-03-06' })
    await postJson(api, `/api/assignments/${asg.id}/return`, { returned_date: '2026-03-20' })

    const ours = (feed) => feed.events.filter(e => e.nomenclature_id === nom.id)

    // Уся стрічка: 2 рухи + видано + повернуто, новіші зверху
    const all = await api.get('/api/custody/feed').then(r => r.json())
    const mine = ours(all)
    expect(mine.map(e => e.kind === 'movement' ? e.type : e.kind))
      .toEqual(['returned', 'issued', 'transfer', 'receipt'])
    expect(mine[0].person).toContain(`Боєць${tag}`)
    expect(mine.find(e => e.type === 'transfer').from_warehouse).toBe(svcWh.name)
    expect(mine.find(e => e.kind === 'issued').nomenclature_name).toBe(`FeedРіч ${tag}`)

    // Фільтр складу: склад служби бачить лише свої два рухи (видача — на складі підрозділу)
    const bySvcWh = ours(await api.get(`/api/custody/feed?warehouse_id=${svcWh.id}`).then(r => r.json()))
    expect(bySvcWh.map(e => e.type).sort()).toEqual(['receipt', 'transfer'])

    // Фільтр дат — по КОЖНІЙ події: 06.03–31.03 лишає видано+повернуто
    const byDate = ours(await api.get('/api/custody/feed?date_from=2026-03-06&date_to=2026-03-31').then(r => r.json()))
    expect(byDate.map(e => e.kind).sort()).toEqual(['issued', 'returned'])

    // Скоуп ролі: service-юзер чужої служби не бачить нічого нашого
    const other = await postJson(api, '/api/settings/services', { name: `FeedOther ${tag}` })
    cleanup.push(`/api/settings/services/${other.id}`)
    const uname = `feeduser-${tag}`
    await postJson(api, '/api/users', { username: uname, password: 'test1234', role: 'service', service_id: other.id })
    const svcApi = await loginApi(request, { user: uname, pass: 'test1234' })
    const foreign = await svcApi.get('/api/custody/feed').then(r => r.json())
    expect(ours(foreign)).toHaveLength(0)
    await svcApi.dispose()
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
