/**
 * The global фінслужба МВО is a singleton (one active at a time), so tests that
 * create one must first close any pre-existing active fin — otherwise they
 * collide on the shared hermetic DB. Closing with to_date = from_date makes it
 * inactive and a single-day range that won't cover future document dates.
 */
async function closeActiveFin(api) {
  const rows = await api.get('/api/structure/mvo').then(r => r.json())
  for (const m of rows.filter(x => x.kind === 'fin' && x.to_date === null)) {
    await api.put(`/api/structure/mvo/${m.id}`, { data: { to_date: m.from_date } })
  }
}

module.exports = { closeActiveFin }
