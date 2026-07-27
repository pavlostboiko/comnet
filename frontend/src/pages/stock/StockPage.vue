<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Залишки</span>
          <button class="btn-sec2" :disabled="!warehouseId" @click="openReceive">Прийняти майно</button>
          <button class="btn-add" :disabled="!warehouseId" @click="openDoc">Додати переміщення</button>
        </div>
        <!-- Кнопки-склади: служби + внутрішні підрозділи (зовнішні не показуємо) -->
        <div class="wh-tabs">
          <button v-for="w in selectableWarehouses" :key="w.id" class="wh-btn"
            :class="{ on: warehouseId === w.id }" @click="selectWarehouse(w.id)">{{ w.name }}</button>
          <span v-if="!selectableWarehouses.length" class="wh-empty">Немає складів</span>
        </div>

        <div v-if="!warehouseId" class="empty">Оберіть склад, щоб побачити залишки</div>

        <template v-else>
          <!-- Пошук -->
          <div class="search-row">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            <input ref="stockSearchRef" v-model="stockSearch" placeholder="Пошук за назвою, серійним…" @keydown.esc="stockSearch=''" />
            <button v-if="stockSearch" class="search-clear" @click="stockSearch=''; stockSearchRef?.focus()">×</button>
          </div>
          <!-- Фільтри стану -->
          <div v-if="isUnitWh" class="filter-row">
            <button v-for="f in FILTERS" :key="f.key" class="f-chip" :class="{ on: stockFilter === f.key }" @click="stockFilter = f.key">
              {{ f.label }} <span class="f-count">{{ countOf(f.key) }}</span>
            </button>
          </div>

          <!-- Об'єднана таблиця майна на складі -->
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Найменування</th><th class="col-serial">Серійний №</th><th class="col-off">Тип</th>
                <th class="col-num">К-сть</th><th class="col-uom">Од.</th><th class="col-num">Вартість</th>
                <th>На кому</th><th class="col-note">Примітка</th><th class="col-issue"></th>
              </tr></thead>
              <tbody>
                <tr v-if="!filteredRows.length"><td colspan="9" class="empty">Порожньо</td></tr>
                <tr v-for="r in filteredRows" :key="r.key">
                  <td class="td-name">{{ r.name }}</td>
                  <td class="td-mono td-dim">{{ r.serial_no || '—' }}</td>
                  <td><span class="chip" :class="r.is_official ? 'chip-gov' : 'chip-vol'">{{ r.is_official ? 'облік' : 'ндм' }}</span></td>
                  <td class="td-num">{{ fmtQty(r.qty) }}</td>
                  <td class="td-center">{{ r.unit_of_measure || '—' }}</td>
                  <td class="td-num">{{ r.price != null ? Number(r.price).toFixed(2) : '—' }}</td>
                  <td class="td-dim">{{ r.holder || '—' }}</td>
                  <td class="col-note">
                    <input v-if="r.kind === 'serial'" class="note-inp" :value="r.note || ''"
                      placeholder="—" @change="saveNote(r, $event.target.value)" />
                    <span v-else class="td-dim">—</span>
                  </td>
                  <td class="td-issue">
                    <button v-if="r.kind === 'serial'" class="btn-hist" @click="openHistory(r)">Історія</button>
                    <button v-if="isUnitWh && r.state === 'issued'" class="btn-return" @click="doReturn(r.assignment)">Повернути</button>
                    <button v-else-if="isUnitWh && r.state === 'stock'" class="btn-issue" @click="openIssue(r)">Видати</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>

    <!-- ═══ Накладна на переміщення (batch) ═══ -->
    <div class="overlay" :class="{ open: docOpen }" @click.self="docOpen = false">
      <div v-if="docOpen" class="modal wide">
        <div class="modal-head">
          <span class="modal-title">Додати переміщення — з «{{ warehouseName(warehouseId) }}»</span>
          <button class="modal-close" @click="docOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="doc-top">
            <div class="fg">
              <label class="fl">Куди (склад)</label>
              <select class="fi" v-model="doc.to_warehouse_id" @change="onDestChange">
                <option :value="null" disabled>— оберіть —</option>
                <option v-for="w in otherWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>
            <div class="fg"><label class="fl">Дата</label><input class="fi" type="date" v-model="doc.date" /></div>
          </div>
          <p class="doc-hint">Накладну сформуєш пізніше на «Документи» → «Без документа».</p>

          <div class="doc-label">Позиції</div>
          <div v-for="(r, i) in doc.items" :key="i" class="doc-row">
            <div class="row-nom">
              <ItemAutocomplete :items="nomOptions" :model-value="nomById(r.nomenclature_id)?.name || ''" @select="onDocNom(r, i, $event)" />
            </div>
            <template v-if="nomById(r.nomenclature_id)?.is_serialized">
              <select class="fi row-qty" v-model="r.instance_id">
                <option :value="null" disabled>екземпляр</option>
                <option v-for="s in availInstances(r, i)" :key="s.instance_id" :value="s.instance_id">{{ s.serial_no }}</option>
              </select>
            </template>
            <template v-else-if="r.nomenclature_id">
              <input class="fi row-qty" type="number" min="0.0001" step="0.0001" v-model="r.quantity" placeholder="к-сть" />
            </template>
            <div v-if="isDestUnit" class="row-person">
              <ItemAutocomplete :items="destPersonOptions" placeholder="кому (опц.)"
                :model-value="r.assign_person_id ? personName(r.assign_person_id) : ''"
                @select="onDocPerson(r, $event)" />
              <button v-if="r.assign_person_id" class="row-clearp" title="прибрати особу" @click="r.assign_person_id = null">✕</button>
            </div>
            <button class="row-del" @click="doc.items.splice(i, 1)" :disabled="doc.items.length === 1">✕</button>
          </div>
          <button class="btn-addrow" @click="doc.items.push({ nomenclature_id: null, quantity: null, instance_id: null, assign_person_id: null })">+ Додати позицію</button>

          <div v-if="docErr" class="err">{{ docErr }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="docOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="docSaving" @click="saveDoc">Провести</button>
        </div>
      </div>
    </div>

    <!-- ═══ Прийняти майно ззовні (batch receipt) ═══ -->
    <div class="overlay" :class="{ open: recvOpen }" @click.self="recvOpen = false">
      <div v-if="recvOpen" class="modal wide">
        <div class="modal-head">
          <span class="modal-title">Прийняти майно — на «{{ warehouseName(warehouseId) }}»</span>
          <button class="modal-close" @click="recvOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="doc-top">
            <div class="fg">
              <label class="fl">Форма</label>
              <select class="fi" v-model="recv.form">
                <option value="накладна">Накладна</option>
                <option value="акт">Акт прийому-передачі</option>
              </select>
            </div>
            <div class="fg"><label class="fl">№ документа</label><input class="fi" v-model="recv.doc_number" placeholder="авто" /></div>
            <div class="fg"><label class="fl">Дата</label><input class="fi" type="date" v-model="recv.doc_date" /></div>
          </div>
          <div class="fg" style="margin-bottom:14px">
            <label class="fl">Від кого (зовнішній підрозділ)</label>
            <select class="fi" v-model="recv.counterparty">
              <option value="">— оберіть —</option>
              <option v-for="u in externalUnits" :key="u.id" :value="u.name">{{ u.name }}</option>
            </select>
          </div>

          <div class="doc-label">Позиції</div>
          <div v-for="(r, i) in recv.items" :key="i" class="recv-row">
            <div class="recv-line">
              <div class="row-nom">
                <ItemAutocomplete :items="allNomOptions" :model-value="nomById(r.nomenclature_id)?.name || ''" @select="onRecvNomSelect(r, i, $event)" />
              </div>
              <button class="btn-newnom" @click="openNewNom(i)" title="Нова номенклатура">+ нова</button>
              <template v-if="recvSerialized(r)">
                <input class="fi row-qty" v-model="r.serial_no" placeholder="серійний №" />
                <input class="fi row-qty" v-model="r.card_number" placeholder="№ картки" />
              </template>
              <template v-else-if="r.nomenclature_id">
                <input class="fi row-qty" type="number" min="0.0001" step="0.0001" v-model="r.quantity" placeholder="к-сть" />
              </template>
              <button class="row-del" @click="recv.items.splice(i, 1)" :disabled="recv.items.length === 1">✕</button>
            </div>
          </div>
          <button class="btn-addrow" @click="addRecvRow">+ Додати позицію</button>

          <div v-if="recvErr" class="err">{{ recvErr }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="recvOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="recvSaving" @click="saveReceive">Прийняти</button>
        </div>
      </div>
    </div>

    <!-- ═══ Видача modal ═══ -->
    <div class="overlay" :class="{ open: issueOpen }" @click.self="issueOpen = false">
      <div v-if="issueOpen" class="modal">
        <div class="modal-head">
          <span class="modal-title">Видати: {{ issue.itemName }}</span>
          <button class="modal-close" @click="issueOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <label class="fl">Кому</label>
          <select class="fi" v-model="issue.person_id">
            <option :value="null" disabled>— оберіть особу —</option>
            <option v-for="p in unitPersons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
          </select>
          <template v-if="!issue.instance_id">
            <label class="fl">Кількість</label>
            <input class="fi" type="number" min="0.0001" step="0.0001" v-model="issue.quantity" />
          </template>
          <label class="fl">Дата видачі</label>
          <input class="fi" type="date" v-model="issue.issued_date" />
          <div v-if="issueErr" class="err">{{ issueErr }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="issueOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="issueSaving" @click="saveIssue">Видати</button>
        </div>
      </div>
    </div>


    <!-- ═══ Історія екземпляра ═══ -->
    <div class="overlay" :class="{ open: histOpen }" @click.self="histOpen = false">
      <div v-if="histOpen" class="modal wide">
        <div class="modal-head">
          <span class="modal-title">Історія: {{ histTitle }}</span>
          <button class="modal-close" @click="histOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="histLoading" class="empty">Завантаження…</div>
          <HistoryTimeline v-else :events="histEvents" />
        </div>
      </div>
    </div>

    <!-- Нова номенклатура (спільна форма з «Майно») -->
    <NomenclatureModal :open="newNomOpen" :services="services" :categories="recvCategories"
      :default-service-id="recvDefaultService" @saved="onNewNomSaved" @close="newNomOpen=false" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses, getUnits } from '../../api/structure.js'
import { getNomenclature, updateInstance } from '../../api/nomenclature.js'
import { getBalances, getSerialAt, createDocument, receiveDocument, itemHistory } from '../../api/custody.js'
import { getPersons, getServices } from '../../api/settings.js'
import HistoryTimeline from '../../components/HistoryTimeline.vue'
import ItemAutocomplete from '../../components/ItemAutocomplete.vue'
import NomenclatureModal from '../../components/NomenclatureModal.vue'
import { getAssignments, createAssignment, returnAssignment } from '../../api/assignments.js'
import { useAuthStore } from '../../stores/auth.js'

const auth = useAuthStore()

const warehouses = ref([])
const nomenclature = ref([])
const warehouseId = ref(null)
const balances = ref([])
const serial = ref([])
const assignments = ref([])
const persons = ref([])
const services = ref([])
const units = ref([])

const externalUnitIds = computed(() => new Set(units.value.filter(u => u.is_external).map(u => u.id)))
const externalUnits = computed(() => units.value.filter(u => u.is_external))
const serviceWarehouses = computed(() => warehouses.value.filter(w => w.type === 'service'))
// Лише внутрішні склади підрозділів (зовнішні — джерело приймання, не облік залишків).
const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit' && !externalUnitIds.value.has(w.unit_id)))
// Склади для кнопок-перемикачів і напрямків переміщення: служби + внутрішні підрозділи.
const selectableWarehouses = computed(() => [...serviceWarehouses.value, ...unitWarehouses.value])
const otherWarehouses = computed(() => selectableWarehouses.value.filter(w => w.id !== warehouseId.value))
const selectedWarehouse = computed(() => warehouses.value.find(w => w.id === warehouseId.value) || null)
const isUnitWh = computed(() => selectedWarehouse.value?.type === 'unit')
const unitPersons = computed(() => persons.value.filter(p => p.unit_id === selectedWarehouse.value?.unit_id))

// «Додати переміщення»: якщо призначення = склад підрозділу, можна одразу видати особі
const destWarehouse = computed(() => warehouses.value.find(w => w.id === doc.to_warehouse_id) || null)
const isDestUnit = computed(() => destWarehouse.value?.type === 'unit')
const destPersonOptions = computed(() => persons.value
  .filter(p => p.unit_id === destWarehouse.value?.unit_id)
  .map(p => ({ id: p.id, name: personLabel(p), number: [p.rank, p.position].filter(Boolean).join(', ') })))

function selectWarehouse(id) { warehouseId.value = id; loadStock() }

async function saveNote(r, val) {
  const note = (val || '').trim() || null
  try {
    await updateInstance(r.nomenclature_id, r.instance_id, { note })
    const s = serial.value.find(x => x.instance_id === r.instance_id)
    if (s) s.note = note
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось зберегти примітку')
  }
}

function personLabel(p) {
  const full = [p.last_name, p.first_name].filter(Boolean).join(' ')
  return full || p.callsign || `#${p.id}`
}
const personName = (id) => {
  const p = persons.value.find(x => x.id === id)
  return p ? personLabel(p) : '—'
}
const assignmentOfInstance = (instId) => assignments.value.find(x => x.instance_id === instId) || null

// ── Історія екземпляра ───────────────────────────────────────────────
const histOpen = ref(false)
const histLoading = ref(false)
const histTitle = ref('')
const histEvents = ref([])
async function openHistory(r) {
  histTitle.value = `${r.name}${r.serial_no ? ' · ' + r.serial_no : ''}`
  histEvents.value = []
  histLoading.value = true
  histOpen.value = true
  try {
    const { data } = await itemHistory(r.nomenclature_id, r.instance_id)
    histEvents.value = data.events || []
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось завантажити історію')
  } finally {
    histLoading.value = false
  }
}

const FILTERS = [
  { key: 'all', label: 'Все' },
  { key: 'stock', label: 'На складі' },
  { key: 'issued', label: 'Видане' },
]
const stockFilter = ref('all')

// Скільки несерійного (nom, is_official) зараз на руках (активні видачі).
const activeIssued = (nomId, isOfficial) => assignments.value
  .filter(a => a.nomenclature_id === nomId && !a.instance_id && a.is_official === isOfficial)
  .reduce((s, a) => s + Number(a.quantity), 0)

// Єдиний список рядків зі станом: 'stock' (фізично на складі) / 'issued' (на особі).
// Несерійне: вільний залишок (баланс − видане) як 'stock' + кожна видача як 'issued'.
// Серійне: кожен екземпляр — 'issued' якщо на руках, інакше 'stock'.
const stockRows = computed(() => {
  const rows = []
  for (const b of balances.value) {
    const free = Number(b.qty) - activeIssued(b.nomenclature_id, b.is_official)
    if (free > 0) rows.push({
      key: `n${b.nomenclature_id}-${b.is_official}`, kind: 'nonserial', state: 'stock',
      name: b.name, serial_no: null, is_official: b.is_official, qty: free,
      unit_of_measure: b.unit_of_measure, price: b.price, holder: null,
      nomenclature_id: b.nomenclature_id, assignment: null,
    })
  }
  for (const a of assignments.value.filter(a => !a.instance_id)) {
    const nom = nomById(a.nomenclature_id)
    rows.push({
      key: `a${a.id}`, kind: 'nonserial', state: 'issued',
      name: nom?.name || nomName(a.nomenclature_id), serial_no: null, is_official: a.is_official,
      qty: Number(a.quantity), unit_of_measure: nom?.unit_of_measure,
      price: nom?.price, holder: personName(a.person_id),
      nomenclature_id: a.nomenclature_id, assignment: a,
    })
  }
  for (const s of serial.value) {
    const a = assignmentOfInstance(s.instance_id)
    rows.push({
      key: `s${s.instance_id}`, kind: 'serial', state: a ? 'issued' : 'stock',
      name: s.name, serial_no: s.serial_no, is_official: s.is_official, qty: 1,
      unit_of_measure: s.unit_of_measure, price: s.price,
      holder: a ? personName(a.person_id) : null, note: s.note,
      instance_id: s.instance_id, nomenclature_id: s.nomenclature_id, assignment: a,
    })
  }
  rows.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'uk') || (a.serial_no || '').localeCompare(b.serial_no || ''))
  return rows
})
const stockSearch = ref('')
const stockSearchRef = ref(null)
const filteredRows = computed(() => {
  let rows = stockFilter.value === 'all' ? stockRows.value : stockRows.value.filter(r => r.state === stockFilter.value)
  const q = stockSearch.value.trim().toLowerCase()
  if (q) rows = rows.filter(r =>
    (r.name || '').toLowerCase().includes(q) || (r.serial_no || '').toLowerCase().includes(q))
  return rows
})
const countOf = (key) => key === 'all' ? stockRows.value.length : stockRows.value.filter(r => r.state === key).length

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
const nomById = (id) => nomenclature.value.find(n => n.id === id) || null

