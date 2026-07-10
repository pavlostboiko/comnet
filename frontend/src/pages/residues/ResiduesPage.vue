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
        <div v-if="!selectedUnit">
          <div class="search-row">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            <input ref="unitSearchRef" v-model="unitSearch"
              placeholder="Пошук за назвою підрозділу..." @keydown.esc="unitSearch = ''" />
            <kbd v-if="!unitSearch" class="search-hint">/</kbd>
            <button v-if="unitSearch" class="search-clear" @click="unitSearch = ''; unitSearchRef?.focus()">×</button>
          </div>
          <div class="table-wrap">
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
              <tr v-else-if="!sorted.length"><td colspan="5" class="empty">{{ unitSearch ? 'Нічого не знайдено' : 'Немає підрозділів з залишками' }}</td></tr>
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
          <div class="t-foot" v-if="!loading">Показано <b>{{ sorted.length }}</b> з <b>{{ rows.length }}</b> підрозділів</div>
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
          <template v-else>
            <div class="search-row">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
              <input ref="unitDetailSearchRef" v-model="unitDetailSearch"
                placeholder="Пошук за № картки, назвою, серійним, категорією..." @keydown.esc="unitDetailSearch = ''" />
              <kbd v-if="!unitDetailSearch" class="search-hint">/</kbd>
              <button v-if="unitDetailSearch" class="search-clear" @click="unitDetailSearch = ''; unitDetailSearchRef?.focus()">×</button>
            </div>
            <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="sortable col-card" @click="udToggleSort('item_card_num')">№ картки <span class="sort-arrow">{{ udSortIcon('item_card_num') }}</span></th>
                  <th class="sortable col-name" @click="udToggleSort('name')">Найменування <span class="sort-arrow">{{ udSortIcon('name') }}</span></th>
                  <th class="sortable col-cat" @click="udToggleSort('category')">Категорія <span class="sort-arrow">{{ udSortIcon('category') }}</span></th>
                  <th class="sortable col-unit" @click="udToggleSort('unit_of_measure')">Од. <span class="sort-arrow">{{ udSortIcon('unit_of_measure') }}</span></th>
                  <th class="sortable col-serial" @click="udToggleSort('serial_number')">Серійний № <span class="sort-arrow">{{ udSortIcon('serial_number') }}</span></th>
                  <th class="sortable col-qty" @click="udToggleSort('qty_num')">К-сть <span class="sort-arrow">{{ udSortIcon('qty_num') }}</span></th>
                  <th class="sortable col-price" @click="udToggleSort('price_num')">Ціна <span class="sort-arrow">{{ udSortIcon('price_num') }}</span></th>
                  <th class="sortable col-amount" @click="udToggleSort('amount_num')">Сума <span class="sort-arrow">{{ udSortIcon('amount_num') }}</span></th>
                  <th class="col-hist"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!udSorted.length"><td colspan="9" class="empty">Нічого не знайдено</td></tr>
                <tr v-for="it in udSorted" :key="it.item_card_num">
                  <td class="td-mono">{{ it.item_card_num }}</td>
                  <td>{{ it.name || '—' }}</td>
                  <td>{{ it.category || '—' }}</td>
                  <td class="td-center">{{ it.unit_of_measure || '—' }}</td>
                  <td class="td-mono td-dim">{{ it.serial_number || '—' }}</td>
                  <td class="td-num">{{ fmtQty(it.qty) }}</td>
                  <td class="td-num">{{ fmtPrice(it.price) }}</td>
                  <td class="td-num">{{ fmtPrice(it.amount) }}</td>
                  <td class="td-hist">
                    <button v-if="it.item_id" class="btn-hist" @click="openHistory(it)" title="Історія">Історія</button>
                  </td>
                </tr>
              </tbody>
            </table>
            </div>
            <div class="t-foot">Показано <b>{{ udSorted.length }}</b> з <b>{{ detail.items.length }}</b> позицій</div>
          </template>
        </div>
        </template>

        <!-- ═══ TAB: По особах ═══ -->
        <template v-else>
        <!-- Master: recipients -->
        <div v-if="!selectedRecipient">
          <div class="search-row">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            <input ref="recipientSearchRef" v-model="recipientSearch"
              placeholder="Пошук за позивним..." @keydown.esc="recipientSearch = ''" />
            <kbd v-if="!recipientSearch" class="search-hint">/</kbd>
            <button v-if="recipientSearch" class="search-clear" @click="recipientSearch = ''; recipientSearchRef?.focus()">×</button>
          </div>
          <div class="table-wrap">
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
              <tr v-else-if="!rSorted.length"><td colspan="6" class="empty">{{ recipientSearch ? 'Нічого не знайдено' : 'Ні у кого немає майна' }}</td></tr>
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
          <div class="t-foot" v-if="!recipientsLoading">Показано <b>{{ rSorted.length }}</b> з <b>{{ recipientRows.length }}</b> осіб</div>
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
            <div v-if="recipientDetail?.splits?.length || recipientDetail?.serial_items?.length" class="search-row">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
              <input ref="recipientDetailSearchRef" v-model="recipientDetailSearch"
                placeholder="Пошук за № картки, назвою, серійним, категорією..." @keydown.esc="recipientDetailSearch = ''" />
              <kbd v-if="!recipientDetailSearch" class="search-hint">/</kbd>
              <button v-if="recipientDetailSearch" class="search-clear" @click="recipientDetailSearch = ''; recipientDetailSearchRef?.focus()">×</button>
            </div>

            <!-- Non-serial splits -->
            <div v-if="recipientDetail?.splits?.length" class="table-wrap">
              <div class="section-label">Видачі (розділені): <span class="section-count">{{ rdSplitsSorted.length }} з {{ recipientDetail.splits.length }}</span></div>
              <table>
                <thead>
                  <tr>
                    <th class="sortable col-card" @click="rdSplitsToggleSort('item_number')">№ картки <span class="sort-arrow">{{ rdSplitsSortIcon('item_number') }}</span></th>
                    <th class="sortable col-name" @click="rdSplitsToggleSort('item_name')">Найменування <span class="sort-arrow">{{ rdSplitsSortIcon('item_name') }}</span></th>
                    <th class="sortable col-cat" @click="rdSplitsToggleSort('category')">Категорія <span class="sort-arrow">{{ rdSplitsSortIcon('category') }}</span></th>
                    <th class="sortable col-unit" @click="rdSplitsToggleSort('unit_of_measure')">Од. <span class="sort-arrow">{{ rdSplitsSortIcon('unit_of_measure') }}</span></th>
                    <th class="sortable col-qty" @click="rdSplitsToggleSort('qty_num')">К-сть <span class="sort-arrow">{{ rdSplitsSortIcon('qty_num') }}</span></th>
                    <th class="sortable col-date" @click="rdSplitsToggleSort('issued_at')">Дата видачі <span class="sort-arrow">{{ rdSplitsSortIcon('issued_at') }}</span></th>
                    <th class="sortable col-price" @click="rdSplitsToggleSort('price_num')">Ціна <span class="sort-arrow">{{ rdSplitsSortIcon('price_num') }}</span></th>
                    <th class="sortable col-amount" @click="rdSplitsToggleSort('amount_num')">Сума <span class="sort-arrow">{{ rdSplitsSortIcon('amount_num') }}</span></th>
                    <th class="col-hist"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!rdSplitsSorted.length"><td colspan="9" class="empty">Нічого не знайдено</td></tr>
                  <tr v-for="s in rdSplitsSorted" :key="s.split_id">
                    <td class="td-mono">{{ s.item_number || '—' }}</td>
                    <td>{{ s.item_name || '—' }}</td>
                    <td>{{ s.category || '—' }}</td>
                    <td class="td-center">{{ s.unit_of_measure || '—' }}</td>
                    <td class="td-num">{{ fmtQty(s.qty) }}</td>
                    <td class="td-mono td-dim">{{ s.issued_at || '—' }}</td>
                    <td class="td-num">{{ fmtPrice(s.price) }}</td>
                    <td class="td-num">{{ fmtPrice(s.amount) }}</td>
                    <td class="td-hist">
                      <button v-if="s.item_id" class="btn-hist" @click="openHistory(s)" title="Історія">Історія</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Serial items -->
            <div v-if="recipientDetail?.serial_items?.length" class="table-wrap">
              <div class="section-label">Серійне майно (закріплено): <span class="section-count">{{ rdSerialSorted.length }} з {{ recipientDetail.serial_items.length }}</span></div>
              <table>
                <thead>
                  <tr>
                    <th class="sortable col-card" @click="rdSerialToggleSort('item_number')">№ картки <span class="sort-arrow">{{ rdSerialSortIcon('item_number') }}</span></th>
                    <th class="sortable col-name" @click="rdSerialToggleSort('item_name')">Найменування <span class="sort-arrow">{{ rdSerialSortIcon('item_name') }}</span></th>
                    <th class="sortable col-cat" @click="rdSerialToggleSort('category')">Категорія <span class="sort-arrow">{{ rdSerialSortIcon('category') }}</span></th>
                    <th class="sortable col-serial" @click="rdSerialToggleSort('serial_number')">Серійний № <span class="sort-arrow">{{ rdSerialSortIcon('serial_number') }}</span></th>
                    <th class="sortable col-unit" @click="rdSerialToggleSort('unit_of_measure')">Од. <span class="sort-arrow">{{ rdSerialSortIcon('unit_of_measure') }}</span></th>
                    <th class="sortable col-qty" @click="rdSerialToggleSort('qty_num')">К-сть <span class="sort-arrow">{{ rdSerialSortIcon('qty_num') }}</span></th>
                    <th class="sortable col-price" @click="rdSerialToggleSort('price_num')">Ціна <span class="sort-arrow">{{ rdSerialSortIcon('price_num') }}</span></th>
                    <th class="sortable col-amount" @click="rdSerialToggleSort('amount_num')">Сума <span class="sort-arrow">{{ rdSerialSortIcon('amount_num') }}</span></th>
                    <th class="col-hist"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!rdSerialSorted.length"><td colspan="9" class="empty">Нічого не знайдено</td></tr>
                  <tr v-for="it in rdSerialSorted" :key="it.item_id">
                    <td class="td-mono">{{ it.item_number }}</td>
                    <td>{{ it.item_name || '—' }}</td>
                    <td>{{ it.category || '—' }}</td>
                    <td class="td-mono">{{ it.serial_number || '—' }}</td>
                    <td class="td-center">{{ it.unit_of_measure || '—' }}</td>
                    <td class="td-num">{{ fmtQty(it.qty) }}</td>
                    <td class="td-num">{{ fmtPrice(it.price) }}</td>
                    <td class="td-num">{{ fmtPrice(it.amount) }}</td>
                    <td class="td-hist">
                      <button class="btn-hist" @click="openHistory(it)" title="Історія">Історія</button>
                    </td>
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

    <ItemHistoryModal :item-id="historyItemId" :item-title="historyItemTitle" @close="closeHistory" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import ItemHistoryModal from '../../components/ItemHistoryModal.vue'
