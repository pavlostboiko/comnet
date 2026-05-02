<template>
  <div class="page-wrap">
    <TopBar>
      <template #actions>
        <button class="btn-primary" @click="openForm(null)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Додати
        </button>
      </template>
    </TopBar>

    <div class="content-scroll">
      <div class="tile">
        <!-- Header -->
        <div class="tile-header">
          <span class="tile-title">Довідник майна</span>
          <span class="tile-count">{{ items.length }}</span>
          <div class="tile-tabs">
            <button class="tt-btn" :class="{ on: activeTab === 'all' }" @click="activeTab='all'">
              Всі <span class="c">{{ tabCounts.all }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'serial' }" @click="activeTab='serial'">
              Серійні <span class="c">{{ tabCounts.serial }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'nonserial' }" @click="activeTab='nonserial'">
              Несерійні <span class="c">{{ tabCounts.nonserial }}</span>
            </button>
          </div>
        </div>

        <!-- Search row -->
        <div class="search-row">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            style="color:var(--text-light);flex-shrink:0"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input ref="searchInputRef" v-model="search"
            placeholder="Пошук за назвою, №, серійним номером..."
            @keydown.esc="search = ''" />
          <kbd v-if="!search" class="search-hint">/</kbd>
          <button v-if="search" class="search-clear" @click="search = ''; searchInputRef.focus()">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <!-- Type filter chips -->
        <div class="sub-row" v-if="itemTypes.length">
          <span class="sub-row-label">Тип</span>
          <div class="sub-chips">
            <span v-for="t in itemTypes" :key="t" class="sub-chip"
              :class="{ on: selectedType === t }" @click="toggleType(t)">{{ t }}</span>
          </div>
          <span class="sub-clear" v-if="selectedType" @click="selectedType=null">× Скинути</span>
        </div>

        <!-- Table -->
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width:70px">№ картки</th>
                <th>Найменування</th>
                <th style="width:150px">Тип</th>
                <th style="width:130px">Серійний №</th>
                <th style="width:80px">Категорія</th>
                <th style="width:50px;text-align:center">Од.</th>
                <th style="width:80px;text-align:right">К-сть</th>
                <th style="width:120px;text-align:right">Вартість, грн</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="9" style="text-align:center;padding:32px;color:var(--text-light)">Завантаження…</td>
              </tr>
              <tr v-else-if="!filteredItems.length">
                <td colspan="9" style="text-align:center;padding:32px;color:var(--text-light)">Нічого не знайдено</td>
              </tr>
              <tr v-for="item in filteredItems" :key="item.id" @click="openCard(item)">
                <td><span class="td-num-badge">{{ item.number }}</span></td>
                <td>
                  <span class="td-name">{{ item.name }}</span>
                  <span v-if="!item.is_official" class="unoffic-badge">волонтерське</span>
                </td>
                <td><span v-if="item.item_type" class="type-chip">{{ item.item_type }}</span></td>
                <td>
                  <span v-if="item.serial_number" class="td-serial">{{ item.serial_number }}</span>
                  <span v-else class="td-serial none">несерійне</span>
                </td>
                <td>
                  <span v-if="item.category" class="cat-badge" :class="catClass(item.category)">
                    {{ item.category }}
                  </span>
                </td>
                <td style="text-align:center">{{ item.unit_of_measure || '—' }}</td>
                <td class="td-num-val" :class="{ 'td-qty-large': true }">{{ fmtQty(item.quantity) }}</td>
                <td class="td-num-val">{{ fmtPrice(item.price) }}</td>
                <td @click.stop>
                  <div class="acts">
                    <button class="act e" title="Редагувати" @click="openFormFromList(item)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                        <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button class="act d" title="Видалити" @click="confirmDelete(item)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="t-foot">
          Показано <b>{{ filteredItems.length }}</b> з <b>{{ items.length }}</b> позицій
        </div>
      </div>
    </div>

    <!-- ═══════════ CARD OVERLAY ═══════════ -->
    <div class="overlay" :class="{ open: cardVisible }" @click.self="cardVisible=false">
      <div class="card-modal" v-if="cardItem">
        <div class="card-head">
          <div class="card-head-info">
            <div class="card-head-num">{{ cardItem.number }}</div>
            <div class="card-head-name">{{ cardItem.name }}</div>
            <div class="card-head-badges">
              <span v-if="cardItem.item_type" class="type-chip">{{ cardItem.item_type }}</span>
              <span v-if="cardItem.category" class="cat-badge" :class="catClass(cardItem.category)">
                {{ cardItem.category }}
              </span>
              <span v-if="!cardItem.is_official" class="unoffic-badge">волонтерське</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-edit-card" @click="openForm(cardItem); cardVisible=false">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
              Редагувати
            </button>
            <button class="modal-close" @click="cardVisible=false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
        <div class="card-body">
          <div>
            <div class="card-section-title">Характеристики</div>
            <div class="card-fields">
              <div class="card-field">
                <div class="card-field-label">Код номенклатури</div>
                <div class="card-field-value mono">{{ cardItem.nomenclature_code || '—' }}</div>
              </div>
              <div class="card-field">
                <div class="card-field-label">Одиниця виміру</div>
                <div class="card-field-value">{{ cardItem.unit_of_measure || '—' }}</div>
              </div>
              <div class="card-field">
                <div class="card-field-label">Кількість</div>
                <div class="card-field-value mono">{{ fmtQty(cardItem.quantity) }}</div>
              </div>
              <div class="card-field">
                <div class="card-field-label">Вартість</div>
                <div class="card-field-value mono">{{ fmtPrice(cardItem.price) }} грн</div>
              </div>
              <div class="card-field">
                <div class="card-field-label">Серійний №</div>
                <div class="card-field-value mono" :class="{ dim: !cardItem.serial_number }">
                  {{ cardItem.serial_number || 'несерійне' }}
                </div>
              </div>
              <div class="card-field">
                <div class="card-field-label">Batch (партія)</div>
                <div class="card-field-value mono" :class="{ dim: !cardItem.batch_id }">
                  {{ cardItem.batch_id || '—' }}
                </div>
              </div>
            </div>
          </div>
          <div v-if="cardItem.notes">
            <hr class="card-divider">
            <div class="card-section-title">Примітки</div>
            <p style="font-size:14px;color:var(--text-mid);line-height:1.5">{{ cardItem.notes }}</p>
          </div>
          <div>
            <hr class="card-divider">
            <div class="card-section-title">Прикріплені документи</div>
            <div v-if="cardItem.documents.length" class="doc-list">
              <div v-for="d in cardItem.documents" :key="d.id" class="doc-card">
                <div class="doc-card-type">{{ DOC_TYPE_LABELS[d.doc_type] || d.doc_type }}</div>
                <div class="doc-card-num">{{ d.doc_number || '—' }}</div>
                <div class="doc-card-date">{{ d.doc_date || '' }}</div>
              </div>
            </div>
            <div v-else class="doc-empty">Документи не прикріплено</div>
          </div>
        </div>
      </div>
      <div v-else-if="cardVisible" style="color:white;font-size:14px">Завантаження…</div>
    </div>

    <!-- ═══════════ FORM OVERLAY ═══════════ -->
    <div class="overlay" :class="{ open: formVisible }" @click.self="formVisible=false">
      <div class="form-modal">
        <div class="modal-head">
          <span class="modal-title">{{ formMode === 'add' ? 'Додати позицію' : 'Редагувати позицію' }}</span>
          <button class="modal-close" @click="formVisible=false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="modal-body">

          <!-- Тип обліку -->
          <div>
            <div class="form-section-title">Тип обліку</div>
            <div class="serial-toggle">
              <button class="serial-opt" :class="{ on: isSerial }" @click="setSerial(true)">Серійне майно</button>
              <button class="serial-opt" :class="{ on: !isSerial }" @click="setSerial(false)">Несерійне майно</button>
            </div>
          </div>

          <!-- Основна інформація -->
          <div>
            <div class="form-section-title">Основна інформація</div>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">№ картки *</label>
                <input class="form-input" v-model="f.number" placeholder="0001">
              </div>
              <div class="form-group">
                <label class="form-label">Тип майна</label>
                <input class="form-input" v-model="f.item_type" placeholder="Засоби зв'язку" list="types-list">
                <datalist id="types-list">
                  <option v-for="t in itemTypes" :key="t" :value="t"/>
                  <option value="Засоби зв'язку"/>
                  <option value="Комп'ютерна техніка"/>
                  <option value="Оптика"/>
                  <option value="Спорядження"/>
                  <option value="Захист"/>
                  <option value="Медичне"/>
                  <option value="Озброєння"/>
                  <option value="Техніка та обладнання"/>
                </datalist>
              </div>
              <div class="form-group full">
                <label class="form-label">Найменування *</label>
                <input class="form-input" v-model="f.name" placeholder="Радіостанція Р-187-П1">
              </div>
              <div class="form-group">
                <label class="form-label">Категорія</label>
                <select class="form-select" v-model="f.category">
                  <option value="">— оберіть —</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                  <option value="5">5</option>
                  <option value="пр.">придатний (пр.)</option>
                  <option value="непр.">непридатний (непр.)</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Код номенклатури</label>
                <input class="form-input" v-model="f.nomenclature_code" placeholder="26.30.11-00.01">
              </div>
              <div class="form-group">
                <label class="form-label">Одиниця виміру</label>
                <input class="form-input" v-model="f.unit_of_measure" placeholder="шт">
              </div>
              <div class="form-group">
                <label class="form-label">{{ isSerial ? 'Кількість (авто = 1)' : 'Кількість' }}</label>
                <input class="form-input" v-model="f.quantity" type="number" step="0.0001"
                  placeholder="1" :disabled="isSerial">
              </div>
              <div class="form-group">
                <label class="form-label">Вартість, грн</label>
                <input class="form-input" v-model="f.price" type="number" step="0.01" placeholder="0.00">
              </div>
              <div class="form-group" v-if="isSerial">
                <label class="form-label">Серійний номер</label>
                <input class="form-input" v-model="f.serial_number" placeholder="SN-ABC-001">
              </div>
              <div class="form-group">
                <label class="form-label">Batch (партія надходження)</label>
                <input class="form-input" v-model="f.batch_id" placeholder="НКЛ-001/25">
              </div>
              <div class="form-group full">
                <label class="form-label">Примітки</label>
                <input class="form-input" v-model="f.notes" placeholder="Додаткова інформація">
              </div>
              <div class="form-group full">
                <label class="form-label official-wrap">
                  <input type="checkbox" v-model="f.is_official" class="form-checkbox">
                  Офіційне майно (на балансі)
                </label>
              </div>
            </div>
          </div>

          <!-- Документи -->
          <div>
            <div class="form-section-title">Прикріплені документи</div>
            <div class="doc-form-list">
              <div v-for="(doc, idx) in docRows" :key="idx" class="doc-form-row">
                <select class="form-select" v-model="doc.doc_type">
                  <option value="">— тип —</option>
                  <option value="акт_техн_стану">Акт техн. стану</option>
                  <option value="акт_введення">Акт введення в експл.</option>
                  <option value="акт_прийому">Акт прийому-передачі</option>
                  <option value="акт_прийому_благ">Акт прийому благ</option>
                  <option value="накладна">Накладна</option>
                </select>
                <input class="form-input" v-model="doc.doc_number" placeholder="№ документа">
                <input class="form-input" v-model="doc.doc_date" placeholder="дд.мм.рррр">
                <button class="btn-remove-doc" @click="docRows.splice(idx,1)" title="Видалити">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
            <button class="btn-add-doc" @click="docRows.push({doc_type:'',doc_number:'',doc_date:''})">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              Додати документ
            </button>
          </div>
        </div>

        <div class="modal-foot">
          <button class="btn-cancel" @click="formVisible=false">Скасувати</button>
          <button class="btn-submit" :disabled="saving" @click="submitForm">
            {{ saving ? 'Збереження…' : 'Зберегти' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div class="toast" :class="{ show: toastVisible }">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { createItem, deleteItem as apiDelete, getItem, getItems, updateItem } from '../../api/items.js'

const DOC_TYPE_LABELS = {
  акт_техн_стану:  'Акт техн. стану',
  акт_введення:    'Акт введення в експл.',
  акт_прийому:     'Акт прийому-передачі',
  акт_прийому_благ:'Акт прийому благ',
  накладна:        'Накладна',
}

// ── State ──────────────────────────────────────────────────────
const items        = ref([])
const loading      = ref(false)
const search       = ref('')
const searchInputRef = ref(null)
const activeTab    = ref('all')
const selectedType = ref(null)

// Card
const cardVisible = ref(false)
const cardItem    = ref(null)

// Form
const formVisible = ref(false)
const formMode    = ref('add')
const editItemId  = ref(null)
const isSerial    = ref(true)
const saving      = ref(false)
const f = reactive({
  number: '', name: '', item_type: '', category: '',
  nomenclature_code: '', unit_of_measure: '',
  quantity: '', price: '', serial_number: '', batch_id: '', notes: '',
  is_official: true,
})
const docRows = ref([])

// Toast
const toastMsg     = ref('')
const toastVisible = ref(false)
let toastTimer

// ── Computed ───────────────────────────────────────────────────
const tabCounts = computed(() => ({
  all:       items.value.length,
  serial:    items.value.filter(i => i.serial_number).length,
  nonserial: items.value.filter(i => !i.serial_number).length,
}))

const itemTypes = computed(() => {
  const s = new Set(items.value.map(i => i.item_type).filter(Boolean))
  return [...s].sort()
})

const filteredItems = computed(() => {
  let list = items.value
  if (activeTab.value === 'serial')    list = list.filter(i => i.serial_number)
  if (activeTab.value === 'nonserial') list = list.filter(i => !i.serial_number)
  if (selectedType.value)              list = list.filter(i => i.item_type === selectedType.value)
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(i =>
      i.name?.toLowerCase().includes(q) ||
      i.number?.toLowerCase().includes(q) ||
      i.serial_number?.toLowerCase().includes(q)
    )
  }
  return list
})

// ── Helpers ────────────────────────────────────────────────────
function catClass(cat) {
  return { '1':'cat-1','2':'cat-2','3':'cat-3','4':'cat-4','5':'cat-5',
           'пр.':'cat-pr','непр.':'cat-npr' }[cat] || ''
}

function fmtQty(v) {
  if (v == null) return '—'
  const n = parseFloat(v)
  return n % 1 === 0 ? n.toFixed(0) : n.toString()
}

function fmtPrice(v) {
  if (v == null) return '—'
  return parseFloat(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function showToast(msg) {
  toastMsg.value = msg
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2400)
}

function toggleType(t) {
  selectedType.value = selectedType.value === t ? null : t
}

function setSerial(val) {
  isSerial.value = val
  if (val) f.quantity = '1'
}

// ── Data ───────────────────────────────────────────────────────
async function fetchItems() {
  loading.value = true
  try { items.value = await getItems() }
  finally { loading.value = false }
}

// ── Card ───────────────────────────────────────────────────────
async function openCard(item) {
  cardItem.value = null
  cardVisible.value = true
  cardItem.value = await getItem(item.id)
}

// ── Form ───────────────────────────────────────────────────────
function populateForm(item) {
  formMode.value  = item ? 'edit' : 'add'
  editItemId.value = item?.id ?? null
  isSerial.value  = item ? !!item.serial_number : true

  f.number           = item?.number ?? ''
  f.name             = item?.name ?? ''
  f.item_type        = item?.item_type ?? ''
  f.category         = item?.category ?? ''
  f.nomenclature_code = item?.nomenclature_code ?? ''
  f.unit_of_measure  = item?.unit_of_measure ?? ''
  f.quantity         = item?.quantity != null ? String(parseFloat(item.quantity)) : (isSerial.value ? '1' : '')
  f.price            = item?.price != null ? String(parseFloat(item.price)) : ''
  f.serial_number    = item?.serial_number ?? ''
  f.batch_id         = item?.batch_id ?? ''
  f.notes            = item?.notes ?? ''
  f.is_official      = item?.is_official ?? true

  docRows.value = item?.documents?.map(d => ({
    doc_type: d.doc_type ?? '',
    doc_number: d.doc_number ?? '',
    doc_date: d.doc_date ?? '',
  })) ?? []
}

function openForm(item) {
  populateForm(item)
  formVisible.value = true
}

async function openFormFromList(item) {
  const full = await getItem(item.id)
  openForm(full)
}

async function submitForm() {
  if (!f.number.trim() || !f.name.trim()) {
    showToast('Заповніть № картки та найменування')
    return
  }
  saving.value = true
  try {
    const payload = {
      number:           f.number.trim(),
      name:             f.name.trim(),
      category:         f.category || null,
      nomenclature_code: f.nomenclature_code || null,
      serial_number:    isSerial.value ? (f.serial_number || null) : null,
      unit_of_measure:  f.unit_of_measure || null,
      quantity:         isSerial.value ? 1 : (parseFloat(f.quantity) || null),
      price:            parseFloat(f.price) || null,
      item_type:        f.item_type || null,
      batch_id:         f.batch_id || null,
      notes:            f.notes || null,
      is_official:      f.is_official,
      documents:        docRows.value.filter(d => d.doc_type || d.doc_number),
    }
    if (formMode.value === 'add') {
      await createItem(payload)
      showToast('Позицію додано')
    } else {
      await updateItem(editItemId.value, payload)
      showToast('Позицію оновлено')
    }
    formVisible.value = false
    await fetchItems()
  } catch (err) {
    const msg = err.response?.data?.detail
    showToast(msg === 'Item number already exists' ? '№ картки вже існує' : 'Помилка збереження')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(item) {
  if (!confirm(`Видалити «${item.name}»?`)) return
  await apiDelete(item.id)
  showToast('Позицію видалено')
  await fetchItems()
}

// ── Keyboard shortcut ──────────────────────────────────────────
function onKeyDown(e) {
  const tag = document.activeElement?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.key === '/' || e.key === '.') {
    e.preventDefault()
    searchInputRef.value?.focus()
  }
}

// ── Init ───────────────────────────────────────────────────────
onMounted(() => {
  fetchItems()
  document.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.content-scroll::-webkit-scrollbar { width:6px; }
.content-scroll::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

/* Topbar slot */
.btn-primary { display:flex; align-items:center; gap:5px; padding:8px 14px; background:var(--accent); border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:600; color:white; cursor:pointer; transition:all 0.15s; white-space:nowrap; }
.btn-primary:hover { background:var(--accent-dark); }

/* Search row */
.search-row { padding:10px 20px; display:flex; align-items:center; gap:8px; border-bottom:1px solid var(--border-light); background:var(--surface); }
.search-row input { flex:1; border:none; background:transparent; font-family:inherit; font-size:14px; color:var(--text); outline:none; }
.search-row input::placeholder { color:var(--text-light); }
.search-hint { font-family:'DM Mono',monospace; font-size:11px; color:var(--text-light); background:var(--border-light); border:1px solid var(--border); border-radius:3px; padding:1px 5px; line-height:16px; flex-shrink:0; }
.search-clear { width:20px; height:20px; border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; border-radius:3px; flex-shrink:0; }
.search-clear:hover { background:var(--border-light); color:var(--text); }

/* Tile */
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden; }
.tile-header { padding:12px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); flex-wrap:wrap; }
.tile-title { font-size:15px; font-weight:700; }
.tile-count { font-family:'DM Mono',monospace; font-size:11.5px; font-weight:500; background:var(--accent-light); color:var(--accent); padding:2px 8px; border-radius:var(--radius-sm); }
.tile-tabs { display:flex; gap:2px; background:var(--bg); padding:3px; border-radius:var(--radius-sm); border:1px solid var(--border-light); margin-left:auto; }
.tt-btn { padding:5px 13px; border:none; background:transparent; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; transition:all 0.12s; display:flex; align-items:center; gap:6px; }
.tt-btn:hover { color:var(--text-mid); }
.tt-btn.on { background:var(--surface); color:var(--text); box-shadow:0 1px 2px rgba(0,0,0,0.06); font-weight:600; }
.tt-btn .c { font-family:'DM Mono',monospace; font-size:10.5px; color:var(--text-light); background:var(--border-light); padding:0 6px; border-radius:var(--radius-sm); line-height:17px; min-width:20px; text-align:center; }
.tt-btn.on .c { background:var(--accent-light); color:var(--accent); }

/* Chips */
.sub-row { padding:9px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); background:var(--bg); flex-wrap:wrap; }
.sub-row-label { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-light); flex-shrink:0; }
.sub-chips { display:flex; gap:6px; flex-wrap:wrap; }
.sub-chip { padding:4px 11px; border:1px solid var(--border); background:var(--surface); border-radius:var(--radius-pill); font-size:12.5px; font-weight:500; color:var(--text-mid); cursor:pointer; transition:all 0.12s; }
.sub-chip:hover { border-color:var(--text-light); color:var(--text); }
.sub-chip.on { background:var(--accent); border-color:var(--accent); color:white; font-weight:600; }
.sub-clear { margin-left:auto; font-size:12px; color:var(--text-light); cursor:pointer; padding:3px 8px; border-radius:var(--radius-sm); }
.sub-clear:hover { color:var(--text); background:var(--border-light); }

/* Table */
.table-wrap { overflow-x:auto; }
.table-wrap::-webkit-scrollbar { height:6px; }
.table-wrap::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
table { width:100%; border-collapse:collapse; min-width:900px; }
thead tr { background:var(--bg); }
th { padding:9px 12px; text-align:left; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); border-bottom:1px solid var(--border); white-space:nowrap; }
th:first-child { padding-left:20px; }
th:last-child { padding-right:20px; width:52px; }
tbody tr { border-bottom:1px solid var(--border-light); transition:background 0.1s; cursor:pointer; }
tbody tr:last-child { border-bottom:none; }
tbody tr:nth-child(even) { background:#f8fafc; }
tbody tr:hover { background:var(--row-hover) !important; }
td { padding:10px 12px; font-size:14px; color:var(--text-mid); vertical-align:middle; white-space:nowrap; }
td:first-child { padding-left:20px; }
td:last-child { padding-right:20px; }
.td-num-badge { font-family:'DM Mono',monospace; font-size:11px; font-weight:600; color:var(--accent); background:var(--accent-light); padding:2px 8px; border-radius:var(--radius-sm); display:inline-block; }
.td-name { font-weight:600; color:var(--text); }
.td-serial { font-family:'DM Mono',monospace; font-size:12.5px; }
.td-serial.none { color:var(--text-light); font-style:italic; font-family:inherit; }
.td-num-val { font-family:'DM Mono',monospace; font-size:12.5px; text-align:right; }
.td-qty-large { color:var(--text); font-weight:600; }
.unoffic-badge { display:inline-block; margin-left:6px; padding:1px 6px; border-radius:var(--radius-sm); font-size:11px; font-weight:600; background:#fef9c3; color:#a16207; }

/* Category badges */
.cat-badge { display:inline-block; padding:2px 8px; border-radius:var(--radius-sm); font-size:11.5px; font-weight:600; font-family:'DM Mono',monospace; }
.cat-1 { background:#eff6ff; color:#2563eb; }
.cat-2 { background:#ecfdf5; color:#059669; }
.cat-3 { background:#fef9c3; color:#a16207; }
.cat-4 { background:#fff7ed; color:#c2410c; }
.cat-5 { background:#fef2f2; color:#b91c1c; }
.cat-pr  { background:#f0fdf4; color:#16a34a; }
.cat-npr { background:#fef2f2; color:#dc2626; }

/* Type chip */
.type-chip { display:inline-block; padding:2px 9px; border-radius:var(--radius-pill); font-size:12px; font-weight:500; background:var(--border-light); color:var(--text-mid); white-space:nowrap; }

/* Row actions */
.acts { display:flex; gap:2px; opacity:0; transition:opacity 0.12s; justify-content:flex-end; }
tbody tr:hover .acts { opacity:1; }
.act { width:28px; height:28px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; transition:all 0.12s; }
.act svg { width:14px; height:14px; }
.act.e:hover { background:var(--accent-light); color:var(--accent); }
.act.d:hover { background:var(--red-bg); color:var(--red); }

/* Footer */
.t-foot { padding:10px 20px; border-top:1px solid var(--border-light); font-size:13px; color:var(--text-light); background:var(--bg); }
.t-foot b { color:var(--text); font-weight:600; }

/* Overlay */
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.4); backdrop-filter:blur(2px); z-index:100; display:flex; align-items:center; justify-content:center; opacity:0; pointer-events:none; transition:opacity 0.2s; }
.overlay.open { opacity:1; pointer-events:all; }

/* Card modal */
.card-modal { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow-xl); width:740px; max-width:calc(100vw - 48px); max-height:calc(100vh - 60px); overflow-y:auto; transform:translateY(12px) scale(0.98); transition:transform 0.2s; display:flex; flex-direction:column; }
.overlay.open .card-modal { transform:translateY(0) scale(1); }
.card-head { padding:20px 24px 16px; border-bottom:1px solid var(--border-light); display:flex; align-items:flex-start; gap:12px; position:sticky; top:0; background:var(--surface); z-index:1; }
.card-head-info { flex:1; min-width:0; }
.card-head-num { font-family:'DM Mono',monospace; font-size:11px; font-weight:600; color:var(--accent); background:var(--accent-light); padding:2px 8px; border-radius:var(--radius-sm); display:inline-block; margin-bottom:6px; }
.card-head-name { font-size:18px; font-weight:700; color:var(--text); line-height:1.2; margin-bottom:8px; }
.card-head-badges { display:flex; gap:6px; flex-wrap:wrap; }
.card-actions { display:flex; align-items:center; gap:6px; flex-shrink:0; }
.btn-edit-card { display:flex; align-items:center; gap:5px; padding:7px 12px; background:var(--accent-light); border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:12.5px; font-weight:600; color:var(--accent); cursor:pointer; transition:all 0.12s; }
.btn-edit-card:hover { background:var(--accent); color:white; }
.modal-close { width:30px; height:30px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; transition:all 0.12s; }
.modal-close:hover { background:var(--bg); color:var(--text); }
.card-body { padding:20px 24px; display:flex; flex-direction:column; gap:20px; }
.card-section-title { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); margin-bottom:10px; }
.card-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px 20px; }
.card-field { display:flex; flex-direction:column; gap:3px; }
.card-field-label { font-size:11px; font-weight:600; color:var(--text-light); text-transform:uppercase; letter-spacing:0.04em; }
.card-field-value { font-size:14px; color:var(--text); font-weight:500; }
.card-field-value.mono { font-family:'DM Mono',monospace; font-size:13px; }
.card-field-value.dim { color:var(--text-light); font-style:italic; }
.card-divider { border:none; border-top:1px solid var(--border-light); }
.doc-list { display:flex; flex-wrap:wrap; gap:8px; }
.doc-card { padding:10px 14px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); min-width:160px; }
.doc-card-type { font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); margin-bottom:4px; }
.doc-card-num { font-family:'DM Mono',monospace; font-size:13px; font-weight:600; color:var(--text); }
.doc-card-date { font-size:12px; color:var(--text-light); margin-top:2px; }
.doc-empty { font-size:13px; color:var(--text-light); font-style:italic; padding:8px 0; }

/* Form modal */
.form-modal { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow-xl); width:660px; max-width:calc(100vw - 48px); max-height:calc(100vh - 60px); overflow-y:auto; transform:translateY(12px) scale(0.98); transition:transform 0.2s; }
.overlay.open .form-modal { transform:translateY(0) scale(1); }
.modal-head { padding:20px 24px 16px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; background:var(--surface); z-index:1; }
.modal-title { font-size:17px; font-weight:700; }
.modal-body { padding:20px 24px; display:flex; flex-direction:column; gap:20px; }
.modal-foot { padding:16px 24px; border-top:1px solid var(--border-light); display:flex; justify-content:flex-end; gap:8px; position:sticky; bottom:0; background:var(--surface); }
.form-section-title { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); margin-bottom:10px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px 16px; }
.form-group { display:flex; flex-direction:column; gap:5px; }
.form-group.full { grid-column:span 2; }
.form-label { font-size:12px; font-weight:600; color:var(--text-mid); }
.form-input { padding:9px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; color:var(--text); background:var(--bg); outline:none; transition:all 0.15s; }
.form-input:focus { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); background:var(--surface); }
.form-input::placeholder { color:var(--text-light); }
.form-input:disabled { opacity:0.5; cursor:not-allowed; }
.form-select { padding:9px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; color:var(--text); background:var(--bg); outline:none; cursor:pointer; transition:all 0.15s; appearance:none; background-image:url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2394a3b8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 10px center; padding-right:28px; }
.form-select:focus { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); }
.form-checkbox { width:14px; height:14px; accent-color:var(--accent); margin-right:6px; cursor:pointer; }
.official-wrap { display:flex; align-items:center; font-size:13.5px; font-weight:500; color:var(--text-mid); cursor:pointer; }
.serial-toggle { display:flex; border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; }
.serial-opt { flex:1; padding:8px 12px; border:none; background:transparent; font-family:inherit; font-size:13px; font-weight:500; color:var(--text-mid); cursor:pointer; transition:all 0.12s; }
.serial-opt.on { background:var(--accent); color:white; font-weight:600; }
.serial-opt:not(.on):hover { background:var(--bg); }
.doc-form-list { display:flex; flex-direction:column; gap:8px; }
.doc-form-row { display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:8px; align-items:center; }
.btn-add-doc { display:flex; align-items:center; gap:5px; padding:7px 12px; border:1px dashed var(--border); border-radius:var(--radius-sm); background:transparent; font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; transition:all 0.12s; margin-top:4px; }
.btn-add-doc:hover { border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }
.btn-remove-doc { width:26px; height:26px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; }
.btn-remove-doc:hover { background:var(--red-bg); color:var(--red); }
.btn-cancel { padding:9px 16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:500; color:var(--text-mid); cursor:pointer; transition:all 0.12s; }
.btn-cancel:hover { border-color:var(--text-light); color:var(--text); }
.btn-submit { padding:9px 20px; background:var(--accent); border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:600; color:white; cursor:pointer; transition:all 0.15s; }
.btn-submit:hover:not(:disabled) { background:var(--accent-dark); }
.btn-submit:disabled { opacity:0.6; cursor:not-allowed; }

/* Toast */
.toast { position:fixed; bottom:20px; left:50%; transform:translateX(-50%) translateY(80px); background:var(--text); color:white; padding:11px 20px; border-radius:var(--radius-sm); font-size:13.5px; font-weight:500; box-shadow:var(--shadow-xl); z-index:200; opacity:0; transition:all 0.25s; white-space:nowrap; }
.toast.show { transform:translateX(-50%) translateY(0); opacity:1; }
</style>
