<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Переміщення</span>
          <select class="wh-select" v-model="filterWh">
            <option :value="null">— усі склади —</option>
            <optgroup label="Склади служб">
              <option v-for="w in serviceWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
            <optgroup label="Склади підрозділів">
              <option v-for="w in unitWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="col-date">Дата</th><th class="col-type">Тип</th>
              <th>Звідки → Куди</th><th>Номенклатура</th><th class="col-serial">Картка</th>
              <th class="col-doc">Накладна</th><th class="col-num">К-сть</th>
            </tr></thead>
            <tbody>
              <tr v-if="loading"><td colspan="6" class="empty">Завантаження…</td></tr>
              <tr v-else-if="!filtered.length"><td colspan="6" class="empty">Немає рухів</td></tr>
              <tr v-for="m in filtered" :key="m.id">
                <td class="td-mono">{{ m.date }}</td>
                <td><span class="chip" :class="`mv-${m.type}`">{{ moveLabel(m.type) }}</span></td>
                <td class="td-dim">{{ warehouseName(m.from_warehouse_id) }} → {{ warehouseName(m.to_warehouse_id) }}</td>
                <td>{{ nomName(m.nomenclature_id) }}</td>
                <td class="td-mono td-dim">{{ m.card_number || '—' }}</td>
                <td class="td-mono td-dim">{{ m.doc_number || '—' }}</td>
                <td class="td-num">{{ fmtQty(m.quantity) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="t-foot">Показано <b>{{ filtered.length }}</b> з <b>{{ movements.length }}</b></div>
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
const filterWh = ref(null)
const loading = ref(true)

const serviceWarehouses = computed(() => warehouses.value.filter(w => w.type === 'service'))
const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit'))
const filtered = computed(() => {
  if (!filterWh.value) return movements.value
  return movements.value.filter(m => m.from_warehouse_id === filterWh.value || m.to_warehouse_id === filterWh.value)
})

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
function moveLabel(t) { return { receipt: 'надходження', transfer: 'переміщення', writeoff: 'списання' }[t] || t }
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

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
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; }
.tile-title { font-weight:700; font-size:15px; }
.wh-select { margin-left:auto; padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; min-width:220px; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-date { width:110px; } .col-type { width:130px; } .col-serial { width:120px; } .col-doc { width:120px; } .col-num { width:90px; text-align:right; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.td-dim { color:var(--text-light); }
.td-num { text-align:right; font-family:'DM Mono',monospace; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.mv-receipt { background:#dcfce7; color:#166534; } .mv-transfer { background:#e0e7ff; color:#3730a3; } .mv-writeoff { background:#fee2e2; color:#991b1b; }
.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }
</style>
