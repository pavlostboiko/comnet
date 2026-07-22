/**
 * v2 structure API — units, groups, warehouses (auto), mvo.
 *
 * Covers Phase 1 foundations: warehouse auto-create per service/unit,
 * МВО single-active-per-warehouse + type=unit invariants, group CRUD.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('v2 structure API', () => {
  let api
  let cleanup

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    cleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  })

  test('creating a unit auto-creates exactly one unit-warehouse', async () => {
    const tag = `u-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`)

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const mine = whs.filter(w => w.unit_id === unit.id)
    expect(mine).toHaveLength(1)
    expect(mine[0].type).toBe('unit')
    expect(mine[0].service_id).toBeNull()
  })

  test('creating a service auto-creates exactly one service-warehouse', async () => {
    const tag = `s-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const mine = whs.filter(w => w.service_id === svc.id)
    expect(mine).toHaveLength(1)
    expect(mine[0].type).toBe('service')
    expect(mine[0].unit_id).toBeNull()
  })

  test('duplicate unit name → 409', async () => {
    const tag = `dup-${Date.now()}`
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`)
    const resp = await api.post('/api/structure/units', { data: { name: `Рота ${tag}` } })
    expect(resp.status()).toBe(409)
  })

  test('group CRUD + commander link', async () => {
    const tag = `g-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`)
    const person = await postJson(api, '/api/settings/persons', {
      first_name: 'Гру', last_name: `Ком-${tag}`, position: 'Командир',
    })
    cleanup.push(`/api/settings/persons/${person.id}`)

    const group = await postJson(api, '/api/structure/groups', {
      name: `Група ${tag}`, unit_id: unit.id, commander_id: person.id,
    })
    cleanup.push(`/api/structure/groups/${group.id}`)
    expect(group.unit_id).toBe(unit.id)
    expect(group.commander_id).toBe(person.id)

    const list = await api.get('/api/structure/groups').then(r => r.json())
    expect(list.find(g => g.id === group.id)).toBeTruthy()
  })

  test('МВО: only on a unit-warehouse; one active per warehouse; rotation', async () => {
    const tag = `m-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`)
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const svcWh = whs.find(w => w.service_id === svc.id)

    const p1 = await postJson(api, '/api/settings/persons', { first_name: 'МВО', last_name: `Один-${tag}` })
    const p2 = await postJson(api, '/api/settings/persons', { first_name: 'МВО', last_name: `Два-${tag}` })
    cleanup.push(`/api/settings/persons/${p1.id}`, `/api/settings/persons/${p2.id}`)

    // Cannot assign МВО to a service warehouse
    const badResp = await api.post('/api/structure/mvo', {
      data: { warehouse_id: svcWh.id, person_id: p1.id, from_date: '2026-01-01' },
    })
    expect(badResp.status()).toBe(400)

    // Assign active МВО to the unit warehouse
    const m1 = await postJson(api, '/api/structure/mvo', {
      warehouse_id: unitWh.id, person_id: p1.id, from_date: '2026-01-01',
    })
    expect(m1.to_date).toBeNull()

    // Second active on the same warehouse → 409
    const dupResp = await api.post('/api/structure/mvo', {
      data: { warehouse_id: unitWh.id, person_id: p2.id, from_date: '2026-06-01' },
    })
    expect(dupResp.status()).toBe(409)

    // Rotation: close m1, then a new active is allowed
    await api.put(`/api/structure/mvo/${m1.id}`, { data: { to_date: '2026-06-30' } })
    const m2 = await postJson(api, '/api/structure/mvo', {
      warehouse_id: unitWh.id, person_id: p2.id, from_date: '2026-07-01',
    })
    expect(m2.to_date).toBeNull()

    // Current active is p2
    const rows = await api.get('/api/structure/mvo').then(r => r.json())
    const active = rows.filter(m => m.warehouse_id === unitWh.id && m.to_date === null)
    expect(active).toHaveLength(1)
    expect(active[0].person_id).toBe(p2.id)
  })
})