function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

async function loadRefs() {
  const [w, n, p, s, u] = await Promise.all([getWarehouses(), getNomenclature(), getPersons(), getServices(), getUnits()])
  warehouses.value = w.data
  nomenclature.value = n.data
  persons.value = p.data
  services.value = s.data
  units.value = u.data
  // МВО: одразу відкриваємо свій склад
  if (auth.user?.role === 'mvo' && auth.user?.warehouse_id) {
    warehouseId.value = auth.user.warehouse_id
    await loadStock()
  }
}
async function loadStock() {
  if (!warehouseId.value) return
  const [b, s] = await Promise.all([
    getBalances(warehouseId.value), getSerialAt(warehouseId.value),
  ])
  balances.value = b.data
  serial.value = s.data
  if (isUnitWh.value) {
    assignments.value = (await getAssignments(warehouseId.value)).data
  } else {
    assignments.value = []
  }
}
function onKeyDown(e) {
  const tag = document.activeElement?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.key === '/') { e.preventDefault(); stockSearchRef.value?.focus() }
}
onMounted(() => { loadRefs(); document.addEventListener('keydown', onKeyDown) })
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

// ── Видача ───────────────────────────────────────────────────────────
const issueOpen = ref(false)
const issueSaving = ref(false)
const issueErr = ref('')
const issue = reactive({})
function openIssueNonSerial(b) {
  issueErr.value = ''
  Object.assign(issue, {
    itemName: b.name, nomenclature_id: b.nomenclature_id, instance_id: null,
    is_official: b.is_official, quantity: 1, person_id: null,
    issued_date: new Date().toISOString().slice(0, 10),
  })
  issueOpen.value = true
}
function openIssueSerial(s) {
  issueErr.value = ''
  Object.assign(issue, {
    itemName: `${s.name} (${s.serial_no})`, nomenclature_id: s.nomenclature_id,
    instance_id: s.instance_id, is_official: s.is_official, quantity: 1, person_id: null,
    issued_date: new Date().toISOString().slice(0, 10),
  })
  issueOpen.value = true
}
function openIssue(r) {
  if (r.kind === 'serial') openIssueSerial(r)
  else openIssueNonSerial(r)
}
async function saveIssue() {
  if (!issue.person_id) { issueErr.value = 'Оберіть особу'; return }
  issueSaving.value = true
  issueErr.value = ''
  try {
    await createAssignment({
      warehouse_id: warehouseId.value, person_id: issue.person_id,
      nomenclature_id: issue.nomenclature_id, instance_id: issue.instance_id,
      quantity: issue.instance_id ? 1 : Number(issue.quantity),
      is_official: issue.is_official, issued_date: issue.issued_date,
    })
    issueOpen.value = false
    await loadStock()
  } catch (e) {
    issueErr.value = e?.response?.data?.detail || 'Помилка видачі'
  } finally {
    issueSaving.value = false
  }
}
async function doReturn(a) {
  if (!a) return
  if (!confirm(`Повернути «${nomName(a.nomenclature_id)}» від «${personName(a.person_id)}»?`)) return
  try {
    await returnAssignment(a.id)
    await loadStock()
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось повернути')
  }
}

