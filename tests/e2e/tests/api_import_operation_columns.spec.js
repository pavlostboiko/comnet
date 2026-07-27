/**
 * Movements import must read the operation from column Z (Запасне поле2) and the
 * document form from column Y (Тип документа), instead of guessing from the
 * presence of from/to warehouses.
 *
 *   надходження + «Акт прийому-передачі»  → receipt, form=акт, from=None,
 *                                            counterparty from «Звідки»
 *   внутрішнє переміщення + «Накладна (вимога)» → transfer, form=накладна
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

test('import reads operation (Z) and document form (Y) from columns', async ({ request }) => {
  const api = await loginApi(request)
  try {
    await up(api, '/api/admin/v2/import/items', 'import_v2_op_items.xlsx')
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_op_mv.xlsx').then(r => r.json())
    expect(mv.movements).toBe(2)
    expect(mv.documents_created).toBe(2)
    // both rows classified via column Z (not the fallback heuristic)
    expect(mv.classified_by_column).toBe(2)
    expect(mv.by_heuristic).toBe(0)

    const docs = await api.get('/api/custody/documents').then(r => r.json())
    const akt = docs.find(d => d.doc_number === 'AKT-1')
    const nak = docs.find(d => d.doc_number === 'NAK-1')

    // надходження ззовні → receipt / акт / counterparty з «Звідки», from=None
    expect(akt).toBeTruthy()
    expect(akt.operation).toBe('receipt')
    expect(akt.form).toBe('акт')
    expect(akt.counterparty).toBe('ЗовнішнійПостач')
    expect(akt.from_warehouse_id ?? null).toBeNull()

    // внутрішнє переміщення → transfer / накладна / обидва склади
    expect(nak).toBeTruthy()
    expect(nak.operation).toBe('transfer')
    expect(nak.form).toBe('накладна')
    expect(nak.from_warehouse_id).toBeTruthy()
    expect(nak.to_warehouse_id).toBeTruthy()

    // The receipt movement itself has no source warehouse (came from outside)
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    const recv = movements.find(m => m.doc_number === 'AKT-1')
    expect(recv.type).toBe('receipt')
    expect(recv.from_warehouse_id ?? null).toBeNull()
  } finally {
    await api.dispose()
  }
})
