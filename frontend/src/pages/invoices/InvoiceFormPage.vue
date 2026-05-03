<template>
  <div class="page-wrap">
    <!-- Header bar -->
    <div class="top-bar">
      <router-link to="/invoices" class="back-link">← Накладні</router-link>
      <div class="top-actions">
        <button class="btn-outline" @click="printInvoice" v-if="invoiceId">Друк / PDF</button>
        <button class="btn-outline" @click="exportXlsx" v-if="invoiceId" :disabled="exporting">
          {{ exporting ? 'Завантаження...' : 'Експорт XLSX' }}
        </button>
        <button class="btn-primary" @click="save" :disabled="saving">
          {{ saving ? 'Збереження...' : (invoiceId ? 'Зберегти' : 'Створити') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Завантаження...</div>
    <template v-else>
      <!-- Header fields -->
      <div class="tile">
        <h3>Накладна (вимога) Додаток 25</h3>
        <div class="form-grid">
          <div class="form-row">
            <label>№ накладної</label>
            <input v-model="form.doc_number" placeholder="Н-440/25" />
          </div>
          <div class="form-row">
            <label>Дата складання</label>
            <input v-model="form.composed_date" type="date" />
          </div>
          <div class="form-row">
            <label>Термін дії</label>
            <input v-model="form.validity_date" placeholder="31.12.2025" />
          </div>
          <div class="form-row">
            <label>Дата операції</label>
            <input v-model="form.operation_date" type="date" />
          </div>
          <div class="form-row">
            <label>Місце складання</label>
            <input v-model="form.composed_location" :placeholder="unitSettings?.location || ''" />
          </div>
          <div class="form-row">
            <label>Служба</label>
            <input v-model="form.service" placeholder="Технічна" />
          </div>
          <div class="form-row">
            <label>Вид операції</label>
            <input v-model="form.op_type_text" placeholder="Внутрішнє переміщення" />
          </div>
          <div class="form-row">
            <label>Підстава</label>
            <input v-model="form.basis" placeholder="Наказ №..." />
          </div>
          <div class="form-row">
            <label>Звідки (підрозділ)</label>
            <input v-model="form.from_unit" />
          </div>
          <div class="form-row">
            <label>Куди (підрозділ)</label>
            <input v-model="form.to_unit" />
          </div>
          <div class="form-row">
            <label>Відповідальна особа-отримувач</label>
            <input v-model="form.responsible_recipient" />
          </div>
          <div class="form-row">
            <label>Статус</label>
            <select v-model="form.status">
              <option value="draft">Чернетка</option>
              <option value="final">Фінальна</option>
            </select>
          </div>
        </div>

        <div class="persons-grid">
          <div class="person-field">
            <label>Передає</label>
            <PersonSelect v-model="form.sender_id" :persons="persons" />
          </div>
          <div class="person-field">
            <label>Приймає</label>
            <PersonSelect v-model="form.receiver_id" :persons="persons" />
          </div>
          <div class="person-field">
            <label>Керівник (підписант)</label>
            <PersonSelect v-model="form.commander_id" :persons="persons" />
          </div>
          <div class="person-field">
            <label>МВО здав</label>
            <PersonSelect v-model="form.mvo_from_id" :persons="persons" />
          </div>
          <div class="person-field">
            <label>МВО прийняв</label>
            <PersonSelect v-model="form.mvo_to_id" :persons="persons" />
          </div>
        </div>
      </div>

      <!-- Items table -->
      <div class="tile">
        <div class="tile-header">
          <h3>Позиції</h3>
          <button class="btn-outline" @click="addItem">+ Додати рядок</button>
        </div>

        <div class="table-scroll">
          <table class="items-table">
            <thead>
              <tr>
                <th style="width:40px">№</th>
                <th>Назва майна</th>
                <th style="width:130px">Код номенкл.</th>
                <th style="width:80px">Од. виміру</th>
                <th style="width:100px">Категорія</th>
                <th style="width:110px">Ціна за од.</th>
                <th style="width:100px">К-сть відпр.</th>
                <th style="width:100px">К-сть прийн.</th>
                <th style="width:110px">Сума</th>
                <th style="width:140px">Примітка</th>
                <th style="width:32px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in form.items" :key="idx">
                <td class="center">{{ idx + 1 }}</td>
                <td>
                  <ItemAutocomplete
                    v-model="item.item_name"
                    :items="items"
                    @select="onItemSelect(idx, $event)"
                  />
                </td>
                <td><input v-model="item.nomenclature_code" class="cell-input" /></td>
                <td><input v-model="item.unit_of_measure" class="cell-input" /></td>
                <td><input v-model="item.category" class="cell-input" /></td>
                <td><input v-model.number="item.price" type="number" min="0" step="0.01" class="cell-input" @input="recalc(idx)" /></td>
                <td><input v-model.number="item.quantity" type="number" min="0" step="1" class="cell-input" @input="recalc(idx)" /></td>
                <td><input v-model.number="item.qty_received" type="number" min="0" step="1" class="cell-input" /></td>
                <td class="center amount-cell">{{ formatAmount(item.amount) }}</td>
                <td><input v-model="item.notes" class="cell-input" /></td>
                <td class="center">
                  <button class="del-btn" @click="removeItem(idx)">×</button>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="6" class="totals-label">Разом:</td>
                <td class="center total-val">{{ totalQty }}</td>
                <td></td>
                <td class="center total-val">{{ formatAmount(totalAmount) }}</td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div class="words-row">
          <div class="form-row">
            <label>Всього одиниць (прописом)</label>
            <input v-model="form.total_qty_words" placeholder="Двадцять" />
          </div>
          <div class="form-row">
            <label>Сума (прописом)</label>
            <input v-model="form.total_amount_words" placeholder="Двадцять тисяч гривень" />
          </div>
        </div>
      </div>
    </template>

    <!-- Print view overlay -->
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
import { getInvoice, createInvoice, updateInvoice, exportInvoiceXlsx } from '../../api/invoices'
import http from '../../api/http'
import PersonSelect from './components/PersonSelect.vue'
import ItemAutocomplete from './components/ItemAutocomplete.vue'
import InvoicePrintView from './components/InvoicePrintView.vue'

const route = useRoute()
const router = useRouter()
const invoiceId = computed(() => route.params.id !== 'new' ? Number(route.params.id) : null)

const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const showPrint = ref(false)

const persons = ref([])
const items = ref([])
const unitSettings = ref(null)

const emptyForm = () => ({
  doc_number: '',
  doc_date: '',
  composed_date: new Date().toISOString().slice(0, 10),
  composed_location: '',
  validity_date: '',
  operation_date: '',
  service: '',
  op_type_text: '',
  basis: '',
  from_unit: '',
  to_unit: '',
  responsible_recipient: '',
  sender_id: null,
  receiver_id: null,
  commander_id: null,
  mvo_from_id: null,
  mvo_to_id: null,
  total_qty_words: '',
  total_amount_words: '',
  status: 'draft',
  items: [],
})

const form = ref(emptyForm())

function addItem() {
  form.value.items.push({
    item_name: '', nomenclature_code: '', unit_of_measure: '',
    category: '', quantity: null, qty_received: null,
    price: null, amount: null, notes: '',
  })
}

function removeItem(idx) {
  form.value.items.splice(idx, 1)
}

function recalc(idx) {
  const it = form.value.items[idx]
  if (it.price != null && it.quantity != null) {
    it.amount = Math.round(it.price * it.quantity * 100) / 100
  } else {
    it.amount = null
  }
}

function onItemSelect(idx, item) {
  const it = form.value.items[idx]
  it.item_name = item.name || ''
  it.nomenclature_code = item.nomenclature_code || ''
  it.unit_of_measure = item.unit_of_measure || ''
  it.category = item.category || ''
  it.price = item.price ? parseFloat(item.price) : null
  recalc(idx)
}

const totalQty = computed(() =>
  form.value.items.reduce((s, it) => s + (it.quantity || 0), 0)
)
const totalAmount = computed(() =>
  form.value.items.reduce((s, it) => s + (it.amount || 0), 0)
)

function formatAmount(v) {
  if (v == null || v === '') return '—'
  return Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (invoiceId.value) {
      await updateInvoice(invoiceId.value, payload)
    } else {
      const created = await createInvoice(payload)
      router.replace(`/invoices/${created.id}`)
    }
  } finally {
    saving.value = false
  }
}

async function exportXlsx() {
  if (!invoiceId.value) return
  exporting.value = true
  try {
    const resp = await exportInvoiceXlsx(invoiceId.value)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `nakладна_${form.value.doc_number || invoiceId.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

function printInvoice() {
  showPrint.value = true
}

async function loadRefs() {
  const [ps, its, us] = await Promise.all([
    http.get('/persons').then(r => r.data),
    http.get('/items').then(r => r.data),
    http.get('/settings/unit').then(r => r.data).catch(() => null),
  ])
  persons.value = ps
  items.value = its
  unitSettings.value = us
}

onMounted(async () => {
  loading.value = true
  try {
    await loadRefs()
    if (invoiceId.value) {
      const inv = await getInvoice(invoiceId.value)
      form.value = {
        ...emptyForm(),
        ...inv,
        items: inv.items || [],
      }
    } else {
      if (unitSettings.value) {
        form.value.composed_location = unitSettings.value.location || ''
      }
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-wrap { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; }
.back-link { color: #2563eb; text-decoration: none; font-size: 14px; }
.top-actions { display: flex; gap: 8px; }
.tile { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.tile h3 { margin: 0 0 16px; font-size: 16px; }
.tile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.tile-header h3 { margin: 0; }
.loading { text-align: center; padding: 60px; color: #94a3b8; }

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px 20px;
}
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 12px; color: #64748b; font-weight: 500; }
.form-row input, .form-row select {
  border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 7px 10px; font-size: 14px; outline: none;
}
.form-row input:focus, .form-row select:focus { border-color: #2563eb; }

.persons-grid {
  display: flex; flex-wrap: wrap; gap: 12px 20px; margin-top: 16px;
}
.person-field { display: flex; flex-direction: column; gap: 4px; min-width: 200px; flex: 1; }
.person-field label { font-size: 12px; color: #64748b; font-weight: 500; }

.table-scroll { overflow-x: auto; }
.items-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.items-table th {
  background: #f8fafc; padding: 8px 6px; text-align: center;
  border: 1px solid #e2e8f0; white-space: nowrap; font-size: 12px;
}
.items-table td { padding: 4px 4px; border: 1px solid #e2e8f0; }
.center { text-align: center; }
.cell-input {
  width: 100%; border: none; background: transparent; padding: 4px;
  font-size: 13px; outline: none;
}
.cell-input:focus { background: #eff6ff; border-radius: 3px; }
.del-btn {
  background: none; border: none; cursor: pointer; color: #dc2626;
  font-size: 16px; padding: 2px 4px; line-height: 1;
}
.del-btn:hover { color: #b91c1c; }
.amount-cell { color: #334155; }
.items-table tfoot td { padding: 8px 6px; font-weight: 600; background: #f8fafc; }
.totals-label { text-align: right; padding-right: 12px; }
.total-val { text-align: center; }

.words-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px; margin-top: 16px; }

.btn-primary {
  background: #2563eb; color: #fff; border: none; border-radius: 6px;
  padding: 8px 18px; cursor: pointer; font-size: 14px;
}
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.btn-outline {
  background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px;
  padding: 8px 14px; cursor: pointer; font-size: 14px;
}
.btn-outline:hover:not(:disabled) { background: #f1f5f9; }
.btn-outline:disabled { opacity: 0.6; cursor: default; }

/* Print overlay */
.print-overlay {
  position: fixed; inset: 0; background: #fff; z-index: 9999; overflow: auto;
}
.print-toolbar {
  display: flex; gap: 8px; padding: 12px 16px; background: #f8fafc;
  border-bottom: 1px solid #e2e8f0; position: sticky; top: 0;
}
.print-toolbar button {
  padding: 6px 14px; border-radius: 6px; border: 1px solid #cbd5e1;
  cursor: pointer; font-size: 13px; background: #fff;
}
@media print {
  .no-print { display: none !important; }
}
</style>