// ── Накладна на переміщення (batch) ──────────────────────────────────
const docOpen = ref(false)
const docSaving = ref(false)
const docErr = ref('')
const doc = reactive({ to_warehouse_id: null, date: '', items: [] })

// Вільний несерійний залишок картки на поточному складі (баланс − видане).
const freeQtyOf = (nomId) => {
  const b = balances.value.find(x => x.nomenclature_id === nomId)
  return b ? Number(b.qty) - activeIssued(nomId, b.is_official) : 0
}

// Autocomplete: ЛИШЕ майно, що реально доступне на поточному складі для
// переміщення — несерійне з вільним залишком або серійне з невиданими екземплярами.
const nomOptions = computed(() => {
  const ids = new Set()
  for (const b of balances.value) {
    if (Number(b.qty) - activeIssued(b.nomenclature_id, b.is_official) > 0) ids.add(b.nomenclature_id)
  }
  for (const s of serial.value) {
    if (!assignmentOfInstance(s.instance_id)) ids.add(s.nomenclature_id)  // невидані
  }
  return nomenclature.value
    .filter(n => ids.has(n.id))
    .map(n => ({ id: n.id, name: n.name, number: n.code || '', is_serialized: n.is_serialized }))
})

// Вибір номенклатури в рядку: несерійну картку не даємо додати двічі.
function onDocNom(r, i, item) {
  if (!item.is_serialized) {
    const dup = doc.items.some((x, idx) => idx !== i && x.nomenclature_id === item.id && !x.instance_id)
    if (dup) { docErr.value = `«${item.name}» вже додано — змініть кількість у наявному рядку`; return }
  }
  r.nomenclature_id = item.id
  r.instance_id = null
  r.quantity = item.is_serialized ? null : (r.quantity || 1)
  docErr.value = ''
}

