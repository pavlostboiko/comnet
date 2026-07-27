<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll" v-if="doc">
      <div class="form-head">
        <button class="btn-back" @click="$router.push('/docs')">← Усі документи</button>
        <div class="head-title">
          <span class="chip">{{ opLabel(doc.operation) }} · {{ doc.form }}</span>
          <b>{{ form.doc_number || 'без номера' }}</b>
          <span class="chip" :class="`st-${doc.status}`">{{ stLabel(doc.status) }}</span>
        </div>
        <div class="head-btns">
          <template v-if="doc.status === 'draft'">
            <button class="btn-sec" :disabled="busy" @click="save">Зберегти</button>
            <button class="btn-primary" :disabled="busy" @click="doSign">Підписати</button>
            <button class="btn-danger" :disabled="busy" @click="doDelete">Видалити</button>
          </template>
          <template v-else>
            <button class="btn-sec" :disabled="busy" @click="exportXlsx">XLSX</button>
            <button class="btn-danger" :disabled="busy" @click="doUnsign">Зняти підпис</button>
          </template>
        </div>
      </div>

      <div v-if="signErrors.length" class="err-box">
        Заповніть: {{ signErrors.join(', ') }}
      </div>

      <div class="tile">
        <div class="tile-header"><span class="tile-title">Реквізити</span></div>
        <div class="form-grid">
          <label>Форма
            <select v-model="form.form" :disabled="ro" class="fi">
              <option value="накладна">Накладна (вимога)</option>
              <option value="акт">Акт прийому-передачі</option>
            </select>
          </label>
          <label>Номер <input v-model="form.doc_number" :disabled="ro" class="fi" placeholder="авто" /></label>
          <label>Дата <input type="date" v-model="form.doc_date" :disabled="ro" class="fi" /></label>
          <label>Дата операції <input type="date" v-model="form.date_operation" :disabled="ro" class="fi" /></label>
          <label v-if="doc.operation === 'receipt'">Від кого (контрагент)
            <input v-model="form.counterparty" :disabled="ro" class="fi" /></label>
          <label>Підстава <input v-model="form.basis" :disabled="ro" class="fi" /></label>
          <label>Служба
            <select v-model="form.service_id" :disabled="ro" class="fi">
              <option :value="null">—</option>
              <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <label>Тип операції
            <select v-model="form.op_type_id" :disabled="ro" class="fi">
              <option :value="null">—</option>
              <option v-for="o in opTypes" :key="o.id" :value="o.id">{{ o.name }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="tile">
        <div class="tile-header"><span class="tile-title">Підписанти (МВО)</span></div>
        <div class="form-grid three">
          <label>Здав (відправник)
            <select v-model="form.sender_id" :disabled="ro" class="fi">
              <option :value="null">—</option>
              <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
          </label>
          <label>Прийняв (отримувач)
            <select v-model="form.receiver_id" :disabled="ro" class="fi">
              <option :value="null">—</option>
              <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
          </label>
          <label>Фінслужба
            <select v-model="form.fin_id" :disabled="ro" class="fi">
              <option :value="null">—</option>
              <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Позиції</span>
          <span class="tile-sub">{{ doc.from_unit || '—' }} → {{ doc.to_unit || '—' }}</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="col-i">№</th><th>Номенклатура</th><th class="col-c">Код</th>
              <th class="col-u">Од.</th><th class="col-c">Кат.</th>
              <th class="col-n">Вартість</th><th class="col-n">К-сть</th>
              <th class="col-s">Картка/серійний</th><th v-if="!ro" class="col-x"></th>
            </tr></thead>
            <tbody>
              <tr v-if="!lines.length"><td :colspan="ro ? 8 : 9" class="empty">Немає позицій</td></tr>
              <tr v-for="(l, i) in lines" :key="l.id">
                <td class="td-dim">{{ i + 1 }}</td>
                <td>{{ l.nomenclature_name }}</td>
                <td class="td-mono td-dim">{{ l.nomenclature_code || '—' }}</td>
                <td class="td-dim">{{ l.unit_of_measure || '—' }}</td>
                <td class="td-dim">{{ l.category || '—' }}</td>
                <td class="td-num">{{ l.price ?? '—' }}</td>
                <td class="td-num">{{ fmtQty(l.quantity) }}</td>
                <td class="td-mono td-dim">{{ l.serial_no || l.card_number || '—' }}</td>
                <td v-if="!ro" class="td-x"><button class="btn-x" @click="removeLine(l.id)">×</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '../../components/TopBar.vue'
import { getDoc, updateDoc, signDoc, unsignDoc, deleteDoc, exportDocXlsx } from '../../api/custody.js'
import { getServices, getPersons, getOpTypes } from '../../api/settings.js'

const route = useRoute()
const router = useRouter()
const doc = ref(null)
const lines = ref([])
const services = ref([])
const persons = ref([])
const opTypes = ref([])
const busy = ref(false)
const signErrors = ref([])
const form = reactive({
  form: 'накладна', doc_number: '', doc_date: '', date_operation: '',
  counterparty: '', basis: '', service_id: null, op_type_id: null,
  sender_id: null, receiver_id: null, fin_id: null,
})

const ro = computed(() => doc.value?.status !== 'draft')

function opLabel(o) { return { receipt: 'надходження', transfer: 'переміщення' }[o] || o }
function stLabel(s) { return { draft: 'чернетка', signed: 'підписано' }[s] || s }
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}
function personLabel(p) {
  const name = [p.last_name, p.first_name].filter(Boolean).join(' ')
  const extra = [p.rank, p.position].filter(Boolean).join(', ')
  return extra ? `${name} (${extra})` : name
}

