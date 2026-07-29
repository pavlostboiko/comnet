/**
 * Real-world J/K format: «Ім'я ПРІЗВИЩЕ» (first name + last name in caps).
 * The person matcher lowercases and keys on «first last», so it resolves to a
 * person with matching first_name/last_name — the МВО journal is built.
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

test('movements import matches МВО given as «Ім\'я ПРІЗВИЩЕ»', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const pIv = await api.post('/api/settings/persons', { data: { first_name: 'Іван', last_name: 'Іваненко' } }).then(r => r.json())
    const pPe = await api.post('/api/settings/persons', { data: { first_name: 'Петро', last_name: 'Петренко' } }).then(r => r.json())

    await up(api, '/api/admin/v2/import/items', 'import_v2_mvo_fl_items.xlsx')
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_mvo_fl_mv.xlsx').then(r => r.json())
    expect(mv.mvo_created).toBeGreaterThanOrEqual(2)   // both J and K resolved

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.name === 'Склад РотаФЛ')
    const mvo = await api.get('/api/structure/mvo').then(r => r.json())
    const rota = mvo.find(m => m.warehouse_id === rotaWh.id && m.to_date === null)
    expect(rota).toBeTruthy()
    expect(rota.person_id).toBe(pIv.id)   // «Іван ІВАНЕНКО» → Іван Іваненко
  } finally {
    await api.dispose()
  }
})
