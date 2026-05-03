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
        <template v-if="form.status === 'draft'">
          <button class="btn-outline" @click="save" :disabled="saving">
            {{ saving ? 'Збереження...' : 'Зберегти' }}
          </button>
          <button class="btn-sign" @click="doSign" :disabled="signing">
            {{ signing ? '...' : 'Підписати' }}
          </button>
        </template>
        <template v-else>
          <button class="btn-outline" @click="printDoc">Друк / PDF</button>
          <button class="btn-outline" @click="exportXlsx" v-if="form.doc_type === 'накладна_25'" :disabled="exporting">
            {{ exporting ? '...' : 'XLSX' }}
          </button>
          <button class="btn-unsign" @click="doUnsign" :disabled="signing">Зняти підпис</button>
        </template>
      </template>
    </TopBar>

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

        <!-- Extra fields for накладна_25 -->
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
            <div class="form-row">
              <label>Відп. отримувач</label>
              <input v-model="form.responsible_recipient" :readonly="isReadonly" />
            </div>
          </div>
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
          <h3>Позиції <span class="items-count">({{ form.items.length }})</span></h3>
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
                <td class="center">{{ idx + 1 }}</td>
                <td>
                  <div v-if="isReadonly" class="cell-text">{{ it.item_name }}</div>
                  <ItemAutocomplete v-else v-model="it.item_name" :items="items" @select="onItemSelect(idx, $event)" />
                </td>
                <td><CellInput v-model="it.nomenclature_code" :readonly="isReadonly" /></td>
                <td><CellInput v-model="it.unit_of_measure" :readonly="isReadonly" /></td>
                <td><CellInput v-model="it.category" :readonly="isReadonly" /></td>
                <td><CellInput v-model.number="it.price" type="number" :readonly="isReadonly" @change="recalc(idx)" /></td>
                <td><CellInput v-model.number="it.quantity" type="number" :readonly="isReadonly" @change="recalc(idx)" /></td>
                <td><CellInput v-model.number="it.qty_received" type="number" :readonly="isReadonly" /></td>
                <td class="center amount">{{ fmt(it.amount) }}</td>
                <td><CellInput v-model="it.notes" :readonly="isReadonly" /></td>
                <td v-if="!isReadonly" class="center">
                  <button class="del-btn" @click="removeItem(idx)">×</button>
                </td>
              </tr>
              <tr v-if="!form.items.length">
                <td :colspan="isReadonly ? 10 : 11" class="empty-items">Позицій немає</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td :colspan="isReadonly ? 6 : 6" class="totals-label">Разом:</td>
                <td class="center total-val">{{ totalQty }}</td>
                <td></td>
                <td class="center total-val">{{ fmt(totalAmount) }}</td>
                <td :colspan="isReadonly ? 1 : 2"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </template>

    <!-- Print overlay -->
    <div v-if="showPrint" class="print-overlay">
      <div class="print-toolbar no-print">
        <button @click="showPrint = false">✕ Закрити</button>
        <button @click="window.print()">Друкувати</button>
      </div>
      <InvoicePrintView :invoice="form" :unit-settings="unitSettings" :persons="persons" />
    </div>
  </div>
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

// simple inline cell input
const CellInput = {
  props: ['modelValue', 'readonly', 'type'],
  emits: ['update:modelValue', 'change'],
  template: `
    <input
      :value="modelValue"
      :type="type || 'text'"
      :readonly="readonly"
      class="cell-input"
      :class="{ 'cell-readonly': readonly }"
      @input="$emit('update:modelValue', $event.target.value)"
      @change="$emit('change')"
    />
  `,
}

const route = useRoute()
const router = useRouter()
const docId = computed(() => Number(route.params.id))

const loading = ref(false)
const saving = ref(false)
const signing = ref(false)
const exporting = ref(false)
const showPrint = ref(false)
const signErrors = ref([])

const persons = ref([])
const items = ref([])
const unitSettings = ref(null)

const emptyForm = () => ({
  doc_type: 'переміщення',
  doc_number: '', doc_date: '', from_unit: '', to_unit: '',
  basis: '', service: '',
  validity_date: '', composed_date: '', composed_location: '',
  operation_date: '', op_type_text: '', responsible_recipient: '',
  sender_id: null, receiver_id: null, commander_id: null,
  mvo_from_id: null, mvo_to_id: null,
  total_qty_words: '', total_amount_words: '',
  status: 'draft',
  items: [],
})
const form = ref(emptyForm())

const isReadonly = computed(() => form.value.status !== 'draft')

const personFields = [
  { key: 'sender_id',   label: 'Передає' },
  { key: 'receiver_id', label: 'Приймає' },
  { key: 'commander_id', label: 'Керівник' },
  { key: 'mvo_from_id', label: 'МВО здав' },
  { key: 'mvo_to_id',   label: 'МВО прийняв' },
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
  parts.push([p.last_name, p.first_name?.[0]+'.', p.patronymic?.[0]+'.'].filter(Boolean).join(' '))
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

const totalQty = computed(() => form.value.items.reduce((s, it) => s + (Number(it.quantity) || 0), 0))
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
    saving.value = false }
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
    a.click()
    URL.revokeObjectURL(url)
  } finally { exporting.value = false }
}