// Екземпляри для цього рядка: на складі-джерелі, НЕвидані, окрім уже обраних
// в інших рядках (щоб один екземпляр не додати двічі й не переміщати видане).
function availInstances(r, i) {
  const used = doc.items.filter((_, idx) => idx !== i).map(x => x.instance_id).filter(Boolean)
  return serial.value.filter(s =>
    s.nomenclature_id === r.nomenclature_id &&
    !used.includes(s.instance_id) &&
    !assignmentOfInstance(s.instance_id))
}

function openDoc() {
  docErr.value = ''
  Object.assign(doc, {
    to_warehouse_id: null, date: new Date().toISOString().slice(0, 10),
    items: [{ nomenclature_id: null, quantity: null, instance_id: null, assign_person_id: null }],
  })
  docOpen.value = true
}
function onDocPerson(r, person) { r.assign_person_id = person.id }
// Зміна складу-призначення → скидаємо обраних осіб (вони прив'язані до підрозділу)
function onDestChange() { doc.items.forEach(r => { r.assign_person_id = null }) }
async function saveDoc() {
  if (!doc.to_warehouse_id) { docErr.value = 'Оберіть склад призначення'; return }
  const items = doc.items.filter(r => r.nomenclature_id && (r.instance_id || Number(r.quantity) > 0))
  if (!items.length) { docErr.value = 'Додайте хоча б одну позицію'; return }
  for (const r of items) {
    if (!r.instance_id) {
      const free = freeQtyOf(r.nomenclature_id)
      if (Number(r.quantity) > free) {
        docErr.value = `«${nomName(r.nomenclature_id)}»: на складі вільно ${free}`
        return
      }
    }
  }
  docSaving.value = true
  docErr.value = ''
  try {
    await createDocument({
      date: doc.date, from_warehouse_id: warehouseId.value, to_warehouse_id: doc.to_warehouse_id,
      items: items.map(r => ({
        nomenclature_id: r.nomenclature_id,
        instance_id: r.instance_id || null,
        quantity: r.instance_id ? 1 : Number(r.quantity),
        assign_person_id: isDestUnit.value ? (r.assign_person_id || null) : null,
      })),
    })
    docOpen.value = false
    await loadStock()
  } catch (e) {
    docErr.value = e?.response?.data?.detail || 'Помилка проведення'
  } finally {
    docSaving.value = false
  }
}

