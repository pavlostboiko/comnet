<template>
  <div class="page-wrap">
    <TopBar>
      <template #actions>
        <router-link to="/documents" class="back-link">← Документи</router-link>
        <div class="doc-title">
          <span class="type-badge" :class="opClass(form.operation)">{{ opLabel(form.operation) }}</span>
          <span class="form-badge">{{ formLabel(form.form_type) }}</span>
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

        <template v-if="hasXlsx">
          <button class="btn-outline" @click="exportXlsx" :disabled="exporting">
            {{ exporting ? '...' : 'XLSX' }}
          </button>
        </template>
        <button v-if="form.status !== 'draft'" class="btn-unsign" @click="doUnsign" :disabled="signing">
          Зняти підпис
        </button>
      </template>
    </TopBar>

    <div class="content-scroll">
      <div v-if="warnings.length" class="warn-block">
        <ul><li v-for="w in warnings" :key="w">{{ w }}</li></ul>
      </div>
      <div v-if="signErrors.length" class="error-block">
        <b>Для підписання заповніть:</b>
        <ul><li v-for="e in signErrors" :key="e">{{ fieldLabel(e) }}</li></ul>
      </div>

      <div v-if="loading" class="loading">Завантаження...</div>

      <!-- ── form=накладна (нова форма за ТЗ §3) ─────────────────────── -->
      <template v-else-if="form.form_type === 'накладна'">

        <!-- 3.1 Реквізити документа -->
        <div class="tile">
          <div class="tile-title">Реквізити документа</div>
          <div class="form-grid">
            <div class="form-row">
              <label>Найменування організації</label>
              <input :value="unitSettings?.name || ''" readonly />
            </div>
            <div class="form-row">
              <label>ЄДРПОУ</label>
              <input :value="unitSettings?.edrpou || ''" readonly />
            </div>
            <div class="form-row">
              <label>Місце складання</label>
              <input :value="unitSettings?.location || ''" readonly />
            </div>
            <div class="form-row">
              <label>Тип операції</label>
              <select v-model.number="form.op_type_id" :disabled="isReadonly">
                <option :value="null">— не вказано —</option>
                <option v-for="ot in opTypes" :key="ot.id" :value="ot.id">{{ ot.name }}</option>
              </select>
            </div>
            <div class="form-row">
              <label>Номер накладної</label>
              <input v-model="form.doc_number" :readonly="isReadonly"
                     :placeholder="numberPlaceholder"
                     :class="{ missing: signErrors.includes('doc_number') }" />
            </div>
            <div class="form-row">
              <label>Дата <span class="req">*</span></label>
              <input v-model="form.doc_date" type="date" :readonly="isReadonly"
                     :class="{ missing: signErrors.includes('doc_date') }" />
            </div>
            <div class="form-row calc">
              <label>Дійсна до (calc: +3 дні)</label>
              <input :value="validityDisplay" readonly />
            </div>
            <div class="form-row">
              <label>Підстава (мета)</label>
              <input v-model="form.basis" :readonly="isReadonly" />
            </div>
          </div>
        </div>

        <!-- 3.2 Сторони — Звідки / Куди / Служба -->
        <div class="tile">
          <div class="tile-title">Сторони</div>
          <div class="form-grid three-col">
            <div class="party">
              <div class="party-head">Звідки</div>
              <!-- Надходження зовні: вільний текст постачальника -->
              <input
                v-if="form.operation === 'надходження'"
                v-model="form.from_unit"
                :readonly="isReadonly"
                class="party-select"
                placeholder="постачальник / в/ч / організація" />
              <!-- Переміщення: select з підрозділів довідника осіб -->
              <select
                v-else
                v-model.number="form.sender_id"
                :disabled="isReadonly"
                class="party-select">
                <option :value="null">— оберіть підрозділ —</option>
                <option v-for="p in subdivisionPersons" :key="p.id" :value="p.id">{{ p.unit }}</option>
              </select>
              <!-- Auto-fill підрозділ-відправника. Для надходження зовні
                   немає посади/ПІБ — приховуємо блок. -->
              <div v-if="form.operation === 'переміщення'" class="auto-block">
                <div class="auto-lbl">Передає</div>
                <div class="auto-val">{{ senderPostDisplay || '—' }}</div>
                <div class="auto-val">{{ senderNameDisplay || '—' }}</div>
              </div>
            </div>
            <div class="party">
              <div class="party-head">Куди</div>
              <select v-model.number="form.receiver_id" :disabled="isReadonly" class="party-select">
                <option :value="null">— оберіть підрозділ —</option>
                <option v-for="p in subdivisionPersons" :key="p.id" :value="p.id">{{ p.unit }}</option>
              </select>
              <div class="auto-block">
                <div class="auto-lbl">Приймає</div>
                <div class="auto-val">{{ receiverPostDisplay || '—' }}</div>
                <div class="auto-val">{{ responsibleRecipientDisplay || '—' }}</div>
              </div>
            </div>
            <div class="party">
              <div class="party-head">Служба</div>
              <select v-model.number="form.service_id" :disabled="isReadonly" class="party-select">
                <option :value="null">— оберіть службу —</option>
                <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <div class="auto-block">
                <div class="auto-lbl">Керівник</div>
                <div class="auto-val">{{ serviceChiefPostDisplay || '—' }}</div>
                <div class="auto-val">{{ serviceChiefNameDisplay || '—' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3.3 Підпис фінансової служби -->
        <div class="tile">
          <div class="tile-title">Підпис фінансової служби</div>
          <div class="form-grid">
            <div class="form-row">
              <label>Посадова особа фінслужби</label>
              <select v-model.number="form.fin_id" :disabled="isReadonly">
                <option :value="null">— не вказано —</option>
                <option v-for="p in persons" :key="p.id" :value="p.id">{{ finLabel(p) }}</option>
              </select>
            </div>
            <div class="form-row calc">
              <label>Посада</label>
              <input :value="finPostDisplay" readonly />
            </div>
            <div class="form-row calc">
              <label>ПІБ</label>
              <input :value="finNameDisplay" readonly />
            </div>
          </div>
        </div>

        <!-- 3.4 Позиції майна -->
        <div class="tile">
          <div class="tile-header">
            <span class="tile-title">Позиції майна</span>
            <span class="tile-count">{{ form.items.length }}</span>
            <button v-if="!isReadonly" class="btn-outline-sm" @click="addItem">+ Рядок</button>
          </div>
          <div class="table-scroll">
            <table class="items-table">
              <thead>
                <tr>
                  <th style="width:36px">№</th>
                  <th>Майно</th>
                  <th style="width:110px">Код</th>
                  <th style="width:70px">Од.</th>
                  <th style="width:70px">Кат.</th>
                  <th style="width:90px">Вартість</th>
                  <th style="width:80px">К-сть відпр.</th>
                  <th style="width:80px">К-сть прийн.</th>
                  <th style="width:100px">Сума</th>
                  <th style="width:130px">Примітка</th>
                  <th v-if="!isReadonly" style="width:28px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in form.items" :key="idx">
                  <td class="td-center">{{ idx + 1 }}</td>
                  <td>
                    <ItemAutocomplete
                      v-if="!isReadonly"
                      v-model="it.item_name"
                      :items="items"
                      @select="onAutocompleteSelect(idx, $event)" />
                    <div v-else class="cell-text">{{ it.item_name }}</div>
                  </td>
                  <td class="cell-text">{{ itemSnap(it).nomenclature_code }}</td>
                  <td class="cell-text">{{ itemSnap(it).unit_of_measure }}</td>
                  <td class="cell-text">{{ itemSnap(it).category }}</td>
                  <td class="cell-text td-right">{{ fmt(itemSnap(it).price) }}</td>
                  <td>
                    <input v-if="!isReadonly" v-model.number="it.quantity" type="number" class="cell-input" step="0.0001" />
                    <span v-else class="cell-text td-right">{{ it.quantity ?? '' }}</span>
                  </td>
                  <td>
                    <input v-if="!isReadonly" v-model.number="it.qty_received" type="number" class="cell-input" step="0.0001" />
                    <span v-else class="cell-text td-right">{{ it.qty_received ?? '' }}</span>
                  </td>
                  <td class="td-center td-amount">{{ fmt(rowAmount(it)) }}</td>
                  <td>
                    <input v-if="!isReadonly" v-model="it.notes" class="cell-input" />
                    <span v-else class="cell-text">{{ it.notes }}</span>
                  </td>
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
          <div class="words-block">
            <div class="word-row">
              <span class="word-label">Всього передано:</span>
              <span class="word-val">{{ qtyWordsDisplay || '—' }}</span>
              <span class="word-suffix">одиниць</span>
            </div>
            <div class="word-row">
              <span class="word-label">На суму:</span>
              <span class="word-val">{{ amountWordsDisplay || '—' }}</span>
            </div>
            <div class="word-hint" v-if="!isReadonly">Розраховується автоматично при збереженні.</div>
          </div>
        </div>
      </template>

      <!-- ── form=акт (Акт прийому-передачі) — мінімальна форма ────────── -->
      <template v-else-if="form.form_type === 'акт'">
        <div class="tile">
          <div class="tile-title">Реквізити акту</div>
          <div class="form-grid">
            <div class="form-row">
              <label>№ документа <span class="req">*</span></label>
              <input v-model="form.doc_number" :readonly="isReadonly"
                     :class="{ missing: signErrors.includes('doc_number') }" />
            </div>
            <div class="form-row">
              <label>Дата <span class="req">*</span></label>
              <input v-model="form.doc_date" type="date" :readonly="isReadonly"
                     :class="{ missing: signErrors.includes('doc_date') }" />
            </div>
            <div class="form-row">
              <label>Звідки</label>
              <input v-model="form.from_unit" :readonly="isReadonly"
                     placeholder="постачальник / в/ч / організація" />
            </div>
            <div class="form-row">
              <label>Куди <span class="req">*</span></label>
              <input v-model="form.to_unit" :readonly="isReadonly"
                     :class="{ missing: signErrors.includes('to_unit') }" />
            </div>
            <div class="form-row">
              <label>Підстава</label>
              <input v-model="form.basis" :readonly="isReadonly" />
            </div>
          </div>
        </div>

        <div class="tile">
          <div class="tile-header">
            <span class="tile-title">Позиції майна</span>
            <span class="tile-count">{{ form.items.length }}</span>
            <button v-if="!isReadonly" class="btn-outline-sm" @click="addItem">+ Рядок</button>
          </div>
          <div class="table-scroll">
            <table class="items-table">
              <thead>
                <tr>
                  <th style="width:36px">№</th>
                  <th>Майно</th>
                  <th style="width:110px">Код</th>
                  <th style="width:70px">Од.</th>
                  <th style="width:80px">К-сть</th>
                  <th style="width:130px">Примітка</th>
                  <th v-if="!isReadonly" style="width:28px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in form.items" :key="idx">
                  <td class="td-center">{{ idx + 1 }}</td>
                  <td>
                    <ItemAutocomplete
                      v-if="!isReadonly"
                      v-model="it.item_name"
                      :items="items"
                      @select="onAutocompleteSelect(idx, $event)" />
                    <div v-else class="cell-text">{{ it.item_name }}</div>
                  </td>
                  <td class="cell-text">{{ it.nomenclature_code || '' }}</td>
                  <td class="cell-text">{{ it.unit_of_measure || '' }}</td>
                  <td>
                    <input v-if="!isReadonly" v-model.number="it.quantity" type="number" class="cell-input" step="0.0001" />
                    <span v-else class="cell-text td-right">{{ it.quantity ?? '' }}</span>
                  </td>
                  <td>
                    <input v-if="!isReadonly" v-model="it.notes" class="cell-input" />
                    <span v-else class="cell-text">{{ it.notes }}</span>
                  </td>
                  <td v-if="!isReadonly" class="td-center">
                    <button class="del-btn" @click="removeItem(idx)">×</button>
                  </td>
                </tr>
                <tr v-if="!form.items.length">
                  <td :colspan="isReadonly ? 6 : 7" class="empty-items">Позицій немає</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>

</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '../../components/TopBar.vue'
import {
  getDocument, updateDocument, signDocument, unsignDocument, exportDocumentXlsx
} from '../../api/documents'
import http from '../../api/http'
import ItemAutocomplete from '../../components/ItemAutocomplete.vue'

const route = useRoute()
const docId = computed(() => Number(route.params.id))

const loading   = ref(false)
const saving    = ref(false)
const signing   = ref(false)
const exporting = ref(false)
const signErrors = ref([])
const warnings = ref([])

const persons      = ref([])
const items        = ref([])
const opTypes      = ref([])
const services     = ref([])
const unitSettings = ref(null)

const emptyForm = () => ({
  operation: 'переміщення',
  form_type: 'накладна',
  doc_type_label: null,
  doc_number: '', doc_date: '', date_operation: '',
  from_unit: '', to_unit: '', basis: '', service: '',
  op_type_id: null, service_id: null,
  sender_id: null, receiver_id: null, fin_id: null,
  status: 'draft',
  extra_data: {},
  items: [],
})
const form = ref(emptyForm())

const isReadonly = computed(() => form.value.status !== 'draft')
// XLSX export is wired only to the Накладна (вимога) form (any operation).
// Акт прийому-передачі has no template yet → button hidden.
const hasXlsx = computed(() => form.value.form_type === 'накладна')

// ── Lookups ──────────────────────────────────────────────────────────────
const personById  = (id) => id ? persons.value.find(p => p.id === id)  : null
const itemById    = (id) => id ? items.value.find(i => i.id === id)    : null
const opTypeById  = (id) => id ? opTypes.value.find(o => o.id === id)  : null
const serviceById = (id) => id ? services.value.find(s => s.id === id) : null

// Persons that represent a subdivision (have non-empty `unit`). TZ §2.1: one
// row per subdivision; the dropdown shows the unit, the FK still points at
// the person whose snap will be captured.
const subdivisionPersons = computed(() =>
  persons.value
    .filter(p => (p.unit || '').trim() && p.is_active !== false)
    .slice()
    .sort((a, b) => (a.unit || '').localeCompare(b.unit || '', 'uk'))
)

const selectedSender    = computed(() => personById(form.value.sender_id))
const selectedReceiver  = computed(() => personById(form.value.receiver_id))
const selectedFin       = computed(() => personById(form.value.fin_id))
const selectedOpType    = computed(() => opTypeById(form.value.op_type_id))
const selectedService   = computed(() => serviceById(form.value.service_id))

// Frozen snap (signed) vs live FK (draft). Per TZ §1: signed docs must NOT
// reflect later changes in the underlying directories.
const ed = computed(() => form.value.extra_data || {})
const senderPostDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_sender_post || '') : (selectedSender.value?.position || ''))
const senderNameDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_sender_name || '') : personDisplayName(selectedSender.value))
const receiverPostDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_recv_post || '') : (selectedReceiver.value?.position || ''))
const finPostDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_fin_post || '') : (selectedFin.value?.position || ''))
const finNameDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_fin_name || '') : personDisplayName(selectedFin.value))
const opTypeDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_op_type_name || '') : (selectedOpType.value?.name || ''))
const serviceChiefPostDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_service_chief_post || '') : (selectedService.value?.chief_position || ''))
const serviceChiefNameDisplay = computed(() =>
  isReadonly.value ? (ed.value.snap_service_chief_name || '') : (selectedService.value?.chief_name || ''))
