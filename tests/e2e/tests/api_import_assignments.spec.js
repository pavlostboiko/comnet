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

    // person «Петренко» in the unit created by the movements import
    const units = await api.get('/api/structure/units').then(r => r.json())
    const rota = units.find(u => u.name === 'РотаASG')
    expect(rota).toBeTruthy()
    await api.post('/api/settings/persons', { data: { last_name: 'Петренко', first_name: 'П', unit_id: rota.id } })
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.unit_id === rota.id)

    // 3. issuance from the SAME items file
    const res = await up(api, '/api/admin/v2/import/assignments', 'import_v2_asg_items.xlsx')
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body.assignments).toBe(2)          // serial + non-serial
    expect(body.rows).toBe(2)

    const asg = await api.get(`/api/assignments?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(asg).toHaveLength(2)
    // issued_date taken from the накладна (placing movement) date
    expect(asg.every(a => a.issued_date === '2026-03-15')).toBe(true)
  } finally {
    await api.dispose()
  }
})
