<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Залишки</span>
          <select class="wh-select" v-model="warehouseId" @change="loadStock">
            <option :value="null" disabled>— оберіть склад —</option>
            <optgroup label="Склади служб">
              <option v-for="w in serviceWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
            <optgroup label="Склади підрозділів">
              <option v-for="w in unitWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
          <button class="btn-sec2" :disabled="!warehouseId" @click="openReceive">Прийняти майно</button>
          <button class="btn-sec3" :disabled="!warehouseId" @click="openDoc">Видати в підрозділ</button>
          <button class="btn-add" :disabled="!warehouseId" @click="openMove">+ Рух</button>
        </div>

        <div v-if="!warehouseId" class="empty">Оберіть склад, щоб побачити залишки</div>

        <template v-else>
          <!-- Об'єднана таблиця майна на складі -->
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Найменування</th><th class="col-serial">Серійний №</th><th class="col-off">Тип</th>
                <th class="col-num">К-сть</th><th class="col-uom">Од.</th><th class="col-num">Вартість</th>
                <th>На кому</th><th class="col-issue"></th>
              </tr></thead>
              <tbody>
                <tr v-if="!stockRows.length"><td colspan="8" class="empty">Порожньо</td></tr>
                <tr v-for="r in stockRows" :key="r.key">
                  <td class="td-name">{{ r.name }}</td>
                  <td class="td-mono td-dim">{{ r.serial_no || '—' }}</td>
                  <td><span class="chip" :class="r.is_official ? 'chip-gov' : 'chip-vol'">{{ r.is_official ? 'облік' : 'ндм' }}</span></td>
                  <td class="td-num">{{ fmtQty(r.qty) }}</td>
                  <td class="td-center">{{ r.unit_of_measure || '—' }}</td>
                  <td class="td-num">{{ r.price != null ? Number(r.price).toFixed(2) : '—' }}</td>
                  <td class="td-dim">{{ r.holder || '—' }}</td>
                  <td class="td-issue">
                    <button v-if="isUnitWh && r.canIssue" class="btn-issue" @click="openIssue(r)">Видати</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Видано особам -->
          <template v-if="isUnitWh">
            <div class="section-label">Видано особам</div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Особа</th><th>Найменування</th><th class="col-serial">Серійний</th><th class="col-num">К-сть</th><th class="col-date">Дата</th><th class="col-issue"></th></tr></thead>
                <tbody>
                  <tr v-if="!assignments.length"><td colspan="6" class="empty">Нічого не видано</td></tr>
                  <tr v-for="a in assignments" :key="a.id">
                    <td class="td-name">{{ personName(a.person_id) }}</td>
                    <td>{{ nomName(a.nomenclature_id) }}</td>
                    <td class="td-mono td-dim">{{ a.instance_id ? serialOfInstance(a.instance_id) : '—' }}</td>
                    <td class="td-num">{{ fmtQty(a.quantity) }}</td>
                    <td class="td-mono">{{ a.issued_date }}</td>
                    <td class="td-issue"><button class="btn-return" @click="doReturn(a)">Повернути</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- ═══ Накладна на переміщення (batch) ═══ -->
    <div class="overlay" :class="{ open: docOpen }" @click.self="docOpen = false">
      <div v-if="docOpen" class="modal wide">
        <div class="modal-head">
          <span class="modal-title">Видати в підрозділ — з «{{ warehouseName(warehouseId) }}»</span>
          <button class="modal-close" @click="docOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="doc-top">
            <div class="fg">
              <label class="fl">Куди (склад)</label>
              <select class="fi" v-model="doc.to_warehouse_id">
                <option :value="null" disabled>— оберіть —</option>
                <option v-for="w in otherWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>
            <div class="fg"><label class="fl">№ накладної</label><input class="fi" v-model="doc.doc_number" /></div>
            <div class="fg"><label class="fl">Дата</label><input class="fi" type="date" v-model="doc.date" /></div>
          </div>

          <div class="doc-label">Позиції</div>
          <div v-for="(r, i) in doc.items" :key="i" class="doc-row">
            <select class="fi row-nom" v-model="r.nomenclature_id" @change="r.instance_id=null">
              <option :value="null" disabled>— номенклатура —</option>
              <option v-for="n in nomenclature" :key="n.id" :value="n.id">{{ n.name }} ({{ n.is_serialized ? 'серійне' : 'несерійне' }})</option>
            </select>
            <template v-if="nomById(r.nomenclature_id)?.is_serialized">
              <select class="fi row-qty" v-model="r.instance_id">
                <option :value="null" disabled>екземпляр</option>
                <option v-for="s in serial.filter(x => x.nomenclature_id === r.nomenclature_id)" :key="s.instance_id" :value="s.instance_id">{{ s.serial_no }}</option>
              </select>
            </template>
            <template v-else>
              <input class="fi row-qty" type="number" min="0.0001" step="0.0001" v-model="r.quantity" placeholder="к-сть" />
            </template>
            <button class="row-del" @click="doc.items.splice(i, 1)" :disabled="doc.items.length === 1">✕</button>
          </div>
          <button class="btn-addrow" @click="doc.items.push({ nomenclature_id: null, quantity: null, instance_id: null })">+ Додати позицію</button>

          <div v-if="docErr" class="err">{{ docErr }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="docOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="docSaving" @click="saveDoc">Провести накладну</button>
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
          <div class="fg" style="margin-bottom:14px"><label class="fl">Від кого (контрагент)</label><input class="fi" v-model="recv.counterparty" placeholder="зовнішній підрозділ / постачальник" /></div>

          <div class="doc-label">Позиції</div>
          <div v-for="(r, i) in recv.items" :key="i" class="recv-row">
            <div class="recv-line">
              <select class="fi row-nom" v-model="r.nomenclature_id" @change="onRecvNom(r)">
                <option :value="null" disabled>— номенклатура —</option>
                <option v-for="n in nomenclature" :key="n.id" :value="n.id">{{ n.name }} ({{ n.is_serialized ? 'серійне' : 'несерійне' }})</option>
                <option value="__new__">+ нова номенклатура…</option>
              </select>
              <template v-if="recvSerialized(r)">
                <input class="fi row-qty" v-model="r.serial_no" placeholder="серійний №" />
                <input class="fi row-qty" v-model="r.card_number" placeholder="№ картки" />
              </template>
              <template v-else>
                <input class="fi row-qty" type="number" min="0.0001" step="0.0001" v-model="r.quantity" placeholder="к-сть" />
              </template>
              <button class="row-del" @click="recv.items.splice(i, 1)" :disabled="recv.items.length === 1">✕</button>
            </div>
            <div v-if="r.nomenclature_id === '__new__'" class="recv-new">
              <input class="fi" v-model="r.nn_name" placeholder="назва" />
              <select class="fi" v-model="r.nn_service_id">
                <option :value="null" disabled>— служба —</option>
                <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <select class="fi" v-model="r.nn_is_official">
                <option :value="true">облік</option>
                <option :value="false">ндм</option>
              </select>
              <label class="ser-chk"><input type="checkbox" v-model="r.nn_is_serialized" /> серійне</label>
              <input class="fi" v-model="r.nn_uom" placeholder="од. (шт)" />
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

    <!-- ═══ Рух modal ═══ -->
    <div class="overlay" :class="{ open: moveOpen }" @click.self="moveOpen = false">
      <div v-if="moveOpen" class="modal">
        <div class="modal-head">
          <span class="modal-title">Новий рух — {{ warehouseName(warehouseId) }}</span>
          <button class="modal-close" @click="moveOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <label class="fl">Тип</label>
          <select class="fi" v-model="mv.type" @change="onTypeChange">
            <option value="receipt">Надходження (ззовні → цей склад)</option>
            <option value="transfer">Переміщення (цей склад → інший)</option>
            <option value="writeoff">Списання (з цього складу)</option>
          </select>

          <label class="fl">Номенклатура</label>
          <select class="fi" v-model="mv.nomenclature_id" @change="onNomChange">
            <option :value="null" disabled>— оберіть —</option>
            <option v-for="n in nomenclature" :key="n.id" :value="n.id">
              {{ n.name }} ({{ n.is_serialized ? 'серійне' : 'несерійне' }})
            </option>
          </select>

          <template v-if="mv.type === 'transfer'">
            <label class="fl">Куди (склад)</label>
            <select class="fi" v-model="mv.to_warehouse_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="w in otherWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </template>

          <template v-if="selectedNom && selectedNom.is_serialized">
            <template v-if="mv.type === 'receipt'">
              <label class="fl">Серійний номер</label>
              <input class="fi" v-model="mv.serial_no" placeholder="напр. SN-12345" />
            </template>
            <template v-else>
              <label class="fl">Екземпляр (на цьому складі)</label>
              <select class="fi" v-model="mv.instance_id">
                <option :value="null" disabled>— оберіть —</option>
                <option v-for="s in serialOfNom" :key="s.instance_id" :value="s.instance_id">{{ s.serial_no }}</option>
              </select>
            </template>
          </template>
          <template v-else-if="selectedNom">
            <label class="fl">Кількість</label>
            <input class="fi" type="number" min="0.0001" step="0.0001" v-model="mv.quantity" />
          </template>

          <label class="fl">Дата</label>
          <input class="fi" type="date" v-model="mv.date" />
          <div v-if="error" class="err">{{ error }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="moveOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="saving" @click="saveMove">Провести</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses } from '../../api/structure.js'
import { getNomenclature, createInstance } from '../../api/nomenclature.js'
import { getBalances, getSerialAt, createMovement, createDocument, receiveDocument } from '../../api/custody.js'
import { getPersons, getServices } from '../../api/settings.js'
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

const serviceWarehouses = computed(() => warehouses.value.filter(w => w.type === 'service'))
const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit'))
const otherWarehouses = computed(() => warehouses.value.filter(w => w.id !== warehouseId.value))
const selectedWarehouse = computed(() => warehouses.value.find(w => w.id === warehouseId.value) || null)
const isUnitWh = computed(() => selectedWarehouse.value?.type === 'unit')
const unitPersons = computed(() => persons.value.filter(p => p.unit_id === selectedWarehouse.value?.unit_id))

function personLabel(p) {
  const full = [p.last_name, p.first_name].filter(Boolean).join(' ')
  return full || p.callsign || `#${p.id}`
}
const personName = (id) => {
  const p = persons.value.find(x => x.id === id)
  return p ? personLabel(p) : '—'
}
const serialOfInstance = (id) => serial.value.find(s => s.instance_id === id)?.serial_no || `#${id}`
const holderOfInstance = (instId) => {
  const a = assignments.value.find(x => x.instance_id === instId)
  return a ? personName(a.person_id) : null
}

// Об'єднана таблиця майна: несерійні лінії балансу + серійні екземпляри
const stockRows = computed(() => {
  const rows = []
  for (const b of balances.value) rows.push({
    key: `n${b.nomenclature_id}-${b.is_official}`, kind: 'nonserial',
    name: b.name, serial_no: null, is_official: b.is_official, qty: b.qty,
    unit_of_measure: b.unit_of_measure, price: b.price, holder: null,
    canIssue: true, nomenclature_id: b.nomenclature_id,
  })
  for (const s of serial.value) rows.push({
    key: `s${s.instance_id}`, kind: 'serial',
    name: s.name, serial_no: s.serial_no, is_official: s.is_official, qty: 1,
    unit_of_measure: null, price: null, holder: holderOfInstance(s.instance_id),
    canIssue: !holderOfInstance(s.instance_id), instance_id: s.instance_id,
    nomenclature_id: s.nomenclature_id,
  })
  rows.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'uk') || (a.serial_no || '').localeCompare(b.serial_no || ''))
  return rows
})

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
const nomById = (id) => nomenclature.value.find(n => n.id === id) || null
const selectedNom = computed(() => nomenclature.value.find(n => n.id === mv.nomenclature_id) || null)
const serialOfNom = computed(() => serial.value.filter(s => s.nomenclature_id === mv.nomenclature_id))

