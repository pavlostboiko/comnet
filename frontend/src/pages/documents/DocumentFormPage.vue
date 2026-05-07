<template>
  <div class="page-wrap">
    <TopBar>
      <template #actions>
        <router-link to="/documents" class="back-link">← Документи</router-link>
        <div class="doc-title">
          <span class="type-badge" :class="typeClass(form.doc_type)">{{ typeLabel(form.doc_type) }}</span>
          <span class="doc-num">{{ form.doc_number || 'без номера' }}</span>
          <span class="status-badge" :class="form.status">{{ statusLabel(form.status) }}</span>
        </div>

        <!-- накладна_25 draft: Save + Sign -->
        <template v-if="form.doc_type === 'накладна_25' && form.status === 'draft'">
          <button class="btn-outline" @click="save" :disabled="saving">
            {{ saving ? 'Збереження...' : 'Зберегти' }}
          </button>
          <button class="btn-sign" @click="doSign" :disabled="signing">
            {{ signing ? '...' : 'Підписати' }}
          </button>
        </template>

        <!-- other types draft: Save only -->
        <template v-else-if="form.status === 'draft'">
          <button class="btn-outline" @click="save" :disabled="saving">
            {{ saving ? 'Збереження...' : 'Зберегти' }}
          </button>
        </template>

        <!-- накладна (будь-який тип): Print + XLSX -->
        <template v-if="isNakl">
          <button class="btn-outline" @click="printDoc">Друк / PDF</button>
          <button class="btn-outline" @click="exportXlsx" :disabled="exporting">
            {{ exporting ? '...' : 'XLSX' }}
          </button>
        </template>
        <!-- All signed docs: Unsign -->
        <button v-if="form.status !== 'draft'" class="btn-unsign" @click="doUnsign" :disabled="signing">
          Зняти підпис
        </button>
      </template>
    </TopBar>

    <div class="content-scroll">
      <div v-if="signErrors.length" class="error-block">
        <b>Для підписання заповніть:</b>
        <ul><li v-for="e in signErrors" :key="e">{{ fieldLabel(e) }}</li></ul>
      </div>

      <div v-if="loading" class="loading">Завантаження...</div>
      <template v-else>
        <!-- Header fields -->
        <div class="tile">
          <div class="form-grid">
            <div class="form-row">
              <label>Тип документа</label>
              <select v-model="form.doc_type" :disabled="isReadonly">
                <option value="надходження">Надходження</option>
                <option value="переміщення">Переміщення</option>
                <option value="накладна_25">Накладна (Дод. 25)</option>
              </select>
            </div>
            <div class="form-row">
              <label>№ документа <span class="req">*</span></label>
              <input v-model="form.doc_number" :readonly="isReadonly" :class="{ missing: signErrors.includes('doc_number') }" />
            </div>
            <div class="form-row">
              <label>Дата <span class="req">*</span></label>
              <input v-model="form.doc_date" type="date" :readonly="isReadonly" :class="{ missing: signErrors.includes('doc_date') }" />
            </div>
            <div class="form-row" v-if="form.doc_type !== 'надходження'">
              <label>Звідки <span class="req">*</span></label>
              <input v-model="form.from_unit" :readonly="isReadonly" :class="{ missing: signErrors.includes('from_unit') }" />
            </div>
            <div class="form-row">
              <label>Куди <span class="req">*</span></label>
              <input v-model="form.to_unit" :readonly="isReadonly" :class="{ missing: signErrors.includes('to_unit') }" />
            </div>
            <div class="form-row">
              <label>Підстава</label>
              <input v-model="form.basis" :readonly="isReadonly" />
            </div>
            <div class="form-row">
              <label>Служба</label>
              <input v-model="form.service" :readonly="isReadonly" />
            </div>
          </div>

          <!-- Extra fields only for накладна_25 -->
          <template v-if="form.doc_type === 'накладна_25'">
            <div class="section-divider">Реквізити накладної</div>
            <div class="form-grid">
              <div class="form-row">
                <label>Термін дії</label>
                <input v-model="form.validity_date" :readonly="isReadonly" />
              </div>
              <div class="form-row">
                <label>Дата складання</label>
                <input v-model="form.composed_date" type="date" :readonly="isReadonly" />
              </div>
              <div class="form-row">
                <label>Місце складання</label>
                <input v-model="form.composed_location" :readonly="isReadonly" :placeholder="unitSettings?.location" />
              </div>
              <div class="form-row">
                <label>Дата операції</label>
                <input v-model="form.operation_date" type="date" :readonly="isReadonly" />
              </div>
              <div class="form-row">
                <label>Вид операції</label>
                <input v-model="form.op_type_text" :readonly="isReadonly" />
              </div>
            </div>
            <div class="section-divider">Підписанти</div>
            <div class="persons-grid">
              <div class="person-field" v-for="pf in personFields" :key="pf.key">
                <label>{{ pf.label }}</label>
                <select v-model="form[pf.key]" :disabled="isReadonly" class="person-select">
                  <option :value="null">— не вказано —</option>
                  <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
                </select>
              </div>
            </div>
            <div class="form-grid" style="margin-top:12px">
              <div class="form-row">
                <label>Кількість (прописом)</label>
                <input v-model="form.total_qty_words" :readonly="isReadonly" />
              </div>
              <div class="form-row">
                <label>Сума (прописом)</label>
                <input v-model="form.total_amount_words" :readonly="isReadonly" />
              </div>
            </div>
          </template>
        </div>

        <!-- Items -->
        <div class="tile">
          <div class="tile-header">
            <span class="tile-title">Позиції</span>
            <span class="tile-count">{{ form.items.length }}</span>
            <button v-if="!isReadonly" class="btn-outline-sm" @click="addItem">+ Рядок</button>
          </div>
          <div class="table-scroll">
            <table class="items-table">
              <thead>
                <tr>
                  <th style="width:36px">№</th>
                  <th>Назва майна</th>
                  <th style="width:120px">Код номенкл.</th>
                  <th style="width:76px">Од.вим.</th>
                  <th style="width:90px">Категорія</th>
                  <th style="width:100px">Ціна</th>
                  <th style="width:90px">К-сть відпр.</th>
                  <th style="width:90px">К-сть прийн.</th>
                  <th style="width:100px">Сума</th>
                  <th style="width:130px">Примітка</th>
                  <th v-if="!isReadonly" style="width:28px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in form.items" :key="idx">
                  <td class="td-center">{{ idx + 1 }}</td>
                  <td>
                    <div v-if="isReadonly" class="cell-text">{{ it.item_name }}</div>
                    <ItemAutocomplete v-else v-model="it.item_name" :items="items" @select="onItemSelect(idx, $event)" />
                  </td>
                  <td v-if="isReadonly" class="cell-text">{{ it.nomenclature_code }}</td>
                  <td v-else><input v-model="it.nomenclature_code" class="cell-input" /></td>
                  <td v-if="isReadonly" class="cell-text">{{ it.unit_of_measure }}</td>
                  <td v-else><input v-model="it.unit_of_measure" class="cell-input" /></td>
                  <td v-if="isReadonly" class="cell-text">{{ it.category }}</td>
                  <td v-else><input v-model="it.category" class="cell-input" /></td>
                  <td v-if="isReadonly" class="cell-text td-right">{{ it.price != null ? fmt(it.price) : '' }}</td>
                  <td v-else><input v-model.number="it.price" type="number" class="cell-input" @change="recalc(idx)" /></td>
                  <td v-if="isReadonly" class="cell-text td-right">{{ it.quantity != null ? it.quantity : '' }}</td>
                  <td v-else><input v-model.number="it.quantity" type="number" class="cell-input" @change="recalc(idx)" /></td>
                  <td v-if="isReadonly" class="cell-text td-right">{{ it.qty_received != null ? it.qty_received : '' }}</td>
                  <td v-else><input v-model.number="it.qty_received" type="number" class="cell-input" /></td>
                  <td class="td-center td-amount">{{ fmt(it.amount) }}</td>
                  <td v-if="isReadonly" class="cell-text">{{ it.notes }}</td>
                  <td v-else><input v-model="it.notes" class="cell-input" /></td>
                  <td v-if="!isReadonly" class="td-center">
                    <button class="del-btn" @click="removeItem(idx)">×</button>
                  </td>
                </tr>
                <tr v-if="!form.items.length">
                  <td :colspan="isReadonly ? 10 : 11" class="empty-items">Позицій немає</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="6" class="totals-label">Разом:</td>
                  <td class="td-center total-val">{{ totalQty }}</td>
                  <td></td>
                  <td class="td-center total-val">{{ fmt(totalAmount) }}</td>
                  <td :colspan="isReadonly ? 1 : 2"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </template>
    </div>

  </div>

  <!-- Print overlay teleported to body so @media print can target it separately from #app -->
  <Teleport to="body">
    <div v-if="showPrint" class="print-overlay">
      <div class="print-toolbar">
        <button class="ptb-btn" @click="showPrint = false">✕ Закрити</button>
        <button class="ptb-btn ptb-primary" @click="printNow">Друкувати / Зберегти PDF</button>
      </div>
      <div class="print-body">
        <InvoicePrintView :invoice="form" :unit-settings="unitSettings" :persons="persons" />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '../../components/TopBar.vue'