// ── Прийняти майно ззовні (batch receipt) ────────────────────────────
const recvOpen = ref(false)
const recvSaving = ref(false)
const recvErr = ref('')
const recv = reactive({ form: 'накладна', doc_number: '', doc_date: '', counterparty: '', items: [] })
function newRecvRow() {
  return { nomenclature_id: null, quantity: null, serial_no: '', card_number: '' }
}
function openReceive() {
  recvErr.value = ''
  Object.assign(recv, {
    form: 'накладна', doc_number: '', doc_date: new Date().toISOString().slice(0, 10),
    counterparty: '', items: [newRecvRow()],
  })
  recvOpen.value = true
}
function addRecvRow() { recv.items.push(newRecvRow()) }
// Приймання: у пошуку — вся номенклатура (завозимо нове, склад не фільтрує).
const allNomOptions = computed(() =>
  nomenclature.value.map(n => ({ id: n.id, name: n.name, number: n.code || '', is_serialized: n.is_serialized })))
function onRecvNomSelect(r, i, item) {
  r.nomenclature_id = item.id
  r.serial_no = ''; r.card_number = ''; r.quantity = null
}
function openNewNom(i) { newNomRow.value = i; newNomOpen.value = true }
function recvSerialized(r) { return !!nomById(r.nomenclature_id)?.is_serialized }

