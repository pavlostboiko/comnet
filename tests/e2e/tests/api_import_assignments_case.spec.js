/**
 * Case-insensitivity: DB surname in CAPS («ПЕТРЕНКО») must match the «Де»
 * surname written normally («Петренко») during the issuance import.
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

test('issuance import matches a CAPS surname in DB to a normal-case «Де» value', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Isolated fixtures («…ASGC», surname «Авдєєнко») so this spec never races
    // the shared-serial api_import_assignments spec on a common DB.
    await up(api, '/api/admin/v2/import/items', 'import_v2_asgc_items.xlsx')
    await up(api, '/api/admin/v2/import/movements', 'import_v2_asgc_mv.xlsx')

    // DB surname stored in CAPS; «Де» in the file is «...Авдєєнко» (capitalized)
    const petr = await api.post('/api/settings/persons', { data: { last_name: 'АВДЄЄНКО' } }).then(r => r.json())

    const res = await up(api, '/api/admin/v2/import/assignments', 'import_v2_asgc_items.xlsx').then(r => r.json())
    expect(res.assignments).toBe(2)           // matched despite case difference
    expect(res.persons_unit_set).toBe(1)

    const p = (await api.get('/api/settings/persons').then(r => r.json())).find(x => x.id === petr.id)
    expect(p.unit_id).toBeTruthy()            // unit filled in for the CAPS person
  } finally {
    await api.dispose()
  }
})