// ── Display helpers ──────────────────────────────────────────────────────
function personDisplayName(p) {
  if (!p) return ''
  return [p.first_name, (p.last_name || '').toUpperCase()].filter(Boolean).join(' ')
}
function finLabel(p) {
  if (!p) return ''
  return (p.position || '—') + ' — ' + personDisplayName(p)
}

const responsibleRecipientDisplay = computed(() => {
  if (isReadonly.value) {
    const ed = form.value.extra_data || {}
    return [ed.snap_recv_rank, ed.snap_recv_name].filter(Boolean).join(' ')
  }
  const r = selectedReceiver.value
  if (!r) return ''
  return [r.rank, personDisplayName(r)].filter(Boolean).join(' ')
})

const numberPlaceholder = computed(() => {
  const op = selectedOpType.value
  if (op?.number_prefix) return `авто: ${op.number_prefix}<N>`
  return ''
})

const UK_MONTHS = ['січня','лютого','березня','квітня','травня','червня',
                   'липня','серпня','вересня','жовтня','листопада','грудня']
function calcValidity(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d)) return ''
  d.setDate(d.getDate() + 3)
  const dd = String(d.getDate()).padStart(2, '0')
  return `"${dd}" ${UK_MONTHS[d.getMonth()]} ${d.getFullYear()} року`
}
const validityDisplay = computed(() => {
  if (isReadonly.value) return form.value.extra_data?.validity_date || ''
  return calcValidity(form.value.doc_date)
})