import {
  getDocument, updateDocument, signDocument, unsignDocument, exportDocumentXlsx
} from '../../api/documents'
import http from '../../api/http'
import ItemAutocomplete from '../invoices/components/ItemAutocomplete.vue'
import InvoicePrintView from '../invoices/components/InvoicePrintView.vue'

const route = useRoute()
const router = useRouter()
const docId = computed(() => Number(route.params.id))

const loading   = ref(false)
const saving    = ref(false)
const signing   = ref(false)
const exporting = ref(false)
const showPrint = ref(false)
const signErrors = ref([])

const persons     = ref([])
const items       = ref([])
const unitSettings = ref(null)

const emptyForm = () => ({
  doc_type: 'переміщення',
  doc_type_label: null,
  doc_number: '', doc_date: '', from_unit: '', to_unit: '',
  basis: '', service: '',
  validity_date: '', composed_date: '', composed_location: '',
  operation_date: '', op_type_text: '',
  sender_id: null, receiver_id: null, commander_id: null,
  mvo_from_id: null, mvo_to_id: null,
  accountant_id: null, fin_chief_id: null,
  total_qty_words: '', total_amount_words: '',
  status: 'draft',
  items: [],
})
const form = ref(emptyForm())

const isReadonly = computed(() => form.value.status !== 'draft')
// накладна_25 created in-app OR imported переміщення via "Накладна (вимога)"
const isNakl = computed(() =>
  form.value.doc_type === 'накладна_25' ||
  (form.value.doc_type_label || '').includes('Накладна')
)