import {
  getResiduesByUnit, getResiduesByUnitDetail,
  getResiduesByRecipient, getResiduesByRecipientDetail,
} from '../../api/residues.js'
import { useSort } from '../../composables/useSort.js'
import { useAuthStore } from '../../stores/auth.js'

const auth = useAuthStore()

const activeTab = ref('unit')

// History modal state — surfaced from either detail table
const historyItemId = ref(null)
const historyItemTitle = ref('')
function openHistory(row) {
  const id = row.item_id ?? row.item_id_
  if (!id) return
  historyItemId.value = id
  historyItemTitle.value = row.name || row.item_name || row.item_card_num || row.item_number || ''
}
function closeHistory() {
  historyItemId.value = null
  historyItemTitle.value = ''
}

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

// Search state — separate per view so context is preserved on navigation
const unitSearch = ref('')
const recipientSearch = ref('')
const unitDetailSearch = ref('')
const recipientDetailSearch = ref('')
const unitSearchRef = ref(null)
const recipientSearchRef = ref(null)
const unitDetailSearchRef = ref(null)
const recipientDetailSearchRef = ref(null)

function matches(row, q, fields) {
  if (!q) return true
  const s = q.toLowerCase()
  return fields.some(f => String(row[f] ?? '').toLowerCase().includes(s))
}

