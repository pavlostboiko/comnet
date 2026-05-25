/**
 * Reusable table-sort state for table pages.
 *
 *   const { sortBy, sortDir, sorted, toggleSort, sortIcon } =
 *     useSort(filteredRowsRef, 'name', 'asc')
 *
 *   <th class="sortable" @click="toggleSort('name')">
 *     Найменування <span class="sort-arrow">{{ sortIcon('name') }}</span>
 *   </th>
 *
 * Behaviour:
 *   - Click a header → asc; click again → desc; third click → asc.
 *   - `sortIcon(col)` returns ▲ / ▼ for the active column, ↕ otherwise.
 *   - Default sort key + dir is applied initially; clicking restores the
 *     default if you pass the same key back via toggle (no — actually
 *     toggles asc/desc; reset uses `clearSort`).
 *
 * Comparator handles:
 *   - null / undefined → sort last (regardless of direction)
 *   - numbers and numeric strings → numeric compare
 *   - everything else → localeCompare('uk', { numeric: true })
 */
import { computed, ref } from 'vue'

function compareValues(a, b) {
  // nulls always last
  const aNil = a == null || a === ''
  const bNil = b == null || b === ''
  if (aNil && bNil) return 0
  if (aNil) return 1
  if (bNil) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  const na = Number(a), nb = Number(b)
  if (!isNaN(na) && !isNaN(nb) && a !== '' && b !== '') return na - nb
  return String(a).localeCompare(String(b), 'uk', { numeric: true })
}

export function useSort(rowsRef, defaultKey = null, defaultDir = 'asc') {
  const sortBy  = ref(defaultKey)
  const sortDir = ref(defaultDir)

  function toggleSort(key) {
    if (sortBy.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy.value = key
      sortDir.value = 'asc'
    }
  }

  function clearSort() {
    sortBy.value = defaultKey
    sortDir.value = defaultDir
  }

  function sortIcon(key) {
    if (sortBy.value !== key) return '↕'
    return sortDir.value === 'asc' ? '▲' : '▼'
  }

  const sorted = computed(() => {
    const list = rowsRef.value || []
    if (!sortBy.value) return list
    const key = sortBy.value
    const sign = sortDir.value === 'desc' ? -1 : 1
    return [...list].sort((a, b) => sign * compareValues(a[key], b[key]))
  })

  return { sortBy, sortDir, sorted, toggleSort, clearSort, sortIcon }
}