const personFields = [
  { key: 'sender_id',      label: 'Передає' },
  { key: 'receiver_id',    label: 'Приймає' },
  { key: 'commander_id',   label: 'Керівник' },
  { key: 'mvo_from_id',    label: 'МВО здав' },
  { key: 'mvo_to_id',      label: 'МВО прийняв' },
  { key: 'accountant_id',  label: 'Гол. бухгалтер' },
  { key: 'fin_chief_id',   label: 'Нач. фінслужби' },
]

function typeLabel(t) {
  return { надходження: 'Надходження', переміщення: 'Переміщення', накладна_25: 'Накладна (Дод. 25)' }[t] || t
}
function typeClass(t) {
  return { надходження: 'incoming', переміщення: 'transfer', накладна_25: 'invoice' }[t] || ''
}
function statusLabel(s) {
  return { draft: 'Чернетка', signed: 'Підписано', receiver_signed: 'Підписано отримувачем' }[s] || s
}
function fieldLabel(f) {
  const map = {
    doc_number: 'Номер документа', doc_date: 'Дата',
    from_unit: 'Звідки', to_unit: 'Куди',
    'items (список позицій порожній)': 'Хоча б одна позиція',
  }
  return map[f] || f
}
function personLabel(p) {
  const parts = []
  if (p.rank) parts.push(p.rank)
  parts.push([p.last_name, p.first_name?.[0] + '.', p.patronymic?.[0] + '.'].filter(Boolean).join(' '))
  return parts.join(' ')
}

function addItem() {
  form.value.items.push({
    item_name: '', nomenclature_code: '', unit_of_measure: '',
    category: '', quantity: null, qty_received: null,
    price: null, amount: null, notes: '',
  })
}
function removeItem(idx) { form.value.items.splice(idx, 1) }
function recalc(idx) {
  const it = form.value.items[idx]
  if (it.price != null && it.quantity != null)
    it.amount = Math.round(it.price * it.quantity * 100) / 100
  else
    it.amount = null
}
function onItemSelect(idx, item) {
  const it = form.value.items[idx]
  Object.assign(it, {
    item_name: item.name || '',
    nomenclature_code: item.nomenclature_code || '',
    unit_of_measure: item.unit_of_measure || '',
    category: item.category || '',
    price: item.price ? parseFloat(item.price) : null,
  })
  recalc(idx)
}

