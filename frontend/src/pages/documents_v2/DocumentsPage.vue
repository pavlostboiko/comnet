<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Документи</span>
          <div class="tabs">
            <button :class="{ on: tab === 'docs' }" @click="tab = 'docs'">Накладні / акти</button>
            <button :class="{ on: tab === 'free' }" @click="tab = 'free'">Без документа</button>
          </div>
        </div>

        <!-- Документи -->
        <div v-if="tab === 'docs'">
          <div class="search-row">
            <input v-model="search" placeholder="Пошук за номером…" />
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Номер</th><th class="col-date">Дата</th><th class="col-type">Тип</th>
                <th>Звідки → Куди</th><th class="col-num">Позицій</th>
                <th class="col-type">Статус</th><th class="col-acts"></th>
              </tr></thead>
              <tbody>
                <tr v-if="loading"><td colspan="7" class="empty">Завантаження…</td></tr>
                <tr v-else-if="!filteredDocs.length"><td colspan="7" class="empty">Немає документів</td></tr>
                <tr v-for="d in filteredDocs" :key="d.id" class="click-row" @click="open(d.id)">
                  <td class="td-name td-mono">{{ d.doc_number || '—' }}</td>
                  <td class="td-mono td-dim">{{ d.doc_date || '—' }}</td>
                  <td><span class="chip">{{ opLabel(d.operation) }} · {{ d.form }}</span></td>
                  <td class="td-dim">{{ d.from_unit || '—' }} → {{ d.to_unit || '—' }}</td>
                  <td class="td-num">{{ d.items_count }}</td>
                  <td><span class="chip" :class="`st-${d.status}`">{{ stLabel(d.status) }}</span></td>
                  <td class="td-acts"><button class="btn-open" @click.stop="open(d.id)">→</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="t-foot">Показано <b>{{ filteredDocs.length }}</b> з <b>{{ docs.length }}</b></div>
        </div>

        <!-- Без документа -->
        <div v-else>
          <div v-if="loading" class="empty">Завантаження…</div>
          <div v-else-if="!freeGroups.length" class="empty">Усі переміщення оформлені документами</div>
          <div v-for="g in freeGroups" :key="g.key" class="free-group">
            <div class="free-head">
              <span class="free-dir">{{ warehouseName(g.from) }} → {{ warehouseName(g.to) }}</span>
              <button class="btn-add" :disabled="!g.selected.size || busy" @click="makeDoc(g)">
                Створити документ ({{ g.selected.size }})
              </button>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr>
                  <th class="col-chk"><input type="checkbox" :checked="allChecked(g)" @change="toggleAll(g, $event)" /></th>
                  <th class="col-date">Дата</th><th>Номенклатура</th>
                  <th class="col-serial">Картка/серійний</th><th class="col-num">К-сть</th>
                  <th class="col-acts"></th>
                </tr></thead>
                <tbody>
                  <tr v-for="m in g.rows" :key="m.id">
                    <td><input type="checkbox" :checked="g.selected.has(m.id)" @change="toggle(g, m.id, $event)" /></td>
                    <td class="td-mono td-dim">{{ m.date }}</td>
                    <td>{{ nomName(m.nomenclature_id) }}</td>
                    <td class="td-mono td-dim">{{ m.card_number || (m.instance_id ? '№' + m.instance_id : '—') }}</td>
                    <td class="td-num">{{ fmtQty(m.quantity) }}</td>
                    <td><button class="btn-revoke" :disabled="busy" @click="revoke(m)">Відкликати</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses } from '../../api/structure.js'
import { getNomenclature } from '../../api/nomenclature.js'
import { getMovements, getDocs, createDoc, deleteMovement } from '../../api/custody.js'

const router = useRouter()
const tab = ref('docs')
const loading = ref(true)
const busy = ref(false)
const search = ref('')
const docs = ref([])
const movements = ref([])
const warehouses = ref([])
const nomenclature = ref([])
const selections = reactive({})   // groupKey → Set

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
function opLabel(o) { return { receipt: 'надходження', transfer: 'переміщення' }[o] || o }
function stLabel(s) { return { draft: 'чернетка', signed: 'підписано' }[s] || s }
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