// Нова номенклатура через спільний компонент NomenclatureModal.
const newNomOpen = ref(false)
const newNomRow = ref(null)
const recvCategories = computed(() =>
  [...new Set(nomenclature.value.map(n => n.category).filter(Boolean))].sort())
const recvDefaultService = computed(() => selectedWarehouse.value?.service_id || null)
function onNewNomSaved(nom) {
  nomenclature.value.push(nom)
  if (newNomRow.value != null && recv.items[newNomRow.value]) {
    const r = recv.items[newNomRow.value]
    r.nomenclature_id = nom.id
    r.serial_no = ''; r.card_number = ''; r.quantity = null
  }
  newNomRow.value = null
}

async function saveReceive() {
  const items = []
  for (const r of recv.items) {
    if (!r.nomenclature_id) continue
    const base = recvSerialized(r)
      ? { serial_no: r.serial_no || null, card_number: r.card_number || null }
      : { quantity: Number(r.quantity) }
    items.push({ ...base, nomenclature_id: r.nomenclature_id })
  }
  if (!items.length) { recvErr.value = 'Додайте хоча б одну позицію'; return }
  recvSaving.value = true
  recvErr.value = ''
  try {
    await receiveDocument({
      to_warehouse_id: warehouseId.value, form: recv.form,
      counterparty: recv.counterparty || null, doc_number: recv.doc_number || null,
      doc_date: recv.doc_date, items,
    })
    recvOpen.value = false
    await loadStock()
  } catch (e) {
    recvErr.value = e?.response?.data?.detail || 'Помилка приймання'
  } finally {
    recvSaving.value = false
  }
}