const qtyWordsDisplay    = computed(() => form.value.extra_data?.total_qty_words || '')
const amountWordsDisplay = computed(() => form.value.extra_data?.total_amount_words || '')

// ── Items ────────────────────────────────────────────────────────────────
function addItem() {
  form.value.items.push({
    item_id: null, item_name: '', nomenclature_code: '',
    unit_of_measure: '', category: '', price: null,
    quantity: null, qty_received: null, amount: null, notes: '',
  })
}
function removeItem(idx) { form.value.items.splice(idx, 1) }

function itemSnap(row) {
  // Live snapshot in draft (from items table by item_id);
  // frozen snapshot in signed (from stored snap columns).
  // Fallback to row's stored snap if the referenced item was removed.
  const stored = {
    nomenclature_code: row.nomenclature_code || '',
    unit_of_measure:   row.unit_of_measure   || '',
    category:          row.category          || '',
    price:             row.price,
  }
  if (isReadonly.value || !row.item_id) return stored
  const ref = itemById(row.item_id)
  if (!ref) return stored
  return {
    nomenclature_code: ref.nomenclature_code || '',
    unit_of_measure:   ref.unit_of_measure   || '',
    category:          ref.category          || '',
    price:             ref.price,
  }
}
function rowAmount(row) {
  const s = itemSnap(row)
  const p = Number(s.price) || 0
  const q = Number(row.quantity) || 0
  return p && q ? Math.round(p * q * 100) / 100 : null
}
function onAutocompleteSelect(idx, item) {
  // Copy snap into the row so columns render immediately. Backend re-snaps
  // authoritatively on save from item_id (single source of truth for signed
  // docs); these row values are for display + draft persistence only.
  const row = form.value.items[idx]
  row.item_id           = item.id
  row.item_name         = item.name || ''
  row.nomenclature_code = item.nomenclature_code || ''
  row.unit_of_measure   = item.unit_of_measure || ''
  row.category          = item.category || ''
  row.price             = item.price != null ? Number(item.price) : null
  // qty defaults: only set if empty (don't clobber a quantity the user typed)
  if (row.quantity == null || row.quantity === '') row.quantity = 1
  if (row.qty_received == null || row.qty_received === '') row.qty_received = 1
  // Serial: always overwrite — changing the item means the previous serial
  // is no longer correct. User can edit the note after if they need to.
  row.notes = item.serial_number || ''
}

