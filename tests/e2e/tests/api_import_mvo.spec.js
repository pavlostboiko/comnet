/**
 * Task 2b: movements import reads МВО from columns J (from) / K (to) and builds
 * the warehouse МВО journal with date ranges (change closes the previous period).
 * Persons must pre-exist; unknown names are reported.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

function up(api, url, fixture) {
  return api.post(url, {
    multipart: {
      file: { name: 'f.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        buffer: fs.readFileSync(path.join(__dirname, 'fixtures', fixture)) },
    },
  })
}

test('movements import builds МВО journal ranges from J/K', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // МВО persons must exist before import
    const pS = await api.post('/api/settings/persons', { data: { last_name: 'МвоСлужбаQZ' } }).then(r => r.json())
    const pA = await api.post('/api/settings/persons', { data: { last_name: 'МвоАльфаQZ' } }).then(r => r.json())
    const pB = await api.post('/api/settings/persons', { data: { last_name: 'МвоБетаQZ' } }).then(r => r.json())

    await up(api, '/api/admin/v2/import/items', 'import_v2_mvo_items.xlsx')
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_mvo_mv.xlsx').then(r => r.json())
    expect(mv.mvo_created).toBeGreaterThanOrEqual(3)   // service(1) + rota(2)

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.name === 'Склад РотаМвоQZ')
    expect(rotaWh).toBeTruthy()

    const mvo = await api.get('/api/structure/mvo').then(r => r.json())
    const rota = mvo.filter(m => m.warehouse_id === rotaWh.id).sort((a, b) => a.from_date.localeCompare(b.from_date))
    expect(rota).toHaveLength(2)
    // first period closed the day before the next; second is active
    expect(rota[0]).toMatchObject({ person_id: pA.id, from_date: '2026-03-01', to_date: '2026-04-30' })
    expect(rota[1]).toMatchObject({ person_id: pB.id, from_date: '2026-05-01', to_date: null })

    // service warehouse got its (single) active МВО
    const svcWh = whs.find(w => w.name === 'Склад СлужбаМвоQZ')
    const svc = mvo.filter(m => m.warehouse_id === svcWh.id)
    expect(svc).toHaveLength(1)
    expect(svc[0]).toMatchObject({ person_id: pS.id, to_date: null })
  } finally {
    await api.dispose()
  }
})