function applyDoc(d) {
  doc.value = d
  lines.value = d.lines || []
  form.form = d.form
  form.doc_number = d.doc_number || ''
  form.doc_date = d.doc_date || ''
  form.date_operation = d.date_operation || ''
  form.counterparty = d.counterparty || ''
  form.basis = d.basis || ''
  form.service_id = d.service_id
  form.op_type_id = d.op_type_id
  form.sender_id = d.sender_id
  form.receiver_id = d.receiver_id
  form.fin_id = d.fin_id
}

function removeLine(id) { lines.value = lines.value.filter(l => l.id !== id) }

function payload() {
  return {
    operation: doc.value.operation, form: form.form,
    doc_number: form.doc_number || null, doc_date: form.doc_date || null,
    date_operation: form.date_operation || null, counterparty: form.counterparty || null,
    basis: form.basis || null, service_id: form.service_id, op_type_id: form.op_type_id,
    sender_id: form.sender_id, receiver_id: form.receiver_id, fin_id: form.fin_id,
    movement_ids: lines.value.map(l => l.id),
  }
}

async function save() {
  busy.value = true; signErrors.value = []
  try {
    const { data } = await updateDoc(doc.value.id, payload())
    applyDoc(data)
  } catch (e) { alert('Помилка: ' + (e.response?.data?.detail || e.message)) }
  finally { busy.value = false }
}

async function doSign() {
  busy.value = true; signErrors.value = []
  try {
    await updateDoc(doc.value.id, payload())
    const { data } = await signDoc(doc.value.id)
    applyDoc(data)
  } catch (e) {
    const d = e.response?.data
    signErrors.value = d?.detail?.missing || (d?.detail ? [String(d.detail)] : ['Помилка підписання'])
  } finally { busy.value = false }
}

async function doUnsign() {
  busy.value = true
  try { const { data } = await unsignDoc(doc.value.id); applyDoc(data) }
  catch (e) { alert('Помилка: ' + (e.response?.data?.detail || e.message)) }
  finally { busy.value = false }
}

async function doDelete() {
  if (!confirm('Видалити документ? Рухи залишаться (без документа).')) return
  busy.value = true
  try { await deleteDoc(doc.value.id); router.push('/docs') }
  catch (e) { alert('Помилка: ' + (e.response?.data?.detail || e.message)); busy.value = false }
}

async function exportXlsx() {
  busy.value = true
  try {
    const resp = await exportDocXlsx(doc.value.id)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url; a.download = `накладна_${form.doc_number || doc.value.id}.xlsx`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    let detail = e.message
    if (e.response?.data instanceof Blob) detail = await e.response.data.text()
    else if (e.response?.data?.detail) detail = e.response.data.detail
    alert('Помилка експорту: ' + String(detail).slice(0, 500))
  } finally { busy.value = false }
}

onMounted(async () => {
  const [d, s, p, o] = await Promise.all([getDoc(route.params.id), getServices(), getPersons(), getOpTypes()])
  services.value = s.data; persons.value = p.data; opTypes.value = o.data
  applyDoc(d.data)
})
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; display:flex; flex-direction:column; gap:16px; }
.form-head { display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
.btn-back { background:transparent; border:none; color:var(--accent); cursor:pointer; font-family:inherit; font-size:13.5px; }
.head-title { display:flex; align-items:center; gap:10px; flex:1; }
.head-title b { font-size:15px; }
.head-btns { display:flex; gap:8px; }
.btn-sec, .btn-primary, .btn-danger { border-radius:var(--radius-sm); padding:6px 14px; cursor:pointer; font-family:inherit; font-size:13px; border:1px solid var(--border); background:var(--surface); color:var(--text-mid); }
.btn-primary { background:#16a34a; color:#fff; border-color:#16a34a; }
.btn-danger { color:#b91c1c; border-color:#fca5a5; }
.btn-sec:disabled, .btn-primary:disabled, .btn-danger:disabled { opacity:.5; cursor:not-allowed; }
.err-box { background:#fef2f2; border:1px solid #fca5a5; color:#991b1b; padding:10px 14px; border-radius:var(--radius-sm); font-size:13px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:12px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:baseline; gap:12px; }
.tile-title { font-weight:700; font-size:14px; } .tile-sub { font-size:12px; color:var(--text-light); }
.form-grid { padding:16px 20px; display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:12px 18px; }
.form-grid.three { grid-template-columns:repeat(3, 1fr); }
label { display:flex; flex-direction:column; gap:4px; font-size:12px; color:var(--text-light); }
.fi { border:1px solid var(--border); border-radius:var(--radius-sm); padding:6px 8px; font-family:inherit; font-size:13.5px; color:var(--text); background:var(--surface); }
.fi:disabled { background:var(--bg); color:var(--text-mid); }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:8px 12px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.col-i { width:40px; } .col-c { width:90px; } .col-u { width:70px; } .col-n { width:90px; text-align:right; } .col-s { width:150px; } .col-x { width:40px; }
.td-dim { color:var(--text-light); } .td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.td-x { text-align:center; }
.btn-x { border:none; background:transparent; color:#b91c1c; cursor:pointer; font-size:16px; }
.empty { text-align:center; padding:24px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; background:#e0e7ff; color:#3730a3; }
.st-draft { background:#f1f5f9; color:#475569; } .st-signed { background:#dcfce7; color:#166534; }
</style>
