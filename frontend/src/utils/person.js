// Єдиний вигляд особи в UI. Раніше кожна сторінка мала власний personLabel, тож
// позивний то показувався, то ні, а списки йшли в порядку створення.

/** «Прізвище Ім'я (Позивний)»; без ПІБ — позивний; зовсім порожня — «#id». */
export function personLabel(p) {
  if (!p) return '—'
  const full = [p.last_name, p.first_name].filter(Boolean).join(' ')
  const callsign = (p.callsign || '').trim()
  if (full && callsign) return `${full} (${callsign})`
  return full || callsign || `#${p.id}`
}

/** Лише ПІБ — для таблиць, де позивний стоїть окремою колонкою. */
export function personFullName(p) {
  if (!p) return '—'
  return [p.last_name, p.first_name, p.patronymic].filter(Boolean).join(' ')
    || (p.callsign || '').trim() || `#${p.id}`
}

/** Список осіб, відсортований за тим самим підписом (українська локаль). */
export function sortedPersons(persons) {
  return [...(persons || [])].sort((a, b) => personLabel(a).localeCompare(personLabel(b), 'uk'))
}

/** Опції для пошукового пікера (ItemAutocomplete): позивний уже в назві, у меті — ІПН. */
export function personOptions(persons) {
  return sortedPersons(persons).map(p => ({ id: p.id, name: personLabel(p), number: p.ipn || '' }))
}
