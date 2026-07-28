/**
 * Audit log: any ORM create/update/delete on a tracked entity is recorded
 * automatically (after_flush hook), with the acting user and a field diff.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('audit records create + update with field diff and acting user', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const name0 = `AuditSvc-${Date.now()}`
    const name1 = `${name0}-ren`
    const svc = await api.post('/api/settings/services', { data: { name: name0 } }).then(r => r.json())
    await api.put(`/api/settings/services/${svc.id}`, { data: { name: name1 } })

    const log = await api.get(`/api/audit?entity_type=Service&entity_id=${svc.id}`).then(r => r.json())
    const create = log.items.find(x => x.action === 'create')
    const update = log.items.find(x => x.action === 'update')

    expect(create).toBeTruthy()
    expect(create.username).toBe('admin')
    expect(create.changes.name).toEqual([null, name0])

    expect(update).toBeTruthy()
    expect(update.changes.name).toEqual([name0, name1])
    expect(update.username).toBe('admin')

    // meta lists Service among tracked entity types
    const meta = await api.get('/api/audit/meta').then(r => r.json())
    expect(meta.entity_types).toContain('Service')
    expect(meta.actions).toEqual(expect.arrayContaining(['create', 'update']))
  } finally {
    await api.dispose()
  }
})

test('audit records a movement create', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = `AUDMV-${Date.now()}`
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const u = await api.post('/api/structure/units', { data: { name: `U${S}` } }).then(r => r.json())
    const wh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
    const mv = await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: wh.id, nomenclature_id: nom.id, quantity: 3, date: '2026-07-10' } }).then(r => r.json())

    const log = await api.get(`/api/audit?entity_type=CustodyMovement&entity_id=${mv.id}`).then(r => r.json())
    const create = log.items.find(x => x.action === 'create')
    expect(create).toBeTruthy()
    expect(create.changes.type).toEqual([null, 'receipt'])
    expect(create.username).toBe('admin')
  } finally {
    await api.dispose()
  }
})

test('non-admin cannot read the audit log', async ({ request }) => {
  const admin = await loginApi(request)
  const username = `op-audit-${Date.now()}`
  try {
    await admin.post('/api/users', { data: { username, password: 'test1234', role: 'service' } })
    const opApi = await loginApi(request, { user: username, pass: 'test1234' })
    const res = await opApi.get('/api/audit')
    expect(res.status()).toBe(403)
    await opApi.dispose()
  } finally {
    await admin.dispose()
  }
})
