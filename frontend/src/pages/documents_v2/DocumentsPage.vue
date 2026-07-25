<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Документи</span>
          <span class="tile-sub">накладні з переміщень</span>
        </div>

        <!-- Master -->
        <div v-if="!selected">
          <div class="search-row">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            <input v-model="search" placeholder="Пошук за номером накладної…" />
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Накладна №</th><th class="col-date">Дата</th><th class="col-num">Позицій</th><th class="col-acts"></th></tr></thead>
              <tbody>
                <tr v-if="loading"><td colspan="4" class="empty">Завантаження…</td></tr>
                <tr v-else-if="!filteredDocs.length"><td colspan="4" class="empty">Немає документів</td></tr>
                <tr v-for="d in filteredDocs" :key="d.doc_number" class="click-row" @click="selected = d">
                  <td class="td-name td-mono">{{ d.doc_number }}</td>
                  <td class="td-mono td-dim">{{ d.date }}</td>
                  <td class="td-num">{{ d.count }}</td>
                  <td class="td-acts"><button class="btn-open" @click.stop="selected = d">→</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="t-foot">Показано <b>{{ filteredDocs.length }}</b> з <b>{{ docs.length }}</b> документів</div>
        </div>

        <!-- Detail -->
        <div v-else class="detail">
          <div class="detail-head">
            <button class="btn-back" @click="selected = null">← Усі документи</button>
            <div class="detail-title">Накладна <b>{{ selected.doc_number }}</b> · {{ selected.date }}</div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th class="col-type">Тип</th><th>Звідки → Куди</th><th>Номенклатура</th><th class="col-serial">Картка/серійний</th><th class="col-num">К-сть</th></tr></thead>
              <tbody>
                <tr v-for="m in selected.rows" :key="m.id">
                  <td><span class="chip" :class="`mv-${m.type}`">{{ moveLabel(m.type) }}</span></td>
                  <td class="td-dim">{{ warehouseName(m.from_warehouse_id) }} → {{ warehouseName(m.to_warehouse_id) }}</td>
                  <td>{{ nomName(m.nomenclature_id) }}</td>
                  <td class="td-mono td-dim">{{ m.card_number || (m.instance_id ? '№' + m.instance_id : '—') }}</td>
                  <td class="td-num">{{ fmtQty(m.quantity) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses } from '../../api/structure.js'
import { getNomenclature } from '../../api/nomenclature.js'
import { getMovements } from '../../api/custody.js'

const movements = ref([])
const warehouses = ref([])
const nomenclature = ref([])
const loading = ref(true)
const search = ref('')
const selected = ref(null)

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
function moveLabel(t) { return { receipt: 'надходження', transfer: 'переміщення', writeoff: 'списання' }[t] || t }
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

// Group movements by doc_number → one document per накладна
const docs = computed(() => {
  const map = new Map()
  for (const m of movements.value) {
    const key = m.doc_number || '(без номера)'
    let d = map.get(key)
    if (!d) { d = { doc_number: key, date: m.date, count: 0, rows: [] }; map.set(key, d) }
    d.rows.push(m)
    d.count++
    if (m.date && (!d.date || m.date < d.date)) d.date = m.date
  }
  return [...map.values()].sort((a, b) => (b.date || '').localeCompare(a.date || ''))
})
const filteredDocs = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? docs.value.filter(d => d.doc_number.toLowerCase().includes(q)) : docs.value
})

onMounted(async () => {
  const [m, w, n] = await Promise.all([getMovements(), getWarehouses(), getNomenclature()])
  movements.value = m.data
  warehouses.value = w.data
  nomenclature.value = n.data
  loading.value = false
})
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:baseline; gap:12px; }
.tile-title { font-weight:700; font-size:15px; }
.tile-sub { font-size:12px; color:var(--text-light); }
.search-row { padding:10px 20px; display:flex; align-items:center; gap:8px; border-bottom:1px solid var(--border-light); }
.search-icon { width:14px; height:14px; color:var(--text-light); flex-shrink:0; }
.search-row input { flex:1; border:none; background:transparent; font-family:inherit; font-size:14px; outline:none; color:var(--text); }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-date { width:120px; } .col-type { width:130px; } .col-serial { width:150px; } .col-num { width:100px; text-align:right; } .col-acts { width:60px; }
.td-name { font-weight:600; color:var(--text); }
.td-dim { color:var(--text-light); } .td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.td-acts { text-align:center; }
.click-row { cursor:pointer; } .click-row:hover { background:var(--bg); }
.btn-open { background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); padding:3px 10px; cursor:pointer; color:var(--text-mid); }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.mv-receipt { background:#dcfce7; color:#166534; } .mv-transfer { background:#e0e7ff; color:#3730a3; } .mv-writeoff { background:#fee2e2; color:#991b1b; }
.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }
.detail-head { padding:12px 20px; display:flex; align-items:center; gap:20px; border-bottom:1px solid var(--border-light); background:var(--bg); }
.btn-back { background:transparent; border:none; color:var(--accent); cursor:pointer; font-family:inherit; font-size:13.5px; }
.detail-title { font-size:14px; color:var(--text-mid); } .detail-title b { color:var(--text); }
</style>