const filteredDocs = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? docs.value.filter(d => (d.doc_number || '').toLowerCase().includes(q)) : docs.value
})

// Ungrouped transfer movements grouped by direction (from → to)
const freeGroups = computed(() => {
  const map = new Map()
  for (const m of movements.value) {
    if (m.document_id != null || m.type !== 'transfer') continue
    const key = `${m.from_warehouse_id}>${m.to_warehouse_id}`
    if (!map.has(key)) {
      if (!selections[key]) selections[key] = new Set()
      map.set(key, { key, from: m.from_warehouse_id, to: m.to_warehouse_id, rows: [], selected: selections[key] })
    }
    map.get(key).rows.push(m)
  }
  return [...map.values()]
})

function toggle(g, id, ev) {
  if (ev.target.checked) g.selected.add(id); else g.selected.delete(id)
}
function allChecked(g) { return g.rows.length > 0 && g.rows.every(m => g.selected.has(m.id)) }
function toggleAll(g, ev) {
  if (ev.target.checked) g.rows.forEach(m => g.selected.add(m.id))
  else g.selected.clear()
}

function open(id) { router.push(`/docs/${id}`) }

async function makeDoc(g) {
  busy.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    const { data } = await createDoc({
      operation: 'transfer', form: 'накладна', doc_date: today,
      movement_ids: [...g.selected],
    })
    router.push(`/docs/${data.id}`)
  } catch (e) {
    alert('Помилка створення: ' + (e.response?.data?.detail || e.message))
  } finally { busy.value = false }
}

async function revoke(m) {
  if (!confirm('Відкликати це переміщення? Майно повернеться на попередній склад, запис зникне з історії. Дію не можна скасувати.')) return
  busy.value = true
  try {
    await deleteMovement(m.id)
    await load()
  } catch (e) {
    alert('Не вдалося відкликати: ' + (e.response?.data?.detail || e.message))
  } finally { busy.value = false }
}

async function load() {
  loading.value = true
  const [d, m, w, n] = await Promise.all([getDocs(), getMovements(), getWarehouses(), getNomenclature()])
  docs.value = d.data
  movements.value = m.data
  warehouses.value = w.data
  nomenclature.value = n.data
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:20px; }
.tile-title { font-weight:700; font-size:15px; }
.tabs { display:flex; gap:6px; }
.tabs button { border:1px solid var(--border); background:var(--bg); border-radius:var(--radius-sm); padding:5px 12px; cursor:pointer; font-family:inherit; font-size:13px; color:var(--text-mid); }
.tabs button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.search-row { padding:10px 20px; border-bottom:1px solid var(--border-light); }
.search-row input { width:100%; border:none; background:transparent; font-family:inherit; font-size:14px; outline:none; color:var(--text); }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-date { width:120px; } .col-type { width:150px; } .col-serial { width:160px; } .col-num { width:90px; text-align:right; } .col-acts { width:60px; } .col-chk { width:40px; }
.td-name { font-weight:600; } .td-dim { color:var(--text-light); }
.td-num { text-align:right; font-family:'DM Mono',monospace; }
.btn-revoke { padding:3px 10px; background:transparent; border:1px solid #dc2626; color:#dc2626; border-radius:var(--radius-sm); font-family:inherit; font-size:12px; cursor:pointer; white-space:nowrap; }
.btn-revoke:disabled { opacity:0.5; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.td-acts { text-align:center; }
.click-row { cursor:pointer; } .click-row:hover { background:var(--bg); }
.btn-open { background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); padding:3px 10px; cursor:pointer; color:var(--text-mid); }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; background:#e0e7ff; color:#3730a3; }
.st-draft { background:#f1f5f9; color:#475569; } .st-signed { background:#dcfce7; color:#166534; }
.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }
.free-group { border-bottom:6px solid var(--bg); }
.free-head { padding:10px 20px; display:flex; align-items:center; justify-content:space-between; background:var(--bg); }
.free-dir { font-weight:600; font-size:13px; }
.btn-add { border:1px solid var(--accent); background:var(--accent); color:#fff; border-radius:var(--radius-sm); padding:5px 12px; cursor:pointer; font-family:inherit; font-size:13px; }
.btn-add:disabled { opacity:.45; cursor:not-allowed; }
</style>
