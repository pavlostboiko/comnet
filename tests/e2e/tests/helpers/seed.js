/**
 * Seed helpers for API integration tests. Each test creates uniquely-named
 * fixtures so concurrent runs and dev-DB residue don't collide.
 *
 * Returns the created entities plus a `cleanup` array of {path, id} pairs in
 * deletion-safe order (drop documents first to release FKs, then dictionaries).
 */

async function postJson(api, path, body) {
  const resp = await api.post(path, { data: body })
  if (!resp.ok()) {
    throw new Error(`POST ${path} → ${resp.status()}: ${await resp.text()}`)
  }
  return resp.json()
}

async function seedNakladnaContext(api, label = 'seed') {
  const tag = `${label}-${Date.now()}-${Math.floor(Math.random() * 9999)}`

  const opType = await postJson(api, '/api/settings/op-types', {
    name: `op-${tag}`,
    // Provide a prefix so /sign-required doc_number is auto-generated for tests
    number_prefix: `T-${tag}-`,
  })
  const service = await postJson(api, '/api/settings/services', {
    name: `Svc-${tag}`,
    chief_name: 'Chief Name',
    chief_position: 'Chief Pos',
  })
  const sender = await postJson(api, '/api/settings/persons', {
    first_name: 'Sender', last_name: 'Original',
    position: 'Sender pos original', unit: `Unit-S-${tag}`,
  })
  const receiver = await postJson(api, '/api/settings/persons', {
    first_name: 'Recv', last_name: 'Original',
    position: 'Recv pos original', rank: 'майор', unit: `Unit-R-${tag}`,
  })
  const fin = await postJson(api, '/api/settings/persons', {
    first_name: 'Fin', last_name: 'Original',
    position: 'Fin pos original',
  })
  const item = await postJson(api, '/api/items', {
    number: `T-${tag}`,
    name: `Test item ${tag}`,
    unit_of_measure: 'шт', price: 100, category: '1',
    nomenclature_code: `N-${tag}`,
  })

  // Cleanup paths in order safe for deletion (FK refs use ON DELETE SET NULL,
  // so dictionary deletes don't require document removal first).
  const cleanup = [
    `/api/items/${item.id}`,
    `/api/settings/persons/${sender.id}`,
    `/api/settings/persons/${receiver.id}`,
    `/api/settings/persons/${fin.id}`,
    `/api/settings/services/${service.id}`,
    `/api/settings/op-types/${opType.id}`,
  ]

  return { tag, opType, service, sender, receiver, fin, item, cleanup }
}

async function bestEffortDelete(api, paths) {
  // Documents must be in draft to be deletable; unsign first.
  for (const path of paths) {
    if (path.startsWith('/api/documents/')) {
      try { await api.post(`${path}/unsign`) } catch (_e) { /* not signed → ignore */ }
    }
  }
  for (const path of paths) {
    try { await api.delete(path) } catch (_e) { /* swallow */ }
  }
}

module.exports = { postJson, seedNakladnaContext, bestEffortDelete }
