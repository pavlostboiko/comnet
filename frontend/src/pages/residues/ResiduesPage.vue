<template>
  <div class="page-wrap">
    <TopBar />

    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Залишки</span>
          <div class="tile-tabs">
            <button class="tt-btn" :class="{ on: activeTab === 'unit' }" @click="switchTab('unit')">По підрозділах</button>
            <button class="tt-btn" :class="{ on: activeTab === 'recipient' }" @click="switchTab('recipient')">По особах</button>
          </div>
        </div>

        <!-- ═══ TAB: По підрозділах ═══ -->
        <template v-if="activeTab === 'unit'">
        <!-- Master: list of units -->
        <div v-if="!selectedUnit" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="sortable col-unit-name" @click="toggleSort('unit')">Підрозділ <span class="sort-arrow">{{ sortIcon('unit') }}</span></th>
                <th class="sortable col-count" @click="toggleSort('items_count')">Позицій <span class="sort-arrow">{{ sortIcon('items_count') }}</span></th>
                <th class="sortable col-qty" @click="toggleSort('total_qty_num')">Всього шт <span class="sort-arrow">{{ sortIcon('total_qty_num') }}</span></th>
                <th class="sortable col-amount" @click="toggleSort('total_amount_num')">Сума, грн <span class="sort-arrow">{{ sortIcon('total_amount_num') }}</span></th>
                <th class="col-acts"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="5" class="empty">Завантаження…</td></tr>
              <tr v-else-if="!sorted.length"><td colspan="5" class="empty">Немає підрозділів з залишками</td></tr>
              <tr v-for="u in sorted" :key="u.unit" class="click-row" @click="openUnit(u)">
                <td class="td-unit-name">{{ u.unit }}</td>
                <td class="td-num">{{ u.items_count }}</td>
                <td class="td-num">{{ fmtQty(u.total_qty_num) }}</td>
                <td class="td-num">{{ fmtPrice(u.total_amount_num) }}</td>
                <td class="td-acts">
                  <button class="btn-open" @click.stop="openUnit(u)">→</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Detail: items of selected unit -->
        <div v-else class="detail">
          <div class="detail-head">
            <button v-if="canGoBack" class="btn-back" @click="closeUnit">← Всі підрозділи</button>
            <div class="detail-title">Майно у: <b>{{ selectedUnit }}</b></div>
            <div class="detail-summary">{{ detail?.items?.length || 0 }} позицій</div>
          </div>
          <div v-if="detailLoading" class="empty">Завантаження…</div>
          <div v-else-if="!detail?.items?.length" class="empty">У цьому підрозділі порожньо</div>
          <div v-else class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="col-card">№ картки</th>
                  <th class="col-name">Найменування</th>
                  <th class="col-cat">Категорія</th>
                  <th class="col-unit">Од.</th>
                  <th class="col-serial">Серійний №</th>
                  <th class="col-qty">К-сть</th>
                  <th class="col-price">Ціна</th>
                  <th class="col-amount">Сума</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in detail.items" :key="it.item_card_num">
                  <td class="td-mono">{{ it.item_card_num }}</td>
                  <td>{{ it.name || '—' }}</td>
                  <td>{{ it.category || '—' }}</td>
                  <td class="td-center">{{ it.unit_of_measure || '—' }}</td>
                  <td class="td-mono td-dim">{{ it.serial_number || '—' }}</td>
                  <td class="td-num">{{ fmtQty(it.qty) }}</td>
                  <td class="td-num">{{ fmtPrice(it.price) }}</td>
                  <td class="td-num">{{ fmtPrice(it.amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        </template>

        <!-- ═══ TAB: По особах ═══ -->
        <template v-else>
        <!-- Master: recipients -->
        <div v-if="!selectedRecipient" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="sortable col-rec-name" @click="rToggleSort('callsign')">Прізвище <span class="sort-arrow">{{ rSortIcon('callsign') }}</span></th>
                <th class="sortable col-count" @click="rToggleSort('splits_count')">Видач <span class="sort-arrow">{{ rSortIcon('splits_count') }}</span></th>
                <th class="sortable col-count" @click="rToggleSort('serial_count')">Серійних <span class="sort-arrow">{{ rSortIcon('serial_count') }}</span></th>
                <th class="sortable col-qty" @click="rToggleSort('total_qty_num')">Всього шт <span class="sort-arrow">{{ rSortIcon('total_qty_num') }}</span></th>
                <th class="sortable col-amount" @click="rToggleSort('total_amount_num')">Сума, грн <span class="sort-arrow">{{ rSortIcon('total_amount_num') }}</span></th>
                <th class="col-acts"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="recipientsLoading"><td colspan="6" class="empty">Завантаження…</td></tr>
              <tr v-else-if="!rSorted.length"><td colspan="6" class="empty">Ні у кого немає майна</td></tr>
              <tr v-for="r in rSorted" :key="r.recipient_id" class="click-row" @click="openRecipient(r)">
                <td class="td-unit-name">{{ r.callsign }}</td>
                <td class="td-num">{{ r.splits_count }}</td>
                <td class="td-num">{{ r.serial_count }}</td>
                <td class="td-num">{{ fmtQty(r.total_qty_num) }}</td>
                <td class="td-num">{{ fmtPrice(r.total_amount_num) }}</td>
                <td class="td-acts"><button class="btn-open" @click.stop="openRecipient(r)">→</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Detail: recipient's holdings -->
        <div v-else class="detail">
          <div class="detail-head">
            <button class="btn-back" @click="closeRecipient">← Всі особи</button>
            <div class="detail-title">Майно у: <b>{{ recipientDetail?.callsign }}</b></div>
            <div class="detail-summary">
              {{ (recipientDetail?.splits?.length || 0) + (recipientDetail?.serial_items?.length || 0) }} позицій
            </div>
          </div>
          <div v-if="recipientDetailLoading" class="empty">Завантаження…</div>
          <template v-else>
            <!-- Non-serial splits -->
            <div v-if="recipientDetail?.splits?.length" class="table-wrap">
              <div class="section-label">Видачі (розділені):</div>
              <table>
                <thead>
                  <tr>
                    <th class="col-card">№ картки</th>
                    <th class="col-name">Найменування</th>
                    <th class="col-cat">Категорія</th>
                    <th class="col-unit">Од.</th>
                    <th class="col-qty">К-сть</th>
                    <th class="col-date">Дата видачі</th>
                    <th class="col-price">Ціна</th>
                    <th class="col-amount">Сума</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in recipientDetail.splits" :key="s.split_id">
                    <td class="td-mono">{{ s.item_number || '—' }}</td>
                    <td>{{ s.item_name || '—' }}</td>
                    <td>{{ s.category || '—' }}</td>
                    <td class="td-center">{{ s.unit_of_measure || '—' }}</td>
                    <td class="td-num">{{ fmtQty(s.qty) }}</td>
                    <td class="td-mono td-dim">{{ s.issued_at || '—' }}</td>
                    <td class="td-num">{{ fmtPrice(s.price) }}</td>
                    <td class="td-num">{{ fmtPrice(s.amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Serial items -->
            <div v-if="recipientDetail?.serial_items?.length" class="table-wrap">
              <div class="section-label">Серійне майно (закріплено):</div>
              <table>
                <thead>
                  <tr>
                    <th class="col-card">№ картки</th>
                    <th class="col-name">Найменування</th>
                    <th class="col-cat">Категорія</th>
                    <th class="col-serial">Серійний №</th>
                    <th class="col-unit">Од.</th>
                    <th class="col-qty">К-сть</th>
                    <th class="col-price">Ціна</th>
                    <th class="col-amount">Сума</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="it in recipientDetail.serial_items" :key="it.item_id">
                    <td class="td-mono">{{ it.item_number }}</td>
                    <td>{{ it.item_name || '—' }}</td>
                    <td>{{ it.category || '—' }}</td>
                    <td class="td-mono">{{ it.serial_number || '—' }}</td>
                    <td class="td-center">{{ it.unit_of_measure || '—' }}</td>
                    <td class="td-num">{{ fmtQty(it.qty) }}</td>
                    <td class="td-num">{{ fmtPrice(it.price) }}</td>
                    <td class="td-num">{{ fmtPrice(it.amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="!recipientDetail?.splits?.length && !recipientDetail?.serial_items?.length" class="empty">
              У цієї людини порожньо
            </div>
          </template>
        </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import {
  getResiduesByUnit, getResiduesByUnitDetail,
  getResiduesByRecipient, getResiduesByRecipientDetail,
} from '../../api/residues.js'
import { useSort } from '../../composables/useSort.js'
import { useAuthStore } from '../../stores/auth.js'

const auth = useAuthStore()

const activeTab = ref('unit')

// unit tab state
const rows = ref([])
const loading = ref(false)
const selectedUnit = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

// recipient tab state
const recipientRows = ref([])
const recipientsLoading = ref(false)
const selectedRecipient = ref(null)
const recipientDetail = ref(null)
const recipientDetailLoading = ref(false)

// Admins can navigate back to the master list; a scoped operator is stuck
// on their unit and shouldn't see the button.
const canGoBack = computed(() => auth.user?.role === 'admin')

// Enrich with numeric shadow fields for sort (backend sends strings)
const enriched = computed(() => rows.value.map(r => ({
  ...r,
  total_qty_num: Number(r.total_qty || 0),
  total_amount_num: Number(r.total_amount || 0),
})))
const { sorted, toggleSort, sortIcon } = useSort(enriched, 'unit', 'asc')

const rEnriched = computed(() => recipientRows.value.map(r => ({
  ...r,
  total_qty_num: Number(r.total_qty || 0),
  total_amount_num: Number(r.total_amount || 0),
})))
const { sorted: rSorted, toggleSort: rToggleSort, sortIcon: rSortIcon } = useSort(rEnriched, 'callsign', 'asc')

async function loadRecipients() {
  recipientsLoading.value = true
  try {
    const { data } = await getResiduesByRecipient()
    recipientRows.value = data
  } finally { recipientsLoading.value = false }
}

async function openRecipient(r) {
  selectedRecipient.value = r.recipient_id
  recipientDetail.value = null
  recipientDetailLoading.value = true
  try {
    const { data } = await getResiduesByRecipientDetail(r.recipient_id)
    recipientDetail.value = data
  } finally { recipientDetailLoading.value = false }
}
function closeRecipient() {
  selectedRecipient.value = null
  recipientDetail.value = null
}

function switchTab(t) {
  activeTab.value = t
  if (t === 'recipient' && recipientRows.value.length === 0 && !recipientsLoading.value) {
    loadRecipients()
  }
}

async function load() {
  loading.value = true
  try {
    const { data } = await getResiduesByUnit()
    rows.value = data
  } finally { loading.value = false }
}

// Non-admins with a linked person land directly on their unit's detail.
async function bootstrap() {
  // Ensure /auth/me is loaded (router guard usually did this already)
  if (!auth.user && auth.token) {
    try { await auth.fetchMe() } catch (_e) { /* handled elsewhere */ }
  }
  const user = auth.user
  if (user && user.role !== 'admin' && user.person_unit) {
    selectedUnit.value = user.person_unit
    detail.value = null
    detailLoading.value = true
    try {
      const { data } = await getResiduesByUnitDetail(user.person_unit)
      detail.value = data
    } finally { detailLoading.value = false }
    return
  }
  await load()
}
onMounted(bootstrap)

async function openUnit(u) {
  selectedUnit.value = u.unit
  detail.value = null
  detailLoading.value = true
  try {
    const { data } = await getResiduesByUnitDetail(u.unit)
    detail.value = data
  } finally { detailLoading.value = false }
}

function closeUnit() {
  selectedUnit.value = null
  detail.value = null
}

function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isInteger(n)) return String(n)
  return n.toLocaleString('uk-UA', { minimumFractionDigits: 0, maximumFractionDigits: 4 })
}
function fmtPrice(v) {
  if (v == null || v === '') return '—'
  return Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; }
.tile-title { font-weight:700; font-size:15px; color:var(--text); }
.tile-tabs { display:flex; gap:2px; background:var(--bg); padding:3px; border-radius:var(--radius-sm); }
.tt-btn { padding:5px 13px; border:none; background:transparent; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; }
.tt-btn.on { background:var(--surface); color:var(--text); box-shadow:0 1px 2px rgba(0,0,0,0.06); font-weight:600; }

.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 12px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
th.sortable { cursor:pointer; user-select:none; }
th.sortable:hover { background:var(--border-light); }
.sort-arrow { color:var(--text-light); font-size:10px; margin-left:3px; opacity:0.5; }
th.sortable:hover .sort-arrow { opacity:1; }

.col-unit-name { width:40%; }
.col-count     { width:120px; text-align:right; }
.col-qty       { width:120px; text-align:right; }
.col-amount    { width:160px; text-align:right; }
.col-acts      { width:60px; }

.click-row { cursor:pointer; }
.click-row:hover { background:var(--bg); }
.td-unit-name { font-weight:600; color:var(--text); }
.td-num { text-align:right; font-family:'DM Mono', monospace; }
.td-mono { font-family:'DM Mono', monospace; font-size:12px; }
.td-center { text-align:center; }
.td-dim { color:var(--text-light); }
.td-acts { text-align:center; }
.btn-open { background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); padding:3px 10px; cursor:pointer; color:var(--text-mid); font-size:14px; }
.btn-open:hover { background:var(--bg); color:var(--text); }
.empty { text-align:center; padding:40px; color:var(--text-light); font-style:italic; }

.detail { }
.detail-head { padding:12px 20px; display:flex; align-items:center; gap:20px; border-bottom:1px solid var(--border-light); background:var(--bg); }
.btn-back { background:transparent; border:none; color:var(--accent); cursor:pointer; font-family:inherit; font-size:13.5px; padding:4px 0; }
.btn-back:hover { text-decoration:underline; }
.detail-title { font-size:14px; color:var(--text-mid); }
.detail-title b { color:var(--text); }
.detail-summary { margin-left:auto; font-size:12.5px; color:var(--text-light); }

.col-card    { width:110px; }
.col-name    { width:26%; }
.col-cat     { width:100px; }
.col-unit    { width:60px; }
.col-serial  { width:12%; }
.col-price   { width:100px; text-align:right; }
.col-amount  { width:120px; text-align:right; }

.col-rec-name { width:30%; }
.col-date     { width:120px; }
.section-label { padding:12px 20px 6px; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; }
</style>
