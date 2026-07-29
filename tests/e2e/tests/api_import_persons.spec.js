/**
 * Import people (ПІБ / ІПН / Позивний, header-based). Key = ІПН:
 * present in DB → update; new → create; ІПН in DB missing from file → deactivate.
 * Rows without ІПН are skipped. search_name = full ПІБ (helps МВО J/K matching).
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

test('import persons: update by ІПН, create new, deactivate missing, skip no-ІПН', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Pre-existing: one to update (in file), one to deactivate (not in file)
    const upd = await api.post('/api/settings/persons', { data: { last_name: 'Старий', ipn: 'IPN-UPD-1', is_active: true } }).then(r => r.json())
    const gone = await api.post('/api/settings/persons', { data: { last_name: 'Зниклий', ipn: 'IPN-GONE-1', is_active: true } }).then(r => r.json())

    const res = await up(api, '/api/admin/v2/import/persons', 'import_v2_persons.xlsx').then(r => r.json())
    expect(res.created).toBe(1)      // IPN-NEW-1
    expect(res.updated).toBe(1)      // IPN-UPD-1
    expect(res.skipped).toBe(1)      // row without ІПН
    expect(res.deactivated).toBeGreaterThanOrEqual(1)

    const persons = await api.get('/api/settings/persons').then(r => r.json())
    const byIpn = (ipn) => persons.find(p => p.ipn === ipn)

    // Updated: name/callsign refreshed, still active, search_name = full ПІБ
    const u = byIpn('IPN-UPD-1')
    expect(u.id).toBe(upd.id)
    expect(u.last_name).toBe('Оновлений')
    expect(u.first_name).toBe('Тест')
    expect(u.callsign).toBe('Альфа')
    expect(u.is_active).toBe(true)
    expect(u.search_name).toBe('оновлений тест')

    // Created + deactivated
    expect(byIpn('IPN-NEW-1')).toBeTruthy()
    expect(byIpn('IPN-NEW-1').is_active).toBe(true)
    expect(byIpn('IPN-GONE-1').id).toBe(gone.id)
    expect(byIpn('IPN-GONE-1').is_active).toBe(false)
  } finally {
    await api.dispose()
  }
})