// Master «По підрозділах» — filter + enrich for sort
const enriched = computed(() => rows.value
  .filter(r => matches(r, unitSearch.value.trim(), ['unit']))
  .map(r => ({
    ...r,
    total_qty_num: Number(r.total_qty || 0),
    total_amount_num: Number(r.total_amount || 0),
  })))
const { sorted, toggleSort, sortIcon } = useSort(enriched, 'unit', 'asc')

// Master «По особах»
const rEnriched = computed(() => recipientRows.value
  .filter(r => matches(r, recipientSearch.value.trim(), ['callsign']))
  .map(r => ({
    ...r,
    total_qty_num: Number(r.total_qty || 0),
    total_amount_num: Number(r.total_amount || 0),
  })))
const { sorted: rSorted, toggleSort: rToggleSort, sortIcon: rSortIcon } = useSort(rEnriched, 'callsign', 'asc')

// Detail «Майно в підрозділі»
const DETAIL_ITEM_FIELDS = ['item_card_num', 'name', 'serial_number', 'category']
const udEnriched = computed(() => (detail.value?.items || [])
  .filter(r => matches(r, unitDetailSearch.value.trim(), DETAIL_ITEM_FIELDS))
  .map(r => ({
    ...r,
    qty_num: Number(r.qty || 0),
    price_num: Number(r.price || 0),
    amount_num: Number(r.amount || 0),
  })))
