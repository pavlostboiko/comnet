<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Переміщення</span>
          <select class="wh-select" v-model="filterWh" @change="load">
            <option :value="null">— усі склади —</option>
            <optgroup label="Склади служб">
              <option v-for="w in serviceWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
            <optgroup label="Склади підрозділів">
              <option v-for="w in unitWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
          <input class="d-inp" type="date" v-model="dateFrom" @change="load" title="Від дати" />
          <input class="d-inp" type="date" v-model="dateTo" @change="load" title="До дати" />
          <button v-if="filterWh || dateFrom || dateTo" class="btn-clear" @click="resetFilters">Скинути</button>
        </div>

        <div class="filter-row">
          <button v-for="k in KINDS" :key="k.key" class="f-chip" :class="{ on: kind === k.key }"
            @click="kind = k.key">
            {{ k.label }} <span class="f-count">{{ countOf(k.key) }}</span>
          </button>
        </div>

        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="col-date">Дата</th><th class="col-type">Подія</th>
              <th>Звідки → Куди / Кому</th><th>Номенклатура</th><th class="col-serial">Картка</th>
              <th class="col-doc">Накладна</th><th class="col-num">К-сть</th>
            </tr></thead>
            <tbody>
              <tr v-if="loading"><td colspan="7" class="empty">Завантаження…</td></tr>
              <tr v-else-if="!filtered.length"><td colspan="7" class="empty">Немає подій</td></tr>
              <tr v-for="e in filtered" :key="`${e.source}-${e.source_id}-${e.kind}`">
                <td class="td-mono">{{ e.date }}</td>
                <td><span class="chip" :class="`mv-${eventKey(e)}`">{{ eventLabel(e) }}</span></td>
                <td class="td-dim">{{ whereLabel(e) }}</td>
                <td>{{ e.nomenclature_name || '—' }}</td>
                <td class="td-mono td-dim">{{ e.card_number || e.serial_no || '—' }}</td>
                <td class="td-mono td-dim">{{ e.doc_number || '—' }}</td>
                <td class="td-num">{{ fmtQty(e.qty) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="t-foot">
          Показано <b>{{ filtered.length }}</b> з <b>{{ events.length }}</b>
          <span v-if="total > events.length"> · всього {{ total }}, у списку — найновіші {{ events.length }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses } from '../../api/structure.js'
import { historyFeed } from '../../api/custody.js'

// Одна стрічка подій: рухи між складами + видачі/повернення особам.
const KINDS = [
  { key: 'all', label: 'Все' },
  { key: 'receipt', label: 'Надходження' },
  { key: 'transfer', label: 'Переміщення' },
  { key: 'writeoff', label: 'Списання' },
  { key: 'issued', label: 'Видано' },
  { key: 'returned', label: 'Повернуто' },
  { key: 'point', label: 'Точка' },
]

const events = ref([])
const total = ref(0)
const warehouses = ref([])
const filterWh = ref(null)
const dateFrom = ref('')
const dateTo = ref('')
const kind = ref('all')
const loading = ref(true)

const serviceWarehouses = computed(() => warehouses.value.filter(w => w.type === 'service'))
const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit'))

const eventKey = (e) => e.kind === 'movement' ? e.type : e.kind
const matches = (e, k) => k === 'all' || eventKey(e) === k
const filtered = computed(() => events.value.filter(e => matches(e, kind.value)))
const countOf = (k) => events.value.filter(e => matches(e, k)).length

function eventLabel(e) {
  return { receipt: 'надходження', transfer: 'переміщення', writeoff: 'списання',
           issued: 'видано', returned: 'повернуто', point: 'точка' }[eventKey(e)] || eventKey(e)
}
function whereLabel(e) {
  // Подія точки: у from/to — назви точок, склад окремо.
  if (e.kind === 'point') return `${e.warehouse || '—'}: ${e.from_warehouse || '—'} → ${e.to_warehouse || '—'}`
  if (e.kind === 'issued') return `${e.to_warehouse || '—'} → ${e.person || '—'}`
  if (e.kind === 'returned') return `${e.person || '—'} → ${e.to_warehouse || '—'}`
  return `${e.from_warehouse || 'ззовні'} → ${e.to_warehouse || 'списано'}`
}
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

async function load() {
  loading.value = true
  try {
    const { data } = await historyFeed({
      warehouse_id: filterWh.value || undefined,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined,
    })
    events.value = data.events
    total.value = data.total
  } finally {
    loading.value = false
  }
}
function resetFilters() {
  filterWh.value = null; dateFrom.value = ''; dateTo.value = ''
  load()
}

onMounted(async () => {
  warehouses.value = (await getWarehouses()).data
  await load()
})
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.tile-title { font-weight:700; font-size:15px; margin-right:auto; }
.wh-select, .d-inp { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; background:var(--surface); color:var(--text); }
.wh-select { min-width:220px; }
.btn-clear { border:1px solid var(--border); background:var(--surface); color:var(--text-mid); border-radius:var(--radius-sm); padding:6px 10px; font-family:inherit; font-size:12.5px; cursor:pointer; }
.filter-row { padding:10px 20px; display:flex; gap:8px; flex-wrap:wrap; border-bottom:1px solid var(--border-light); }
.f-chip { border:1px solid var(--border); background:var(--surface); color:var(--text-mid); border-radius:999px; padding:4px 12px; font-family:inherit; font-size:12.5px; cursor:pointer; }
.f-chip.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.f-count { opacity:.75; font-size:11px; margin-left:4px; }
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
.mv-issued { background:#fef3c7; color:#92400e; } .mv-returned { background:#f1f5f9; color:#475569; }
.mv-point { background:#ede9fe; color:#5b21b6; }
.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }
</style>
