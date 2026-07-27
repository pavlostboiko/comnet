/**
 * Regression: when a serialized instance has two movements on the SAME date,
 * placement must follow the chronologically LATER document (larger doc number),
 * NOT the row that happens to come last in the Excel file.
 *
 * Fixture rows are deliberately in reversed order:
 *   file row 1 → doc 596/250/2/2 → «Склад ДваORD»   (later doc — must win)
 *   file row 2 → doc 596/250/2/1 → «Склад ОдинORD»  (earlier doc)
 * The old «last row wins» logic would place the instance in ОдинORD (wrong).
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

test('same-date movements: placement + history follow the later doc number', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Catalog: serialized АнтенаORD / card ORDCARD-1 (unplaced)
    const it = await up(api, '/api/admin/v2/import/items', 'import_v2_order_items.xlsx').then(r => r.json())
    expect(it.rows).toBe(1)

    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const nom = noms.find(n => n.name === 'АнтенаORD')
    expect(nom).toBeTruthy()
    expect(nom.is_serialized).toBe(true)

    // Two same-date movements, file order reversed vs doc chronology
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_order_mv.xlsx').then(r => r.json())
    expect(mv.movements).toBe(2)

    // Placement follows the LATER doc (596/250/2/2) → «Склад ДваORD», not ОдинORD
    const where = await api.get(`/api/custody/where?nomenclature_id=${nom.id}`).then(r => r.json())
    expect(where.is_serialized).toBe(true)
    const inst = where.serial.find(s => s.serial_no === 'ORDSER-1')
    expect(inst).toBeTruthy()
    expect(inst.warehouse_name).toBe('Склад ДваORD')

    // History: later doc (2/2) sorts ABOVE earlier doc (2/1) despite same date
    const hist = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    const docs = hist.events.filter(e => e.kind === 'movement' && e.doc_number).map(e => e.doc_number)
    expect(docs.indexOf('596/250/2/2')).toBeLessThan(docs.indexOf('596/250/2/1'))
  } finally {
    await api.dispose()
  }
})