const totalQty    = computed(() => form.value.items.reduce((s, it) => s + (Number(it.quantity) || 0), 0))
const totalAmount = computed(() => form.value.items.reduce((s, it) => s + (rowAmount(it) || 0), 0))

function fmt(v) {
  if (v == null || v === '') return ''
  return Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── Labels ───────────────────────────────────────────────────────────────
function opLabel(o) {
  return { надходження: 'Надходження', переміщення: 'Переміщення' }[o] || o
}
function opClass(o) {
  return { надходження: 'incoming', переміщення: 'transfer' }[o] || ''
}
function formLabel(f) {
  return { накладна: 'Накладна (вимога)', акт: 'Акт прийому-передачі' }[f] || f
}
function statusLabel(s) {
  return { draft: 'Чернетка', signed: 'Підписано' }[s] || s
}
function fieldLabel(f) {
  const map = {
    doc_number: 'Номер документа', doc_date: 'Дата',
    from_unit: 'Звідки', to_unit: 'Куди',
    'items (список позицій порожній)': 'Хоча б одна позиція',
  }
  return map[f] || f
}

// ── Persistence ──────────────────────────────────────────────────────────
function applyDoc(doc) {
  // Backend emits `form` for the paper form; in the Vue template it conflicts
  // with `form` (our reactive ref), so rename to `form_type` in local state.
  const { form: formField, ...rest } = doc
  form.value = {
    ...emptyForm(),
    ...rest,
    form_type: formField ?? doc.form_type ?? 'накладна',
    items: doc.items || [],
  }
  warnings.value = doc.warnings || []
  applyDefaultsIfDraft()
}

// Auto-select the first available option in each dropdown when this is a
// draft and the field is empty. Only fires for form=накладна — акт form
// doesn't surface those dropdowns.
function applyDefaultsIfDraft() {
  if (form.value.status !== 'draft') return
  if (!form.value.doc_date) form.value.doc_date = new Date().toISOString().slice(0, 10)
  if (form.value.form_type !== 'накладна') return
  if (!form.value.op_type_id && opTypes.value.length)
    form.value.op_type_id = opTypes.value[0].id
  if (form.value.operation === 'переміщення'
      && !form.value.sender_id && subdivisionPersons.value.length)
    form.value.sender_id = subdivisionPersons.value[0].id
  if (!form.value.receiver_id && subdivisionPersons.value.length)
    form.value.receiver_id = subdivisionPersons.value[0].id
  if (!form.value.service_id && services.value.length)
    form.value.service_id = services.value[0].id
  if (!form.value.fin_id && persons.value.length)
    form.value.fin_id = persons.value[0].id
}

async function save() {
  saving.value = true
  signErrors.value = []
  warnings.value = []
  try {
    // Rename back: local form_type → backend field `form`
    const { form_type, ...rest } = form.value
    const payload = { ...rest, form: form_type }
    const updated = await updateDocument(docId.value, payload)
    applyDoc(updated)
  } finally { saving.value = false }
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
  } finally { signing.value = false }
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
    let detail = e.message
    if (e.response?.data instanceof Blob) detail = await e.response.data.text()
    else if (e.response?.data?.detail) detail = e.response.data.detail
    alert('Помилка експорту:\n' + String(detail).slice(0, 1000))
  } finally { exporting.value = false }
}