</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; }
.tile-title { font-weight:700; font-size:15px; }
.wh-select { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; min-width:240px; }
.wh-tabs { padding:12px 20px; display:flex; flex-wrap:wrap; gap:8px; border-bottom:1px solid var(--border-light); }
.wh-btn { border:1px solid var(--border); background:var(--bg); border-radius:var(--radius-pill); padding:5px 14px; cursor:pointer; font-family:inherit; font-size:13px; color:var(--text-mid); }
.wh-btn.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.wh-empty { color:var(--text-light); font-style:italic; font-size:13px; }
.btn-add { padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-add:disabled { opacity:0.5; }
.btn-sec2 { margin-left:auto; padding:6px 14px; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-sec2:disabled { opacity:0.5; }
.btn-sec3 { padding:6px 14px; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-sec3:disabled { opacity:0.5; }
.recv-row { margin-bottom:10px; border-bottom:1px dashed var(--border-light); padding-bottom:8px; }
.recv-line { display:flex; gap:8px; align-items:center; }
.btn-newnom { flex-shrink:0; border:1px dashed var(--border); background:transparent; color:var(--text-mid); border-radius:var(--radius-sm); padding:6px 10px; font-family:inherit; font-size:12px; cursor:pointer; white-space:nowrap; }
.recv-new { display:grid; grid-template-columns:1fr 1fr 100px auto 90px; gap:8px; margin-top:6px; align-items:center; }
.ser-chk { display:flex; align-items:center; gap:4px; font-size:12px; color:var(--text-mid); white-space:nowrap; }
.modal.wide { width:min(640px,100%); }
.doc-top { display:grid; grid-template-columns:1fr 140px; gap:10px; margin-bottom:6px; }
.doc-hint { margin:0 0 14px; font-size:12px; color:var(--text-light); }
.fg { display:flex; flex-direction:column; gap:4px; }
.doc-label { font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; margin-bottom:6px; }
.doc-row { display:flex; gap:8px; margin-bottom:6px; align-items:center; }
.row-nom { flex:1; }
.row-nom :deep(.cell-input) { width:100%; box-sizing:border-box; border:1px solid var(--border); background:var(--surface); padding:7px 10px; font-size:14px; border-radius:var(--radius-sm); }
.row-nom :deep(.cell-input:focus) { background:var(--surface); }
.row-qty { width:130px; }
.row-person { width:200px; display:flex; align-items:center; gap:2px; border:1px solid var(--border); background:var(--surface); border-radius:var(--radius-sm); padding:0 4px; }
.row-person :deep(.autocomplete-wrap) { flex:1; }
.row-person :deep(.cell-input) { width:100%; box-sizing:border-box; padding:7px 6px; font-size:13px; }
.row-clearp { border:none; background:transparent; cursor:pointer; color:var(--text-light); font-size:14px; padding:0 2px; }
.row-del { width:28px; border:1px solid var(--border); background:transparent; border-radius:var(--radius-sm); cursor:pointer; color:var(--text-light); }
.row-del:disabled { opacity:0.4; }
.btn-addrow { margin-top:6px; background:transparent; border:1px dashed var(--border); color:var(--text-mid); border-radius:var(--radius-sm); padding:6px 12px; font-family:inherit; font-size:13px; cursor:pointer; }

.search-row { padding:10px 20px; display:flex; align-items:center; gap:8px; border-bottom:1px solid var(--border-light); }
.search-icon { width:14px; height:14px; color:var(--text-light); flex-shrink:0; }
.search-row input { flex:1; border:none; background:transparent; font-family:inherit; font-size:14px; outline:none; color:var(--text); }
.search-clear { width:22px; height:22px; border:none; background:transparent; cursor:pointer; color:var(--text-light); font-size:16px; }
.filter-row { padding:12px 20px; display:flex; gap:8px; border-bottom:1px solid var(--border-light); }
.f-chip { border:1px solid var(--border); background:var(--bg); border-radius:var(--radius-pill); padding:5px 14px; cursor:pointer; font-family:inherit; font-size:13px; color:var(--text-mid); display:inline-flex; align-items:center; gap:6px; }
.f-chip.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.f-count { font-size:11px; opacity:0.8; font-family:'DM Mono',monospace; }
.section-label { padding:14px 20px 6px; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-off { width:130px; } .col-num { width:110px; text-align:right; } .col-uom { width:70px; } .col-date { width:110px; } .col-issue { width:180px; text-align:right; white-space:nowrap; }
.col-note { width:160px; }
.note-inp { width:100%; box-sizing:border-box; border:1px solid transparent; background:transparent; border-radius:var(--radius-sm); padding:4px 6px; font-family:inherit; font-size:13px; color:var(--text); }
.note-inp:hover { border-color:var(--border-light); } .note-inp:focus { border-color:var(--border); background:var(--surface); outline:none; }
.td-issue { text-align:center; }
.btn-issue { background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); padding:3px 10px; font-size:12px; font-family:inherit; font-weight:500; cursor:pointer; }
.btn-return { background:transparent; border:1px solid #d97706; color:#b45309; border-radius:var(--radius-sm); padding:3px 10px; font-size:12px; font-family:inherit; cursor:pointer; }
.btn-hist { background:transparent; border:1px solid var(--border); color:var(--text-mid); border-radius:var(--radius-sm); padding:3px 10px; font-size:12px; font-family:inherit; cursor:pointer; margin-right:6px; }
.td-name { font-weight:600; color:var(--text); }
.td-dim { color:var(--text-light); }
.td-center { text-align:center; }
.td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.chip-gov { background:#dbeafe; color:#1e40af; } .chip-vol { background:#fef3c7; color:#854d0e; }
.mv-receipt { background:#dcfce7; color:#166534; } .mv-transfer { background:#e0e7ff; color:#3730a3; } .mv-writeoff { background:#fee2e2; color:#991b1b; }

.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:70px 20px; z-index:1200; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(480px,100%); }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-weight:700; font-size:14px; }
.modal-close { border:none; background:transparent; font-size:16px; color:var(--text-light); cursor:pointer; }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:8px; }
.fi { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; }
.err { margin-top:10px; padding:8px 10px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-sec { padding:7px 14px; background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; cursor:pointer; }
.btn-pri { padding:7px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
</style>
