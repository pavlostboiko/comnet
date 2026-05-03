<template>
  <div class="page-wrap">
    <TopBar>
      <template #actions>
        <div class="tb-search" :class="{ focused: searchFocused }">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            style="color:var(--text-light);flex-shrink:0"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input v-model="search" placeholder="Пошук за назвою, документом..."
            @focus="searchFocused=true" @blur="searchFocused=false">
        </div>
        <button class="btn-primary" @click="openForm(null)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Додати
        </button>
      </template>
    </TopBar>

    <div class="content-scroll">
      <div class="tile">
        <!-- Header -->
        <div class="tile-header">
          <span class="tile-title">Переміщення</span>
          <span class="tile-count">{{ movements.length }}</span>
          <div class="tile-tabs">
            <button class="tt-btn" :class="{ on: activeTab === 'all' }" @click="activeTab='all'">
              Всі <span class="c">{{ tabCounts.all }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'in' }" @click="activeTab='in'">
              Надходження <span class="c">{{ tabCounts.in }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'out' }" @click="activeTab='out'">
              Вибуття <span class="c">{{ tabCounts.out }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'move' }" @click="activeTab='move'">
              Переміщення <span class="c">{{ tabCounts.move }}</span>
            </button>
          </div>
        </div>

        <!-- Unit chips -->
        <div class="sub-row" v-if="allUnits.length">
          <span class="sub-row-label">Підрозділ</span>
          <div class="sub-chips">
            <span v-for="u in allUnits" :key="u" class="sub-chip"
              :class="{ on: selectedUnit === u }" @click="toggleUnit(u)">{{ u }}</span>
          </div>
          <span class="sub-clear" v-if="selectedUnit" @click="selectedUnit=null">× Скинути</span>
        </div>

        <!-- Table -->
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width:44px">#</th>
                <th style="width:100px">Дата</th>
                <th style="width:130px">Тип документа</th>
                <th style="width:110px">№ документа</th>
                <th style="width:130px">Звідки</th>
                <th style="width:110px">МВО звідки</th>
                <th style="width:130px">Куди</th>
                <th style="width:110px">МВО куди</th>
                <th style="width:80px">Категорія</th>
                <th>Найменування</th>
                <th style="width:50px;text-align:right">Од.</th>
                <th style="width:90px;text-align:right">Надійшло</th>
                <th style="width:90px;text-align:right">Вибуло</th>
                <th style="width:110px;text-align:right">Ціна, грн</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="15" style="text-align:center;padding:32px;color:var(--text-light)">Завантаження…</td>
              </tr>
              <tr v-else-if="!filtered.length">
                <td colspan="15" style="text-align:center;padding:32px;color:var(--text-light)">Нічого не знайдено</td>
              </tr>
              <tr v-for="m in filtered" :key="m.id">
                <td><span class="td-idx">{{ m.id }}</span></td>
                <td class="td-mono">{{ fmtDate(m.entry_date) }}</td>
                <td>
                  <span v-if="m.doc_type" class="doc-badge" :class="docClass(m.doc_type)">{{ m.doc_type }}</span>
                  <span v-else class="dim">—</span>
                </td>
                <td class="td-mono">{{ m.doc_number || '—' }}</td>
                <td class="td-unit">{{ m.from_unit || '—' }}</td>
                <td class="td-unit td-mvo">{{ m.mvo_from_name || '—' }}</td>
                <td class="td-unit">{{ m.to_unit || '—' }}</td>
                <td class="td-unit td-mvo">{{ m.mvo_to_name || '—' }}</td>
                <td>
                  <span v-if="m.category" class="cat-badge" :class="catClass(m.category)">{{ m.category }}</span>
                  <span v-else class="dim">—</span>
                </td>
                <td class="td-item">
                  {{ m.item_name || '—' }}
                  <span v-if="m.item_card_num" class="card-ref">{{ m.item_card_num }}</span>
                </td>
                <td class="td-mono" style="text-align:right">{{ m.unit_of_measure || '—' }}</td>
                <td class="td-num" style="text-align:right">
                  <span v-if="m.qty_in && parseFloat(m.qty_in) > 0" class="qty-in">{{ fmtQty(m.qty_in) }}</span>
                  <span v-else class="dim">—</span>
                </td>
                <td class="td-num" style="text-align:right">
                  <span v-if="m.qty_out && parseFloat(m.qty_out) > 0" class="qty-out">{{ fmtQty(m.qty_out) }}</span>
                  <span v-else class="dim">—</span>
                </td>
                <td class="td-num" style="text-align:right">{{ fmtPrice(m.price) }}</td>
                <td @click.stop>
                  <div class="acts">
                    <button class="act e" title="Редагувати" @click="openForm(m)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                        <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button class="act d" title="Видалити" @click="confirmDelete(m)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="t-foot">
          Показано <b>{{ filtered.length }}</b> з <b>{{ movements.length }}</b> записів
        </div>
      </div>
    </div>

    <!-- ═══════════ FORM MODAL ═══════════ -->
    <div class="overlay" :class="{ open: formVisible }" @click.self="formVisible=false">
      <div class="modal">
        <div class="modal-head">
          <div class="modal-title">{{ formMode === 'add' ? 'Додати операцію' : 'Редагувати операцію' }}</div>
          <button class="modal-close" @click="formVisible=false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <!-- Секція: документ -->
          <div class="form-section-title">Документ</div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Дата запису</label>
              <input class="form-input" v-model="f.entry_date" type="date">
            </div>
            <div class="form-group">
              <label class="form-label">Тип документа</label>
              <select class="form-select" v-model="f.doc_type">
                <option value="">— оберіть —</option>
                <option value="Н-440/25">Н-440/25 (Накладна)</option>
                <option value="Н-431">Н-431 (з ПДВ)</option>
                <option value="РВ-57">РВ-57 (Розподільча відомість)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">№ документа</label>
              <input class="form-input" v-model="f.doc_number" placeholder="001/25">
            </div>
            <div class="form-group">
              <label class="form-label">Дата документа</label>
              <input class="form-input" v-model="f.doc_date" type="date">
            </div>
            <div class="form-group">
              <label class="form-label">Підстава</label>
              <input class="form-input" v-model="f.basis" placeholder="наказ, розпорядження...">
            </div>
            <div class="form-group">
              <label class="form-label">Категорія</label>
              <select class="form-select" v-model="f.category">
                <option value="">— оберіть —</option>
                <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>

          <!-- Секція: напрямок -->
          <div class="form-section-title" style="margin-top:18px">Напрямок</div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Звідки</label>
              <input class="form-input" v-model="f.from_unit" list="units-dl" placeholder="Склад / підрозділ">
            </div>
            <div class="form-group">
              <label class="form-label">Куди</label>
              <input class="form-input" v-model="f.to_unit" list="units-dl" placeholder="Підрозділ">
            </div>
            <div class="form-group">
              <label class="form-label">МВО (звідки)</label>
              <select class="form-select" v-model="f.mvo_from_id">
                <option :value="null">— оберіть особу —</option>
                <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">МВО (куди)</label>
              <select class="form-select" v-model="f.mvo_to_id">
                <option :value="null">— оберіть особу —</option>
                <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
              </select>
            </div>
          </div>

          <!-- Секція: майно -->
          <div class="form-section-title" style="margin-top:18px">Майно</div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">№ картки майна</label>
              <input class="form-input" v-model="f.item_card_num" list="items-dl"
                placeholder="Введіть або оберіть" @change="onItemCardChange">
            </div>
            <div class="form-group">
              <label class="form-label">Найменування *</label>
              <input class="form-input" v-model="f.item_name" placeholder="Назва">
            </div>
            <div class="form-group">
              <label class="form-label">Одиниця виміру</label>
              <input class="form-input" v-model="f.unit_of_measure" placeholder="шт">
            </div>
            <div class="form-group">
              <label class="form-label">Код номенклатури</label>
              <input class="form-input" v-model="f.nomenclature_code" placeholder="XXXXXX">
            </div>
            <div class="form-group">
              <label class="form-label">Серійний №</label>
              <input class="form-input" v-model="f.serial_number" placeholder="SN-...">
            </div>
            <div class="form-group">
              <label class="form-label">Ціна, грн</label>
              <input class="form-input" v-model="f.price" type="number" step="0.01" placeholder="0.00">
            </div>
            <div class="form-group">
              <label class="form-label">Надійшло</label>
              <input class="form-input" v-model="f.qty_in" type="number" step="0.0001" placeholder="0">
            </div>
            <div class="form-group">
              <label class="form-label">Вибуло</label>
              <input class="form-input" v-model="f.qty_out" type="number" step="0.0001" placeholder="0">
            </div>
            <div class="form-group full">
              <label class="form-label">Примітки</label>
              <input class="form-input" v-model="f.notes" placeholder="Серійні номери, доп. інформація...">
            </div>
          </div>

          <!-- datalists -->
          <datalist id="units-dl">
            <option v-for="u in allUnits" :key="u" :value="u"/>
          </datalist>
          <datalist id="items-dl">
            <option v-for="item in items" :key="item.id" :value="item.number">{{ item.name }}</option>
          </datalist>
        </div>

        <div class="modal-foot">
          <button class="btn-cancel" @click="formVisible=false">Скасувати</button>
          <button class="btn-submit" :disabled="saving" @click="submitForm">
            {{ saving ? 'Збереження…' : 'Зберегти' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div class="toast" :class="{ show: toastVisible }">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { createMovement, deleteMovement as apiDelete, getMovements, updateMovement } from '../../api/movements.js'
import { getItems } from '../../api/items.js'
import { getPersons } from '../../api/settings.js'

const CATEGORIES = ['1','2','3','4','5','пр.','непр.','пот.рем.']

// ── State ──────────────────────────────────────────────────────
const movements    = ref([])
const items        = ref([])
const persons      = ref([])
const loading      = ref(false)
const search       = ref('')
const searchFocused = ref(false)
const activeTab    = ref('all')
const selectedUnit = ref(null)

// Form
const formVisible = ref(false)
const formMode    = ref('add')
const editId      = ref(null)
const saving      = ref(false)
const f = reactive({
  entry_date: '', doc_type: '', doc_number: '', doc_date: '', basis: '', category: '',
  from_unit: '', to_unit: '',
  mvo_from_id: null, mvo_to_id: null,
  item_card_num: '', item_name: '', unit_of_measure: '', nomenclature_code: '',
  serial_number: '', price: '', qty_in: '', qty_out: '', notes: '',
})

// Toast
const toastMsg     = ref('')
const toastVisible = ref(false)
let toastTimer

// ── Op type logic ───────────────────────────────────────────────
function opType(m) {
  const i = parseFloat(m.qty_in) || 0
  const o = parseFloat(m.qty_out) || 0
  if (i > 0 && o === 0) return 'in'
  if (o > 0 && i === 0) return 'out'
  if (i > 0 && o > 0)   return 'move'
  return 'other'
}

// ── Computed ───────────────────────────────────────────────────
const tabCounts = computed(() => {
  const list = movements.value
  return {
    all:  list.length,
    in:   list.filter(m => opType(m) === 'in').length,
    out:  list.filter(m => opType(m) === 'out').length,
    move: list.filter(m => opType(m) === 'move').length,
  }
})

const allUnits = computed(() => {
  const s = new Set()
  movements.value.forEach(m => {
    if (m.from_unit) s.add(m.from_unit)
    if (m.to_unit)   s.add(m.to_unit)
  })
  return [...s].sort()
})

const filtered = computed(() => {
  let list = movements.value
  if (activeTab.value !== 'all') list = list.filter(m => opType(m) === activeTab.value)
  if (selectedUnit.value) {
    list = list.filter(m => m.from_unit === selectedUnit.value || m.to_unit === selectedUnit.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(m =>
      m.item_name?.toLowerCase().includes(q) ||
      m.doc_number?.toLowerCase().includes(q) ||
      m.doc_type?.toLowerCase().includes(q) ||
      m.from_unit?.toLowerCase().includes(q) ||
      m.to_unit?.toLowerCase().includes(q) ||
      m.item_card_num?.toLowerCase().includes(q)
    )
  }
  return list
})

// ── Helpers ────────────────────────────────────────────────────
function fmtDate(d) {
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  return `${day}.${m}.${y}`
}

function fmtQty(v) {
  if (v == null) return '—'
  const n = parseFloat(v)
  return n % 1 === 0 ? n.toFixed(0) : n.toString()
}

function fmtPrice(v) {
  if (v == null) return '—'
  return parseFloat(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function catClass(cat) {
  return {
    '1': 'cat-1', '2': 'cat-2', '3': 'cat-3', '4': 'cat-4', '5': 'cat-5',
    'пр.': 'cat-pr', 'непр.': 'cat-npr',
  }[cat] || ''
}

function docClass(t) {
  if (t?.includes('440')) return 'doc-440'
  if (t?.includes('431')) return 'doc-431'
  if (t?.includes('57'))  return 'doc-57'
  return ''
}

function personLabel(p) {
  return [p.rank, p.last_name, p.first_name?.[0], p.patronymic?.[0]]
    .filter(Boolean).join(' ')
}

function showToast(msg) {
  toastMsg.value = msg
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2400)
}

function toggleUnit(u) {
  selectedUnit.value = selectedUnit.value === u ? null : u
}

// ── Auto-fill from item card ───────────────────────────────────
function onItemCardChange() {
  const num = f.item_card_num?.trim()
  if (!num) return
  const item = items.value.find(i => i.number === num)
  if (item) {
    if (!f.item_name)         f.item_name         = item.name || ''
    if (!f.unit_of_measure)   f.unit_of_measure   = item.unit_of_measure || ''
    if (!f.nomenclature_code) f.nomenclature_code = item.nomenclature_code || ''
    if (!f.price && item.price) f.price            = String(parseFloat(item.price))
    if (!f.serial_number && item.serial_number) f.serial_number = item.serial_number
  }
}

// ── Data loading ───────────────────────────────────────────────
async function fetchAll() {
  loading.value = true
  try {
    const [mv, it, ps] = await Promise.all([getMovements(), getItems(), getPersons()])
    movements.value = mv
    items.value     = it
    persons.value   = ps.filter(p => p.is_active)
  } finally {
    loading.value = false
  }
}

// ── Form ───────────────────────────────────────────────────────
function openForm(m) {
  formMode.value = m ? 'edit' : 'add'
  editId.value   = m?.id ?? null

  f.entry_date      = m?.entry_date ?? ''
  f.doc_type        = m?.doc_type ?? ''
  f.doc_number      = m?.doc_number ?? ''
  f.doc_date        = m?.doc_date ?? ''
  f.basis           = m?.basis ?? ''
  f.category        = m?.category ?? ''
  f.from_unit       = m?.from_unit ?? ''
  f.to_unit         = m?.to_unit ?? ''
  f.mvo_from_id     = m?.mvo_from_id ?? null
  f.mvo_to_id       = m?.mvo_to_id ?? null
  f.item_card_num   = m?.item_card_num ?? ''
  f.item_name       = m?.item_name ?? ''
  f.unit_of_measure = m?.unit_of_measure ?? ''
  f.nomenclature_code = m?.nomenclature_code ?? ''
  f.serial_number   = m?.serial_number ?? ''
  f.price           = m?.price != null ? String(parseFloat(m.price)) : ''
  f.qty_in          = m?.qty_in != null ? String(parseFloat(m.qty_in)) : ''
  f.qty_out         = m?.qty_out != null ? String(parseFloat(m.qty_out)) : ''
  f.notes           = m?.notes ?? ''

  formVisible.value = true
}

function buildPayload() {
  return {
    entry_date:       f.entry_date   || null,
    doc_type:         f.doc_type     || null,
    doc_number:       f.doc_number   || null,
    doc_date:         f.doc_date     || null,
    basis:            f.basis        || null,
    category:         f.category     || null,
    from_unit:        f.from_unit    || null,
    to_unit:          f.to_unit      || null,
    mvo_from_id:      f.mvo_from_id  || null,
    mvo_to_id:        f.mvo_to_id    || null,
    item_card_num:    f.item_card_num   || null,
    item_name:        f.item_name       || null,
    unit_of_measure:  f.unit_of_measure || null,
    nomenclature_code: f.nomenclature_code || null,
    serial_number:    f.serial_number   || null,
    price:            f.price   !== '' ? parseFloat(f.price)   : null,
    qty_in:           f.qty_in  !== '' ? parseFloat(f.qty_in)  : null,
    qty_out:          f.qty_out !== '' ? parseFloat(f.qty_out) : null,
    notes:            f.notes || null,
  }
}

async function submitForm() {
  if (!f.item_name?.trim()) { showToast('Вкажіть найменування'); return }
  saving.value = true
  try {
    const payload = buildPayload()
    if (formMode.value === 'add') {
      const created = await createMovement(payload)
      movements.value.unshift(created)
      showToast('Операцію додано')
    } else {
      const updated = await updateMovement(editId.value, payload)
      const idx = movements.value.findIndex(m => m.id === editId.value)
      if (idx !== -1) movements.value.splice(idx, 1, updated)
      showToast('Збережено')
    }
    formVisible.value = false
  } catch {
    showToast('Помилка збереження')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(m) {
  if (!confirm(`Видалити запис "${m.item_name || '#' + m.id}"?`)) return
  try {
    await apiDelete(m.id)
    movements.value = movements.value.filter(x => x.id !== m.id)
    showToast('Видалено')
  } catch {
    showToast('Помилка видалення')
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.page-wrap { display:flex; flex-direction:column; height:100vh; overflow:hidden; }

/* TopBar search */
.tb-search {
  display:flex; align-items:center; gap:6px;
  background:var(--bg); border:1px solid var(--border);
  border-radius:var(--radius-sm); padding:7px 12px;
  width:240px; transition:all 0.2s;
}
.tb-search.focused { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-ring); background:var(--surface); width:300px; }
.tb-search input { border:none; background:transparent; font-family:inherit; font-size:13.5px; color:var(--text); outline:none; width:100%; }
.tb-search input::placeholder { color:var(--text-light); }

.btn-primary {
  display:flex; align-items:center; gap:5px; padding:8px 14px;
  background:var(--accent); border:none; border-radius:var(--radius-sm);
  font-family:inherit; font-size:13.5px; font-weight:600; color:white;
  cursor:pointer; transition:all 0.15s;
}
.btn-primary:hover { background:var(--accent-dark); transform:translateY(-1px); }

/* Layout */
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.content-scroll::-webkit-scrollbar { width:6px; }
.content-scroll::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

/* Tile */
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden; }
.tile-header { padding:12px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); flex-wrap:wrap; }
.tile-title  { font-size:15px; font-weight:700; }
.tile-count  { font-family:'DM Mono',monospace; font-size:11.5px; font-weight:500; background:var(--accent-light); color:var(--accent); padding:2px 8px; border-radius:var(--radius-sm); }
.tile-tabs   { display:flex; gap:2px; background:var(--bg); padding:3px; border-radius:var(--radius-sm); border:1px solid var(--border-light); margin-left:auto; }
.tt-btn { padding:5px 13px; border:none; background:transparent; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; transition:all 0.12s; white-space:nowrap; display:flex; align-items:center; gap:6px; }
.tt-btn:hover { color:var(--text-mid); }
.tt-btn.on { background:var(--surface); color:var(--text); box-shadow:0 1px 2px rgba(0,0,0,0.06); font-weight:600; }
.tt-btn .c { font-family:'DM Mono',monospace; font-size:10.5px; color:var(--text-light); background:var(--border-light); padding:0 6px; border-radius:var(--radius-sm); line-height:17px; min-width:20px; text-align:center; }
.tt-btn.on .c { background:var(--accent-light); color:var(--accent); }

/* Sub-row chips */
.sub-row { padding:9px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); background:var(--bg); flex-wrap:wrap; }
.sub-row-label { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-light); flex-shrink:0; }
.sub-chips { display:flex; gap:6px; flex-wrap:wrap; }
.sub-chip { padding:4px 11px; border:1px solid var(--border); background:var(--surface); border-radius:var(--radius-pill); font-size:12.5px; font-weight:500; color:var(--text-mid); cursor:pointer; transition:all 0.12s; }
.sub-chip:hover { border-color:var(--text-light); color:var(--text); }
.sub-chip.on { background:var(--accent); border-color:var(--accent); color:white; font-weight:600; }
.sub-clear { margin-left:auto; font-size:12px; color:var(--text-light); cursor:pointer; padding:3px 8px; border-radius:var(--radius-sm); transition:all 0.12s; }
.sub-clear:hover { color:var(--text); background:var(--border-light); }

/* Table */
.table-wrap { overflow-x:auto; }
.table-wrap::-webkit-scrollbar { height:6px; }
.table-wrap::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
table { width:100%; border-collapse:collapse; min-width:1260px; }
thead tr { background:var(--bg); }
th { padding:9px 12px; text-align:left; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); border-bottom:1px solid var(--border); white-space:nowrap; }
th:first-child { padding-left:20px; }
th:last-child  { padding-right:20px; width:52px; }
tbody tr { border-bottom:1px solid var(--border-light); transition:background 0.1s; }
tbody tr:last-child { border-bottom:none; }
tbody tr:nth-child(even) { background:#f8fafc; }
tbody tr:hover { background:var(--row-hover) !important; }
td { padding:10px 12px; font-size:14px; color:var(--text-mid); vertical-align:middle; white-space:nowrap; }
td:first-child { padding-left:20px; }
td:last-child  { padding-right:20px; }

.td-idx   { font-family:'DM Mono',monospace; font-size:11px; font-weight:600; color:var(--accent); background:var(--accent-light); padding:2px 8px; border-radius:var(--radius-sm); display:inline-block; }
.td-mono  { font-family:'DM Mono',monospace; font-size:12.5px; }
.td-num   { font-family:'DM Mono',monospace; font-size:12.5px; font-variant-numeric:tabular-nums; }
.td-item  { font-weight:600; color:var(--text); max-width:260px; overflow:hidden; text-overflow:ellipsis; }
.td-unit  { max-width:130px; overflow:hidden; text-overflow:ellipsis; font-size:13px; }
.td-mvo   { max-width:110px; color:var(--text-light); font-size:12px; }
.card-ref { font-family:'DM Mono',monospace; font-size:11px; color:var(--text-light); background:var(--accent-light); padding:1px 6px; border-radius:var(--radius-sm); margin-left:6px; }
.dim      { color:var(--text-light); }
.qty-in   { color:#065f46; font-weight:600; }
.qty-out  { color:#991b1b; font-weight:600; }

.cat-badge { display:inline-block; padding:2px 8px; border-radius:var(--radius-sm); font-size:11.5px; font-weight:600; font-family:'DM Mono',monospace; }
.cat-1  { background:#eff6ff; color:#2563eb; }
.cat-2  { background:#ecfdf5; color:#059669; }
.cat-3  { background:#fef9c3; color:#a16207; }
.cat-4  { background:#fef3c7; color:#92400e; }
.cat-5  { background:#fce7f3; color:#9d174d; }
.cat-pr { background:#f0fdf4; color:#16a34a; }
.cat-npr { background:#fef2f2; color:#dc2626; }

.doc-badge { display:inline-block; padding:2px 9px; border-radius:var(--radius-sm); font-size:11.5px; font-weight:600; }
.doc-440 { background:#eff6ff; color:#3b82f6; }
.doc-431 { background:#fdf4ff; color:#a855f7; }
.doc-57  { background:#fff7ed; color:#ea580c; }

/* Row actions */
.acts { display:flex; gap:2px; opacity:0; transition:opacity 0.12s; justify-content:flex-end; }
tbody tr:hover .acts { opacity:1; }
.act { width:28px; height:28px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; transition:all 0.12s; }
.act svg { width:14px; height:14px; }
.act:hover.e { background:var(--accent-light); color:var(--accent); }
.act:hover.d { background:#fee2e2; color:#ef4444; }

/* Footer */
.t-foot { padding:10px 20px; border-top:1px solid var(--border-light); font-size:13px; color:var(--text-light); display:flex; align-items:center; background:var(--bg); }
.t-foot b { color:var(--text); font-weight:600; }

/* Modal */
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.4); backdrop-filter:blur(2px); z-index:100; display:flex; align-items:center; justify-content:center; opacity:0; pointer-events:none; transition:opacity 0.2s; }
.overlay.open { opacity:1; pointer-events:all; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow-xl); width:680px; max-width:calc(100vw - 48px); max-height:calc(100vh - 80px); overflow-y:auto; transform:translateY(12px) scale(0.98); transition:transform 0.2s; }
.overlay.open .modal { transform:translateY(0) scale(1); }
.modal-head { padding:20px 24px 16px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; background:var(--surface); z-index:1; }
.modal-title { font-size:17px; font-weight:700; }
.modal-close { width:30px; height:30px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; transition:all 0.12s; }
.modal-close:hover { background:var(--bg); color:var(--text); }
.modal-body { padding:20px 24px; }
.modal-foot { padding:16px 24px; border-top:1px solid var(--border-light); display:flex; justify-content:flex-end; gap:8px; position:sticky; bottom:0; background:var(--surface); }

.form-section-title { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); margin-bottom:12px; }
.form-grid  { display:grid; grid-template-columns:1fr 1fr; gap:14px 16px; }
.form-group { display:flex; flex-direction:column; gap:6px; }
.form-group.full { grid-column:span 2; }
.form-label { font-size:12.5px; font-weight:600; color:var(--text-mid); }
.form-input { padding:9px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; color:var(--text); background:var(--bg); outline:none; transition:all 0.15s; }
.form-input:focus { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); background:var(--surface); }
.form-input::placeholder { color:var(--text-light); }
.form-select { padding:9px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; color:var(--text); background:var(--bg); outline:none; cursor:pointer; transition:all 0.15s; appearance:none; background-image:url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2394a3b8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 10px center; padding-right:28px; }
.form-select:focus { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); }

.btn-cancel { padding:9px 16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:500; color:var(--text-mid); cursor:pointer; transition:all 0.12s; }
.btn-cancel:hover { border-color:var(--text-light); color:var(--text); }
.btn-submit { padding:9px 20px; background:var(--accent); border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:600; color:white; cursor:pointer; transition:all 0.15s; }
.btn-submit:hover { background:var(--accent-dark); }
.btn-submit:disabled { opacity:0.6; cursor:not-allowed; }

/* Toast */
.toast { position:fixed; bottom:20px; left:50%; transform:translateX(-50%) translateY(80px); background:var(--text); color:white; padding:11px 20px; border-radius:var(--radius-sm); font-size:13.5px; font-weight:500; box-shadow:var(--shadow-xl); z-index:200; opacity:0; transition:all 0.25s; }
.toast.show { transform:translateX(-50%) translateY(0); opacity:1; }
</style>