function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

async function loadRefs() {
  const [w, n, p, s] = await Promise.all([getWarehouses(), getNomenclature(), getPersons(), getServices()])
  warehouses.value = w.data
  nomenclature.value = n.data
  persons.value = p.data
  services.value = s.data
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
onMounted(loadRefs)

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
  if (!confirm(`Повернути «${nomName(a.nomenclature_id)}» від «${personName(a.person_id)}»?`)) return
  try {
    await returnAssignment(a.id)
    await loadStock()
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось повернути')
  }
}

// Move modal
const moveOpen = ref(false)
const saving = ref(false)
const error = ref('')
const mv = reactive({})
function openMove() {
  error.value = ''
  Object.assign(mv, {
    type: 'receipt', nomenclature_id: null, to_warehouse_id: null,
    instance_id: null, serial_no: '', quantity: null, is_official: true,
    date: new Date().toISOString().slice(0, 10),
  })
  moveOpen.value = true
}
function onTypeChange() { mv.instance_id = null }
function onNomChange() { mv.instance_id = null }

// ── Накладна на переміщення (batch) ──────────────────────────────────
const docOpen = ref(false)
const docSaving = ref(false)
const docErr = ref('')
const doc = reactive({ to_warehouse_id: null, doc_number: '', date: '', items: [] })
function openDoc() {
  docErr.value = ''
  Object.assign(doc, {
    to_warehouse_id: null, doc_number: '', date: new Date().toISOString().slice(0, 10),
    items: [{ nomenclature_id: null, quantity: null, instance_id: null }],
  })
  docOpen.value = true
}
async function saveDoc() {
  if (!doc.to_warehouse_id) { docErr.value = 'Оберіть склад призначення'; return }
  const items = doc.items.filter(r => r.nomenclature_id && (r.instance_id || Number(r.quantity) > 0))
  if (!items.length) { docErr.value = 'Додайте хоча б одну позицію'; return }
  docSaving.value = true
  docErr.value = ''
  try {
    await createDocument({
      date: doc.date, from_warehouse_id: warehouseId.value, to_warehouse_id: doc.to_warehouse_id,
      doc_number: doc.doc_number || null,
      items: items.map(r => ({
        nomenclature_id: r.nomenclature_id,
        instance_id: r.instance_id || null,
        quantity: r.instance_id ? 1 : Number(r.quantity),
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
  return {
    nomenclature_id: null, quantity: null, serial_no: '', card_number: '',
    nn_name: '', nn_service_id: null, nn_is_official: true, nn_is_serialized: false, nn_uom: '',
  }
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
function onRecvNom(r) { r.serial_no = ''; r.card_number = ''; r.quantity = null }
function recvSerialized(r) {
  if (r.nomenclature_id === '__new__') return r.nn_is_serialized
  return !!nomById(r.nomenclature_id)?.is_serialized
}
async function saveReceive() {
  const items = []
  for (const r of recv.items) {
    if (!r.nomenclature_id) continue
    const serialized = recvSerialized(r)
    const base = serialized
      ? { serial_no: r.serial_no || null, card_number: r.card_number || null }
      : { quantity: Number(r.quantity) }
    if (r.nomenclature_id === '__new__') {
      if (!r.nn_name || !r.nn_service_id) { recvErr.value = 'Нова номенклатура: назва і служба обов’язкові'; return }
      items.push({ ...base, new_nomenclature: {
        name: r.nn_name, service_id: r.nn_service_id, is_official: r.nn_is_official,
        is_serialized: r.nn_is_serialized, unit_of_measure: r.nn_uom || null,
      } })
    } else {
      items.push({ ...base, nomenclature_id: r.nomenclature_id })
    }
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

async function saveMove() {
  saving.value = true
  error.value = ''
  try {
    if (!mv.nomenclature_id) { error.value = 'Оберіть номенклатуру'; saving.value = false; return }
    const W = warehouseId.value
    const from = mv.type === 'receipt' ? null : W
    const to = mv.type === 'receipt' ? W : (mv.type === 'transfer' ? mv.to_warehouse_id : null)
    if (mv.type === 'transfer' && !to) { error.value = 'Оберіть склад призначення'; saving.value = false; return }

    let instanceId = mv.instance_id
    if (selectedNom.value?.is_serialized && mv.type === 'receipt') {
      if (!mv.serial_no) { error.value = 'Вкажіть серійний номер'; saving.value = false; return }
      const inst = await createInstance(mv.nomenclature_id, { serial_no: mv.serial_no, is_official: mv.is_official })
      instanceId = inst.data.id
    }

    await createMovement({
      date: mv.date, type: mv.type, nomenclature_id: mv.nomenclature_id,
      from_warehouse_id: from, to_warehouse_id: to,
      instance_id: selectedNom.value?.is_serialized ? instanceId : null,
      quantity: selectedNom.value?.is_serialized ? 1 : Number(mv.quantity),
      is_official: mv.is_official,
    })
    moveOpen.value = false
    await loadStock()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка проведення'
  } finally {
    saving.value = false
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
.btn-add { padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-add:disabled { opacity:0.5; }
.btn-sec2 { margin-left:auto; padding:6px 14px; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-sec2:disabled { opacity:0.5; }
.btn-sec3 { padding:6px 14px; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-sec3:disabled { opacity:0.5; }
.recv-row { margin-bottom:10px; border-bottom:1px dashed var(--border-light); padding-bottom:8px; }
.recv-line { display:flex; gap:8px; align-items:center; }
.recv-new { display:grid; grid-template-columns:1fr 1fr 100px auto 90px; gap:8px; margin-top:6px; align-items:center; }
.ser-chk { display:flex; align-items:center; gap:4px; font-size:12px; color:var(--text-mid); white-space:nowrap; }
.modal.wide { width:min(640px,100%); }
.doc-top { display:grid; grid-template-columns:1fr 140px 140px; gap:10px; margin-bottom:14px; }
.fg { display:flex; flex-direction:column; gap:4px; }
.doc-label { font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; margin-bottom:6px; }
.doc-row { display:flex; gap:8px; margin-bottom:6px; align-items:center; }
.row-nom { flex:1; } .row-qty { width:130px; }
.row-del { width:28px; border:1px solid var(--border); background:transparent; border-radius:var(--radius-sm); cursor:pointer; color:var(--text-light); }
.row-del:disabled { opacity:0.4; }
.btn-addrow { margin-top:6px; background:transparent; border:1px dashed var(--border); color:var(--text-mid); border-radius:var(--radius-sm); padding:6px 12px; font-family:inherit; font-size:13px; cursor:pointer; }

.section-label { padding:14px 20px 6px; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-off { width:130px; } .col-num { width:110px; text-align:right; } .col-uom { width:70px; } .col-date { width:110px; } .col-issue { width:100px; text-align:center; }
.td-issue { text-align:center; }
.btn-issue { background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); padding:3px 10px; font-size:12px; font-family:inherit; font-weight:500; cursor:pointer; }
.btn-return { background:transparent; border:1px solid #d97706; color:#b45309; border-radius:var(--radius-sm); padding:3px 10px; font-size:12px; font-family:inherit; cursor:pointer; }
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