const totalQty    = computed(() => form.value.items.reduce((s, it) => s + (Number(it.quantity) || 0), 0))
const totalAmount = computed(() => form.value.items.reduce((s, it) => s + (Number(it.amount) || 0), 0))
function fmt(v) {
  if (v == null || v === '') return '—'
  return Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function applyDoc(doc) {
  form.value = { ...emptyForm(), ...doc, items: doc.items || [] }
}

async function save() {
  saving.value = true
  signErrors.value = []
  try {
    const updated = await updateDocument(docId.value, form.value)
    applyDoc(updated)
  } finally {
    saving.value = false
  }
}

async function doSign() {
  signing.value = true
  signErrors.value = []
  try {
    await save()
    const updated = await signDocument(docId.value)
    applyDoc(updated)
  } catch (e) {
    const data = e.response?.data
    if (data?.missing) signErrors.value = data.missing
    else signErrors.value = [data?.detail || 'Помилка підписання']
  } finally {
    signing.value = false
  }
}

async function doUnsign() {
  if (!confirm('Зняти підпис? Повязані рядки переміщень будуть видалені.')) return
  signing.value = true
  try {
    const updated = await unsignDocument(docId.value)
    applyDoc(updated)
  } finally { signing.value = false }
}

async function exportXlsx() {
  exporting.value = true
  try {
    const resp = await exportDocumentXlsx(docId.value)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `накладна_${form.value.doc_number || docId.value}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('Помилка експорту: ' + (e.response?.status || e.message))
  } finally {
    exporting.value = false
  }
}

function printDoc() { showPrint.value = true }
function printNow() { window.print() }

onMounted(async () => {
  loading.value = true
  try {
    const [doc, ps, its, us] = await Promise.all([
      getDocument(docId.value),
      http.get('/settings/persons').then(r => r.data),
      http.get('/items').then(r => r.data),
      http.get('/settings/unit').then(r => r.data).catch(() => null),
    ])
    applyDoc(doc)
    persons.value = ps
    items.value = its
    unitSettings.value = us
  } finally { loading.value = false }
})
</script>

<style scoped>
.page-wrap { height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
.content-scroll { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.content-scroll::-webkit-scrollbar { width: 6px; }
.content-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* TopBar slot */
.back-link { color: var(--accent); text-decoration: none; font-size: 13.5px; font-weight: 500; white-space: nowrap; }
.doc-title { display: flex; align-items: center; gap: 8px; flex: 1; }
.doc-num { font-size: 15px; font-weight: 600; color: var(--text); }

.btn-outline {
  background: var(--surface); color: var(--text-mid); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 7px 14px; cursor: pointer;
  font-family: inherit; font-size: 13.5px; font-weight: 500; white-space: nowrap;
}
.btn-outline:hover:not(:disabled) { background: var(--bg); color: var(--text); }
.btn-outline:disabled { opacity: 0.5; cursor: default; }

.btn-sign {
  background: #16a34a; color: #fff; border: none; border-radius: var(--radius-sm);
  padding: 7px 18px; cursor: pointer; font-family: inherit; font-size: 13.5px; font-weight: 600;
}
.btn-sign:hover:not(:disabled) { background: #15803d; }
.btn-sign:disabled { opacity: 0.6; cursor: default; }

.btn-unsign {
  background: var(--surface); color: var(--red, #dc2626); border: 1px solid #fca5a5;
  border-radius: var(--radius-sm); padding: 7px 14px; cursor: pointer;
  font-family: inherit; font-size: 13.5px;
}
.btn-unsign:hover:not(:disabled) { background: #fef2f2; }
.btn-unsign:disabled { opacity: 0.6; cursor: default; }

/* Badges */
.type-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; }
.type-badge.incoming { background: #d1fae5; color: #065f46; }
.type-badge.transfer { background: #dbeafe; color: #1e40af; }
.type-badge.invoice  { background: #fef3c7; color: #92400e; }

.status-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
.status-badge.draft           { background: var(--bg); color: var(--text-light); border: 1px solid var(--border); }
.status-badge.signed          { background: #d1fae5; color: #065f46; font-weight: 600; }
.status-badge.receiver_signed { background: #ede9fe; color: #5b21b6; font-weight: 600; }

/* Tile */
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; padding: 20px; }
.tile-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.tile-title { font-size: 15px; font-weight: 700; color: var(--text); }
.tile-count { font-family: 'DM Mono', monospace; font-size: 11.5px; font-weight: 500; background: var(--accent-light); color: var(--accent); padding: 2px 8px; border-radius: var(--radius-sm); }

.section-divider {
  font-size: 11px; font-weight: 600; color: var(--text-light);
  text-transform: uppercase; letter-spacing: .07em;
  margin: 18px 0 10px; border-top: 1px solid var(--border-light); padding-top: 14px;
}

/* Form */
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 18px; }
.form-row { display: flex; flex-direction: column; gap: 3px; }
.form-row label { font-size: 11.5px; color: var(--text-light); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.form-row input, .form-row select {
  border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 7px 10px;
  font-size: 13.5px; font-family: inherit; outline: none; background: var(--surface); color: var(--text);
}
.form-row input:focus, .form-row select:focus { border-color: var(--accent); }
.form-row input[readonly] { background: var(--bg); color: var(--text-mid); cursor: default; }
.form-row input.missing { border-color: #f87171; background: #fff1f2; }
.req { color: #ef4444; }

.persons-grid { display: flex; flex-wrap: wrap; gap: 10px 18px; }
.person-field { display: flex; flex-direction: column; gap: 3px; min-width: 180px; flex: 1; }
.person-field label { font-size: 11.5px; color: var(--text-light); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.person-select {
  border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 7px 10px;
  font-size: 13px; font-family: inherit; outline: none; width: 100%;
  background: var(--surface); color: var(--text);
}
.person-select:focus { border-color: var(--accent); }
.person-select:disabled { background: var(--bg); color: var(--text-mid); }

/* Items table */
.table-scroll { overflow-x: auto; margin: 0 -20px; padding: 0 20px; }
.items-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.items-table th {
  background: var(--bg); padding: 8px 6px; text-align: center;
  border: 1px solid var(--border); font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .05em; color: var(--text-light); white-space: nowrap;
}
.items-table td { padding: 3px 4px; border: 1px solid var(--border); color: var(--text-mid); }
.td-center { text-align: center; }
.td-right  { text-align: right; }
.td-amount { color: var(--text); }
.cell-input {
  width: 100%; border: none; background: transparent; padding: 4px;
  font-size: 13px; font-family: inherit; outline: none; color: var(--text-mid);
}
.cell-input:focus { background: var(--accent-light); border-radius: 3px; }
.cell-text { padding: 4px; font-size: 13px; color: var(--text-mid); }
.del-btn { background: none; border: none; cursor: pointer; color: #dc2626; font-size: 16px; padding: 0 4px; }
.empty-items { text-align: center; color: var(--text-light); padding: 24px; }
.items-table tfoot td { padding: 8px 6px; font-weight: 600; background: var(--bg); border: 1px solid var(--border); }
.totals-label { text-align: right; padding-right: 10px; color: var(--text-mid); }
.total-val { text-align: center; }

.btn-outline-sm {
  background: var(--surface); color: var(--text-mid); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 5px 12px; cursor: pointer;
  font-family: inherit; font-size: 13px; margin-left: auto;
}
.btn-outline-sm:hover { background: var(--bg); color: var(--text); }

/* Error block */
.error-block {
  background: #fef2f2; border: 1px solid #fca5a5; border-radius: var(--radius);
  padding: 12px 16px; font-size: 14px; color: #dc2626;
}
.error-block ul { margin: 6px 0 0 18px; }

.loading { text-align: center; padding: 60px; color: var(--text-light); font-size: 14px; }

@media print { .no-print { display: none !important; } }
</style>

<!-- Global styles for the teleported print overlay -->
<style>
.print-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: #fff; overflow-y: auto;
  display: flex; flex-direction: column;
}
.print-toolbar {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
  position: sticky; top: 0; z-index: 1;
  flex-shrink: 0;
}
.ptb-btn {
  padding: 7px 16px; border-radius: 6px; border: 1px solid #cbd5e1;
  cursor: pointer; font-size: 13.5px; font-family: inherit;
  background: #fff; color: #334155;
}
.ptb-btn:hover { background: #e2e8f0; }
.ptb-primary {
  background: #2563eb; color: #fff; border-color: #2563eb; font-weight: 600;
}
.ptb-primary:hover { background: #1d4ed8; }
.print-body { flex: 1; overflow-y: auto; }

@media print {
  #app { display: none !important; }
  .print-overlay { position: static !important; overflow: visible !important; }
  .print-toolbar { display: none !important; }
  .print-body { overflow: visible !important; }
}
</style>
