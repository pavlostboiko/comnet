/**
 * Глобальний фін-МВО — сінглтон (один ДІЮЧИЙ на систему), тож тести, які просто
 * потребують фін-підписанта, не мають за нього змагатись: кожен бере власне
 * ЗАКРИТЕ вікно дат у минулому й датує свої документи всередині нього. Резолв
 * `mvo_at` бере запис, чий період покриває дату документа, тож чужі періоди
 * (інші тести, «діючий зараз») на це вікно не впливають.
 *
 * `closeActiveFin` лишається для тесту самого правила «один діючий» — там без
 * претензії на активний запис не обійтись.
 */

/** Унікальне вікно {from, to, doc} у минулому: 3 дні, зсув від міток тесту. */
function finWindow(seed = Date.now()) {
  const offset = Math.abs(Math.floor(seed)) % 9000          // ~24 роки з 1990-01-01
  const day = (n) => new Date(Date.UTC(1990, 0, 1) + (offset + n) * 86400000)
    .toISOString().slice(0, 10)
  return { from: day(0), doc: day(1), to: day(2) }
}

async function closeActiveFin(api) {
  const rows = await api.get('/api/structure/mvo').then(r => r.json())
  for (const m of rows.filter(x => x.kind === 'fin' && x.to_date === null)) {
    await api.put(`/api/structure/mvo/${m.id}`, { data: { to_date: m.from_date } })
  }
}

module.exports = { closeActiveFin, finWindow }
