/**
 * 3rd import step — issuance (assignments) from the Items file «Де» column
 * («<підрозділ> [Прізвище]»). Runs after Items + Movements; qty=1; issued_date
 * = the placing movement's накладна date. POST /api/admin/v2/import/assignments.
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

test('import assignments from Items «Де [Прізвище]» after items+movements', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // 1. catalog, 2. movements (places РаціяASG + КаскаASG at РотаASG)
    expect((await up(api, '/api/admin/v2/import/items', 'import_v2_asg_items.xlsx')).status()).toBe(200)
    expect((await up(api, '/api/admin/v2/import/movements', 'import_v2_asg_mv.xlsx')).status()).toBe(200)

    const units = await api.get('/api/structure/units').then(r => r.json())
    const rota = units.find(u => u.name === 'РотаASG')
    expect(rota).toBeTruthy()
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.unit_id === rota.id)

    // «Петренко» pre-exists WITHOUT a unit (people are imported separately now)
    const petr = await api.post('/api/settings/persons', { data: { last_name: 'Петренко' } }).then(r => r.json())
    expect(petr.unit_id ?? null).toBeNull()

    // 3. issuance from the SAME items file — finds Петренко by surname and sets unit
    const res = await up(api, '/api/admin/v2/import/assignments', 'import_v2_asg_items.xlsx')
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body.assignments).toBe(2)          // serial + non-serial
    expect(body.rows).toBe(2)
    expect(body.persons_unit_set).toBe(1)     // Петренко got the unit set once

    const persons = await api.get('/api/settings/persons').then(r => r.json())
    const p = persons.find(x => x.id === petr.id)
    expect(p.unit_id).toBe(rota.id)           // existing person, unit filled in
    // no duplicate Петренко created
    expect(persons.filter(x => x.last_name === 'Петренко').length).toBe(1)

    const asg = await api.get(`/api/assignments?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(asg).toHaveLength(2)
    // issued_date taken from the накладна (placing movement) date
    expect(asg.every(a => a.issued_date === '2026-03-15')).toBe(true)
  } finally {
    await api.dispose()
  }
})
