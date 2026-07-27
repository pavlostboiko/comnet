/**
 * Regression: the v2 «Очистити інвентар» (wipe) must also remove
 * custody_documents. They are created by the movements-import backfill, so
 * without this they pile up across re-imports (orphan headers).
 *
 * ❗ Destructive — wipes the entire v2 inventory layer. Gated behind
 * RUN_WIPE_TEST so it never clobbers other specs in a normal suite run.
 * Enable with RUN_WIPE_TEST=1 (isolated stack only, ephemeral DB):
 *   RUN_WIPE_TEST=1 scripts/e2e.sh tests/api_wipe_documents.spec.js
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

test('wipe also removes custody documents created by import backfill', async ({ request }) => {
  test.skip(!process.env.RUN_WIPE_TEST, 'set RUN_WIPE_TEST=1 to enable (destructive)')

  const api = await loginApi(request)
  try {
    // Import catalog + movements — movements carry doc numbers, so the
    // backfill creates custody_documents.
    await up(api, '/api/admin/v2/import/items', 'import_v2_order_items.xlsx')
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_order_mv.xlsx').then(r => r.json())
    expect(mv.documents_created).toBeGreaterThanOrEqual(1)

    const docsBefore = await api.get('/api/custody/documents').then(r => r.json())
    expect(docsBefore.length).toBeGreaterThanOrEqual(1)

    // Wipe
    const resp = await api.post('/api/admin/v2/wipe')
    expect(resp.ok()).toBe(true)
    const body = await resp.json()
    expect(body.deleted).toHaveProperty('custody_documents')
    expect(body.deleted.custody_documents).toBeGreaterThanOrEqual(1)

    // Documents (and the rest of the inventory layer) are gone
    const docsAfter = await api.get('/api/custody/documents').then(r => r.json())
    expect(docsAfter.length).toBe(0)
    const noms = await api.get('/api/nomenclature').then(r => r.json())
    expect(noms.length).toBe(0)
  } finally {
    await api.dispose()
  }
})