function printDoc() { showPrint.value = true }

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
.page-wrap { padding: 16px; display: flex; flex-direction: column; gap: 16px; }

.top-bar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.back-link { color: #2563eb; text-decoration: none; font-size: 14px; white-space: nowrap; }
.doc-title { display: flex; align-items: center; gap: 8px; flex: 1; }
.doc-num { font-size: 16px; font-weight: 600; color: #0f172a; }
.top-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.type-badge {
  display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 500;
}
.type-badge.incoming { background: #d1fae5; color: #065f46; }
.type-badge.transfer { background: #dbeafe; color: #1e40af; }
.type-badge.invoice  { background: #fef3c7; color: #92400e; }
.status-badge {
  display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px;
}
.status-badge.draft  { background: #f1f5f9; color: #475569; }
.status-badge.signed { background: #d1fae5; color: #065f46; font-weight: 600; }

.tile { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.tile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.tile-header h3 { margin: 0; font-size: 15px; }
.items-count { color: #64748b; font-weight: 400; font-size: 13px; }
.section-divider { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .05em; margin: 16px 0 10px; }

.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 18px; }
.form-row { display: flex; flex-direction: column; gap: 3px; }
.form-row label { font-size: 12px; color: #64748b; font-weight: 500; }
.form-row input, .form-row select {
  border: 1px solid #e2e8f0; border-radius: 6px; padding: 7px 10px;
  font-size: 14px; outline: none; background: #fff;
}
.form-row input:focus, .form-row select:focus { border-color: #2563eb; }
.form-row input[readonly] { background: #f8fafc; color: #475569; }
.form-row input.missing { border-color: #f87171; background: #fff1f2; }
.req { color: #ef4444; }

.persons-grid { display: flex; flex-wrap: wrap; gap: 10px 18px; margin-top: 12px; }
.person-field { display: flex; flex-direction: column; gap: 3px; min-width: 180px; flex: 1; }
.person-field label { font-size: 12px; color: #64748b; font-weight: 500; }
.person-select {
  border: 1px solid #e2e8f0; border-radius: 6px; padding: 7px 10px;
  font-size: 13px; outline: none; width: 100%;
}
.person-select:disabled { background: #f8fafc; color: #475569; }

.table-scroll { overflow-x: auto; }
.items-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.items-table th {
  background: #f8fafc; padding: 8px 5px; text-align: center;
  border: 1px solid #e2e8f0; font-size: 11px; white-space: nowrap;
}
.items-table td { padding: 3px 4px; border: 1px solid #e2e8f0; }
.center { text-align: center; }
.amount { color: #0f172a; }
:deep(.cell-input) {
  width: 100%; border: none; background: transparent; padding: 4px;
  font-size: 13px; outline: none;
}
:deep(.cell-input:focus) { background: #eff6ff; border-radius: 3px; }
:deep(.cell-readonly) { color: #475569; cursor: default; }
.cell-text { padding: 4px; font-size: 13px; color: #0f172a; }
.del-btn { background: none; border: none; cursor: pointer; color: #dc2626; font-size: 16px; padding: 0 4px; }
.empty-items { text-align: center; color: #94a3b8; padding: 16px; }
.items-table tfoot td { padding: 8px 5px; font-weight: 600; background: #f8fafc; }
.totals-label { text-align: right; padding-right: 10px; }
.total-val { text-align: center; }

.btn-primary {
  background: #2563eb; color: #fff; border: none; border-radius: 6px;
  padding: 8px 16px; cursor: pointer; font-size: 14px;
}
.btn-outline {
  background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px;
  padding: 8px 14px; cursor: pointer; font-size: 14px;
}
.btn-outline:hover:not(:disabled) { background: #f1f5f9; }
.btn-outline-sm {
  background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px;
  padding: 5px 12px; cursor: pointer; font-size: 13px;
}
.btn-outline-sm:hover { background: #f1f5f9; }
.btn-sign {
  background: #16a34a; color: #fff; border: none; border-radius: 6px;
  padding: 8px 18px; cursor: pointer; font-size: 14px; font-weight: 600;
}
.btn-sign:hover:not(:disabled) { background: #15803d; }
.btn-sign:disabled { opacity: 0.6; cursor: default; }
.btn-unsign {
  background: #fff; color: #dc2626; border: 1px solid #fca5a5; border-radius: 6px;
  padding: 8px 14px; cursor: pointer; font-size: 14px;
}
.btn-unsign:hover:not(:disabled) { background: #fef2f2; }
.btn-unsign:disabled { opacity: 0.6; cursor: default; }

.error-block {
  background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;
  padding: 12px 16px; font-size: 14px; color: #dc2626;
}
.error-block ul { margin: 6px 0 0 18px; }

.loading { text-align: center; padding: 60px; color: #94a3b8; }

.print-overlay { position: fixed; inset: 0; background: #fff; z-index: 9999; overflow: auto; }
.print-toolbar {
  display: flex; gap: 8px; padding: 12px 16px; background: #f8fafc;
  border-bottom: 1px solid #e2e8f0; position: sticky; top: 0;
}
.print-toolbar button {
  padding: 6px 14px; border-radius: 6px; border: 1px solid #cbd5e1;
  cursor: pointer; font-size: 13px; background: #fff;
}
@media print { .no-print { display: none !important; } }
</style>
