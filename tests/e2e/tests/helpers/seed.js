/**
 * Seed helpers for API integration tests. Each test creates uniquely-named
 * fixtures so concurrent runs and dev-DB residue don't collide.
 */

async function postJson(api, path, body) {
  const resp = await api.post(path, { data: body })
  if (!resp.ok()) {
    throw new Error(`POST ${path} → ${resp.status()}: ${await resp.text()}`)
  }
  return resp.json()
}

async function bestEffortDelete(api, paths) {
  for (const path of paths) {
    try { await api.delete(path) } catch (_e) { /* swallow */ }
  }
}

module.exports = { postJson, bestEffortDelete }
