<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Майно</span>
          <select v-if="isAdmin" class="sel" v-model="serviceId">
            <option :value="null">— усі служби —</option>
            <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <!-- Тип обліку: все / облік / ндм (в один рядок із вибором служби) -->
          <span class="sub-label">Тип</span>
          <span class="sub-chip" :class="{ on: officialFilter === 'all' }" @click="officialFilter = 'all'">Все</span>
          <span class="sub-chip" :class="{ on: officialFilter === 'official' }" @click="officialFilter = 'official'">Облік</span>
          <span class="sub-chip" :class="{ on: officialFilter === 'ndm' }" @click="officialFilter = 'ndm'">НДМ</span>
          <button v-if="isAdmin" class="btn-add" @click="openAdd">+ Додати</button>
        </div>

        <!-- Пошук -->
        <div class="search-row">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input ref="searchRef" v-model="search" placeholder="Пошук за назвою, кодом…" @keydown.esc="search=''" />
          <button v-if="search" class="search-clear" @click="search=''; searchRef?.focus()">×</button>
        </div>

        <!-- Категорії -->
        <div class="sub-row" v-if="categories.length">
          <span class="sub-label">Категорія</span>
          <span v-for="c in categories" :key="c" class="sub-chip" :class="{ on: category === c }" @click="category = category === c ? null : c">{{ c }}</span>
        </div>

        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="sortable" @click="toggleSort('name')">Найменування <span class="arr">{{ sortIcon('name') }}</span></th>
              <th class="sortable col-cat" @click="toggleSort('category')">Категорія <span class="arr">{{ sortIcon('category') }}</span></th>
              <th class="col-svc" v-if="isAdmin && !serviceId">Служба</th>
              <th class="col-obl">Облік</th>
              <th class="col-type">Тип</th>
              <th class="col-uom">Од.</th>
              <th class="sortable col-total" @click="toggleSort('total_num')">Всього <span class="arr">{{ sortIcon('total_num') }}</span></th>
              <th class="sortable col-price" @click="toggleSort('price_num')">Вартість <span class="arr">{{ sortIcon('price_num') }}</span></th>
              <th v-if="isAdmin" class="col-acts"></th>
            </tr></thead>
            <tbody>
              <tr v-if="!sorted.length"><td :colspan="isAdmin ? 9 : 8" class="empty">Нічого не знайдено</td></tr>
              <tr v-for="n in sorted" :key="n.id" class="click-row" @click="openWhere(n)">
                <td class="td-name">{{ n.name }}</td>
                <td class="td-dim">{{ n.category || '—' }}</td>
                <td class="td-dim" v-if="isAdmin && !serviceId">{{ serviceName(n.service_id) }}</td>
                <td><span class="chip" :class="n.is_official ? 'chip-gov' : 'chip-vol'">{{ n.is_official ? 'облік' : 'ндм' }}</span></td>
                <td><span class="chip" :class="n.is_serialized ? 'chip-ser' : 'chip-non'">{{ n.is_serialized ? 'серійне' : 'несерійне' }}</span></td>
                <td class="td-center">{{ n.unit_of_measure || '—' }}</td>
                <td class="td-num"><b>{{ totalOf(n.id) }}</b></td>
                <td class="td-num">{{ n.price != null ? Number(n.price).toFixed(2) : '—' }}</td>
                <td v-if="isAdmin" class="td-acts">
                  <button class="act e" @click.stop="openEdit(n)">✎</button>
                  <button class="act d" @click.stop="del(n)">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="t-foot">Показано <b>{{ sorted.length }}</b> з <b>{{ nomenclature.length }}</b> позицій</div>
      </div>
    </div>

    <!-- Add/Edit modal (спільний компонент — однакова форма створення й редагування) -->
    <NomenclatureModal :open="modalOpen" :item="editItem" :services="services"
      :categories="categories" :default-service-id="serviceId"
      @saved="onSaved" @close="modalOpen=false" />

    <!-- Де знаходиться modal -->
    <div class="overlay" :class="{ open: !!whereData }" @click.self="whereData=null">
      <div v-if="whereData" class="modal wide">
        <div class="modal-head">
          <span class="modal-title"><b>{{ whereData.name }}</b></span>
          <div class="wtabs">
            <button :class="{ on: whereTab==='where' }" @click="whereTab='where'">Де знаходиться</button>
            <button :class="{ on: whereTab==='history' }" @click="showHistory">Історія</button>
          </div>
          <button class="modal-close" @click="whereData=null">✕</button>
        </div>
        <div class="modal-body">
         <!-- ── Історія ── -->
         <template v-if="whereTab==='history'">
           <div v-if="historyLoading" class="empty">Завантаження…</div>
           <HistoryTimeline v-else :events="history" />
         </template>
          <!-- ── Де знаходиться ── -->
          <!-- Несерійне: по складах -->
          <template v-else-if="!whereData.is_serialized">
            <table class="w-table">
              <thead><tr><th>Склад</th><th class="wc-off">Тип</th><th class="wc-num">К-сть</th></tr></thead>
              <tbody>
                <tr v-if="!whereData.nonserial.length"><td colspan="3" class="empty">Ніде немає залишку</td></tr>
                <tr v-for="(r, i) in whereData.nonserial" :key="i">
                  <td class="td-name">{{ r.warehouse_name }}</td>
                  <td><span class="chip" :class="r.is_official ? 'chip-gov' : 'chip-vol'">{{ r.is_official ? 'облік' : 'ндм' }}</span></td>
                  <td class="td-num">{{ fmtQty(r.qty) }}</td>
                </tr>
              </tbody>
            </table>
          </template>
          <!-- Серійне: кожен екземпляр -->
          <template v-else>
            <table class="w-table">
              <thead><tr><th>Серійний №</th><th>Картка</th><th>Склад</th><th>На кому</th></tr></thead>
              <tbody>
                <tr v-if="!whereData.serial.length"><td colspan="4" class="empty">Ніде не розміщено</td></tr>
                <tr v-for="s in whereData.serial" :key="s.instance_id">
                  <td class="td-mono">{{ s.serial_no }}</td>
                  <td class="td-mono td-dim">{{ s.card_number || '—' }}</td>
                  <td class="td-name">{{ s.warehouse_name }}</td>
                  <td class="td-dim">{{ s.holder || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getServices } from '../../api/settings.js'
import { getNomenclature, deleteNomenclature } from '../../api/nomenclature.js'
import { whereIs, getTotals, itemHistory } from '../../api/custody.js'
import HistoryTimeline from '../../components/HistoryTimeline.vue'
import NomenclatureModal from '../../components/NomenclatureModal.vue'
import { useSort } from '../../composables/useSort.js'
import { useAuthStore } from '../../stores/auth.js'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const services = ref([])
const nomenclature = ref([])
const serviceId = ref(null)
const search = ref('')
const searchRef = ref(null)
const category = ref(null)
const officialFilter = ref('all')   // all | official | ndm

const totals = ref({})
const serviceName = (id) => services.value.find(s => s.id === id)?.name || '—'
const totalOf = (id) => {
  const v = totals.value[String(id)]
  return v != null ? fmtQty(v) : '0'
}
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

const filtered = computed(() => {
  let list = nomenclature.value
  if (serviceId.value) list = list.filter(n => n.service_id === serviceId.value)
  if (officialFilter.value === 'official') list = list.filter(n => n.is_official)
  else if (officialFilter.value === 'ndm') list = list.filter(n => !n.is_official)
  if (category.value) list = list.filter(n => n.category === category.value)
  const q = search.value.trim().toLowerCase()
  if (q) list = list.filter(n =>
    (n.name || '').toLowerCase().includes(q) || (n.code || '').toLowerCase().includes(q))
  return list.map(n => ({ ...n, price_num: Number(n.price || 0), total_num: Number(totals.value[String(n.id)] || 0) }))
})
const { sorted, toggleSort, sortIcon } = useSort(filtered, 'name', 'asc')

const categories = computed(() => {
  const src = serviceId.value ? nomenclature.value.filter(n => n.service_id === serviceId.value) : nomenclature.value
  return [...new Set(src.map(n => n.category).filter(Boolean))].sort()
})

async function load() {
  const [s, n, t] = await Promise.all([getServices(), getNomenclature(), getTotals()])
  services.value = s.data
  nomenclature.value = n.data
  totals.value = t.data
}
onMounted(load)

const modalOpen = ref(false)
const editItem = ref(null)
function openAdd() { editItem.value = null; modalOpen.value = true }
function openEdit(n) { editItem.value = n; modalOpen.value = true }
async function onSaved() { modalOpen.value = false; await load() }
async function del(n) {
  if (!confirm(`Видалити «${n.name}»?`)) return
  try { await deleteNomenclature(n.id); await load() }
  catch (e) { alert(e?.response?.data?.detail || 'Не вдалось видалити') }
}

const whereData = ref(null)
const whereTab = ref('where')
const history = ref([])
const historyLoading = ref(false)
async function openWhere(n) {
  whereData.value = null
  whereTab.value = 'where'
  history.value = []
  try {
    const { data } = await whereIs(n.id)
    whereData.value = data
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось завантажити')
  }
}
async function showHistory() {
  whereTab.value = 'history'
  if (history.value.length || !whereData.value) return
  historyLoading.value = true
  try {
    const { data } = await itemHistory(whereData.value.nomenclature_id)
    history.value = data.events || []
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось завантажити історію')
  } finally {
    historyLoading.value = false
  }
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:14px; }
.tile-title { font-weight:700; font-size:15px; }
.sel { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; min-width:200px; }
.btn-add { margin-left:auto; padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.search-row { padding:10px 20px; display:flex; align-items:center; gap:8px; border-bottom:1px solid var(--border-light); }
.search-icon { width:14px; height:14px; color:var(--text-light); flex-shrink:0; }
.search-row input { flex:1; border:none; background:transparent; font-family:inherit; font-size:14px; outline:none; color:var(--text); }
.search-clear { width:22px; height:22px; border:none; background:transparent; cursor:pointer; color:var(--text-light); font-size:16px; }
.sub-row { padding:10px 20px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; border-bottom:1px solid var(--border-light); }
.sub-label { font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; margin-right:6px; }
.sub-chip { padding:3px 10px; border:1px solid var(--border); border-radius:var(--radius-pill); font-size:12px; color:var(--text-mid); cursor:pointer; }
.sub-chip.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
th.sortable { cursor:pointer; user-select:none; }
.arr { color:var(--text-light); font-size:10px; opacity:0.5; }
.col-cat { width:14%; } .col-svc { width:14%; } .col-obl { width:90px; } .col-type { width:100px; } .col-uom { width:56px; } .col-total { width:90px; text-align:right; } .col-price { width:100px; text-align:right; } .col-acts { width:70px; }
.td-name { font-weight:600; color:var(--text); }
.td-dim { color:var(--text-light); } .td-center { text-align:center; } .td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; } .td-acts { text-align:center; }
.act { background:transparent; border:none; cursor:pointer; font-size:13px; color:var(--text-light); padding:2px 5px; }
.act.e:hover { color:var(--accent); } .act.d:hover { color:#dc2626; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.chip-ser { background:#dbeafe; color:#1e40af; } .chip-non { background:#f1f5f9; color:#475569; }
.chip-gov { background:#dbeafe; color:#1e40af; } .chip-vol { background:#fef3c7; color:#854d0e; }
.chip-receipt { background:#dcfce7; color:#166534; } .chip-transfer { background:#e0e7ff; color:#3730a3; }
.chip-writeoff { background:#fee2e2; color:#991b1b; }
.chip-issue { background:#fef3c7; color:#854d0e; } .chip-return { background:#dcfce7; color:#166534; }
.wtabs { display:flex; gap:6px; margin-left:16px; }
.wtabs button { border:1px solid var(--border); background:var(--bg); border-radius:var(--radius-sm); padding:4px 10px; cursor:pointer; font-family:inherit; font-size:12.5px; color:var(--text-mid); }
.wtabs button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.click-row { cursor:pointer; }
.click-row:hover { background:var(--bg); }
.modal.wide { width:min(680px,100%); }
.w-table { width:100%; border-collapse:collapse; }
.w-table th, .w-table td { padding:8px 12px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
.w-table th { color:var(--text-light); font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.wc-off { width:130px; } .wc-num { width:100px; text-align:right; }
.wc-date { width:110px; } .wc-ev { width:120px; }
.modal-head { align-items:center; }
.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:60px 20px; z-index:1200; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(460px,100%); }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-weight:700; font-size:14px; } .modal-close { border:none; background:transparent; font-size:16px; color:var(--text-light); cursor:pointer; }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:8px; }
.fi { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; }
.err { margin-top:10px; padding:8px 10px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-sec { padding:7px 14px; background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; cursor:pointer; }
.btn-pri { padding:7px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
</style>