onMounted(async () => {
  loading.value = true
  try {
    const [doc, ps, its, ots, svs, us] = await Promise.all([
      getDocument(docId.value),
      http.get('/settings/persons').then(r => r.data),
      http.get('/items').then(r => r.data),
      http.get('/settings/op-types').then(r => r.data),
      http.get('/settings/services').then(r => r.data),
      http.get('/settings/unit').then(r => r.data).catch(() => null),
    ])
    persons.value      = ps
    items.value        = its
    opTypes.value      = ots
    services.value     = svs
    unitSettings.value = us
    applyDoc(doc)
  } finally { loading.value = false }
})
</script>

<style scoped>
.page-wrap { height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
.content-scroll { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.content-scroll::-webkit-scrollbar { width: 6px; }
.content-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

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

.type-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; }
.type-badge.incoming { background: #d1fae5; color: #065f46; }
.type-badge.transfer { background: #dbeafe; color: #1e40af; }
.type-badge.invoice  { background: #fef3c7; color: #92400e; }
.form-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 11.5px; color: var(--text-mid); background: var(--bg); border: 1px solid var(--border); font-family: 'DM Mono', monospace; }

.status-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
.status-badge.draft  { background: var(--bg); color: var(--text-light); border: 1px solid var(--border); }
.status-badge.signed { background: #d1fae5; color: #065f46; font-weight: 600; }

.tile { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 18px 20px; }
.tile-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.tile-title { font-size: 14px; font-weight: 700; color: var(--text); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }
.tile-count { font-family: 'DM Mono', monospace; font-size: 11.5px; font-weight: 500; background: var(--accent-light); color: var(--accent); padding: 2px 8px; border-radius: var(--radius-sm); }

.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 18px; }
.form-grid.two-col { grid-template-columns: repeat(2, 1fr); }
.form-grid.three-col { grid-template-columns: repeat(3, 1fr); }
@media (max-width: 880px) { .form-grid.three-col { grid-template-columns: 1fr; } }
.form-row { display: flex; flex-direction: column; gap: 3px; }
.form-row label { font-size: 11.5px; color: var(--text-light); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.form-row input, .form-row select {
  border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 7px 10px;
  font-size: 13.5px; font-family: inherit; outline: none; background: var(--surface); color: var(--text);
}
.form-row input:focus, .form-row select:focus { border-color: var(--accent); }
.form-row input[readonly] { background: var(--bg); color: var(--text-mid); cursor: default; }
.form-row input.missing { border-color: #f87171; background: #fff1f2; }
.form-row.calc input { font-style: italic; }
.req { color: #ef4444; }

.party { background: var(--bg); padding: 14px; border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 10px; }
.party-head { font-size: 12px; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: .07em; }

.party-select {
  border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px;
  font-size: 13.5px; font-family: inherit; outline: none; background: var(--surface); color: var(--text);
  width: 100%;
}
.party-select:focus { border-color: var(--accent); }
.party-select:disabled { background: var(--bg); color: var(--text-mid); }

.auto-block {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; background: var(--surface); border: 1px solid var(--border-light);
  border-radius: var(--radius-sm); font-size: 13px;
}
.auto-lbl { font-size: 10.5px; font-weight: 600; color: var(--text-light); text-transform: uppercase; letter-spacing: .07em; margin-bottom: 2px; }
.auto-val { color: var(--text); font-style: italic; }

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

.words-block { margin-top: 12px; padding: 12px; background: var(--bg); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 6px; }
.word-row { display: flex; gap: 8px; font-size: 13.5px; align-items: baseline; flex-wrap: wrap; }
.word-label { color: var(--text-light); font-weight: 600; }
.word-val { color: var(--text); font-weight: 500; font-style: italic; }
.word-suffix { color: var(--text-light); }
.word-hint { font-size: 12px; color: var(--text-light); font-style: italic; }

.error-block { background: #fef2f2; border: 1px solid #fca5a5; border-radius: var(--radius); padding: 12px 16px; font-size: 14px; color: #dc2626; }
.error-block ul { margin: 6px 0 0 18px; }
.warn-block { background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--radius); padding: 10px 14px; font-size: 13.5px; color: #92400e; }
.warn-block ul { margin: 4px 0 0 18px; }

.loading { text-align: center; padding: 60px; color: var(--text-light); font-size: 14px; }
</style>