const { sorted: udSorted, toggleSort: udToggleSort, sortIcon: udSortIcon } = useSort(udEnriched, 'item_card_num', 'asc')

// Detail «Майно у особи» — splits
const RD_SPLIT_FIELDS = ['item_number', 'item_name', 'category']
const rdSplitsEnriched = computed(() => (recipientDetail.value?.splits || [])
  .filter(r => matches(r, recipientDetailSearch.value.trim(), RD_SPLIT_FIELDS))
  .map(r => ({
    ...r,
    qty_num: Number(r.qty || 0),
    price_num: Number(r.price || 0),
    amount_num: Number(r.amount || 0),
  })))
const { sorted: rdSplitsSorted, toggleSort: rdSplitsToggleSort, sortIcon: rdSplitsSortIcon } = useSort(rdSplitsEnriched, 'item_number', 'asc')

// Detail «Майно у особи» — серійне
const RD_SERIAL_FIELDS = ['item_number', 'item_name', 'serial_number', 'category']
const rdSerialEnriched = computed(() => (recipientDetail.value?.serial_items || [])
  .filter(r => matches(r, recipientDetailSearch.value.trim(), RD_SERIAL_FIELDS))
  .map(r => ({
    ...r,
    qty_num: Number(r.qty || 0),
    price_num: Number(r.price || 0),
    amount_num: Number(r.amount || 0),
  })))
const { sorted: rdSerialSorted, toggleSort: rdSerialToggleSort, sortIcon: rdSerialSortIcon } = useSort(rdSerialEnriched, 'item_number', 'asc')

// «/» hotkey — focuses the currently visible search input
function currentSearchRef() {
  if (activeTab.value === 'unit') {
    return selectedUnit.value ? unitDetailSearchRef.value : unitSearchRef.value
  }
  return selectedRecipient.value ? recipientDetailSearchRef.value : recipientSearchRef.value
}
function onKeyDown(e) {
  const tag = document.activeElement?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.key === '/' || e.key === '.') {
    e.preventDefault()
    currentSearchRef()?.focus()
  }
}

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
  recipientDetailSearch.value = ''
  recipientDetailLoading.value = true
  try {
    const { data } = await getResiduesByRecipientDetail(r.recipient_id)
    recipientDetail.value = data
  } finally { recipientDetailLoading.value = false }
}
function closeRecipient() {
  selectedRecipient.value = null
  recipientDetail.value = null
  recipientDetailSearch.value = ''
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
onMounted(() => {
  bootstrap()
  document.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

async function openUnit(u) {
  selectedUnit.value = u.unit
  detail.value = null
  unitDetailSearch.value = ''
  detailLoading.value = true
  try {
    const { data } = await getResiduesByUnitDetail(u.unit)
    detail.value = data
  } finally { detailLoading.value = false }
}

function closeUnit() {
  selectedUnit.value = null
  detail.value = null
  unitDetailSearch.value = ''
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
.section-count { font-weight:500; color:var(--text-mid); text-transform:none; letter-spacing:0; margin-left:6px; }

.search-row { padding:10px 20px; display:flex; align-items:center; gap:8px; border-bottom:1px solid var(--border-light); background:var(--surface); }
.search-icon { width:14px; height:14px; color:var(--text-light); flex-shrink:0; }
.search-row input { flex:1; border:none; background:transparent; font-family:inherit; font-size:14px; color:var(--text); outline:none; }
.search-row input::placeholder { color:var(--text-light); }
.search-hint { font-family:'DM Mono',monospace; font-size:11px; color:var(--text-light); background:var(--border-light); border:1px solid var(--border); border-radius:3px; padding:1px 5px; line-height:16px; flex-shrink:0; }
.search-clear { width:22px; height:22px; border:none; background:transparent; cursor:pointer; color:var(--text-light); border-radius:3px; flex-shrink:0; font-size:16px; line-height:1; }
.search-clear:hover { background:var(--border-light); color:var(--text); }

.t-foot { padding:10px 20px; font-size:12px; color:var(--text-light); border-top:1px solid var(--border-light); background:var(--bg); }
.t-foot b { color:var(--text-mid); font-weight:600; }

.col-hist { width:90px; }
.td-hist  { text-align:center; }
.btn-hist { background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); padding:3px 10px; cursor:pointer; color:var(--text-mid); font-size:12px; font-family:inherit; }
.btn-hist:hover { background:var(--bg); color:var(--text); border-color:var(--accent); }
</style>
