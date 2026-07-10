<template>
  <div class="overlay" :class="{ open: !!item }" @click.self="$emit('close')">
    <div v-if="item" class="modal">
      <div class="modal-head">
        <div class="modal-title">
          Видати: <b>{{ item.name || item.item_card_num }}</b>
          <span v-if="item.serial_number" class="mono">· {{ item.serial_number }}</span>
        </div>
        <button class="modal-close" @click="$emit('close')" title="Закрити">×</button>
      </div>

      <div class="modal-body">
        <!-- Current holder hint (for serial only) -->
        <div v-if="isSerial && currentHolder" class="current-holder">
          Зараз у: <b>{{ currentHolder }}</b> — видача перевизначить тримача
        </div>
        <div v-if="!isSerial" class="qty-hint">
          Вільно: <b>{{ fmtQty(freeQty) }}</b> з {{ fmtQty(item.qty) }}
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Кому *</label>
            <RecipientAutocomplete
              v-model="form.recipient_id"
              :recipients="recipients"
              placeholder="прізвище або створити нове"
              @created="onRecipientCreated" />
          </div>
          <div class="form-group">
            <label class="form-label">К-сть</label>
            <input v-if="isSerial" type="text" class="form-input" value="1" disabled />
            <input v-else type="number" class="form-input" v-model="form.qty" min="0.0001" :max="freeQty" step="0.0001" />
          </div>
          <div class="form-group">
            <label class="form-label">Дата видачі</label>
            <input type="date" class="form-input" v-model="form.issued_at" :placeholder="'сьогодні за замовчуванням'">
          </div>
          <div class="form-group full">
            <label class="form-label">Примітки</label>
            <input type="text" class="form-input" v-model="form.notes" placeholder="Опціонально" />
          </div>
        </div>

        <div v-if="error" class="form-error">{{ error }}</div>
      </div>

      <div class="modal-foot">
        <button class="btn-secondary" @click="$emit('close')" :disabled="saving">Скасувати</button>
        <button class="btn-primary" @click="submit" :disabled="!canSubmit || saving">
          {{ saving ? 'Збереження…' : 'Видати' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import RecipientAutocomplete from './RecipientAutocomplete.vue'
import { getRecipients } from '../api/recipients.js'
import { getItem, updateItem } from '../api/items.js'
import { createSplit } from '../api/splits.js'

const props = defineProps({
  item: { type: Object, default: null },  // { item_id, item_card_num, name, serial_number, qty }
})
const emit = defineEmits(['close', 'issued'])

const recipients = ref([])
const currentHolder = ref('')
const freeQty = ref(0)
const form = ref({ recipient_id: null, qty: 1, issued_at: '', notes: '' })
const saving = ref(false)
const error = ref('')

const isSerial = computed(() => !!props.item?.serial_number)
const canSubmit = computed(() => !!form.value.recipient_id && (isSerial.value || (Number(form.value.qty) > 0 && Number(form.value.qty) <= freeQty.value)))

async function loadRecipients() {
  try {
    const { data } = await getRecipients()
    recipients.value = data
  } catch (_e) { recipients.value = [] }
}

async function loadItemState() {
  if (!props.item?.item_id) return
  try {
    const it = await getItem(props.item.item_id)
    currentHolder.value = it.issued_to_name || ''
    // For non-serial: free_qty derived on backend
    freeQty.value = Number(it.free_qty ?? it.quantity ?? 0)
    if (isSerial.value) freeQty.value = 1
  } catch (_e) {
    freeQty.value = Number(props.item.qty || 0)
  }
}

function onRecipientCreated(r) {
  if (!recipients.value.find(x => x.id === r.id)) recipients.value.push(r)
}

function reset() {
  form.value = { recipient_id: null, qty: 1, issued_at: '', notes: '' }
  currentHolder.value = ''
  freeQty.value = 0
  error.value = ''
  saving.value = false
}

watch(() => props.item, async (it) => {
  reset()
  if (!it) return
  await Promise.all([loadRecipients(), loadItemState()])
}, { immediate: true })

async function submit() {
  if (!canSubmit.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (isSerial.value) {
      // PUT items — hook journals the split with issued_at
      await updateItem(props.item.item_id, {
        issued_to_recipient_id: form.value.recipient_id,
        issued_at: form.value.issued_at || null,
      })
    } else {
      await createSplit(props.item.item_id, {
        recipient_id: form.value.recipient_id,
        qty: Number(form.value.qty),
        issued_at: form.value.issued_at || null,
        notes: form.value.notes || null,
      })
    }
    emit('issued')
    emit('close')
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Не вдалось зберегти'
  } finally {
    saving.value = false
  }
}

function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isInteger(n)) return String(n)
  return n.toLocaleString('uk-UA', { minimumFractionDigits: 0, maximumFractionDigits: 4 })
}
</script>

<style scoped>
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; z-index:1300; padding:80px 20px 20px; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(640px, 100%); display:flex; flex-direction:column; }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-size:14px; color:var(--text-mid); }
.modal-title b { color:var(--text); font-weight:700; }
.modal-title .mono { font-family:'DM Mono', monospace; color:var(--text-light); font-size:12.5px; margin-left:4px; }
.modal-close { border:none; background:transparent; font-size:22px; line-height:1; color:var(--text-light); cursor:pointer; padding:0 6px; }
.modal-close:hover { color:var(--text); }

.modal-body { padding:16px 20px; }
.current-holder { padding:8px 12px; background:#fef3c7; border-left:3px solid #d97706; color:#854d0e; font-size:12.5px; border-radius:3px; margin-bottom:14px; }
.qty-hint { font-size:12.5px; color:var(--text-mid); margin-bottom:12px; }
.qty-hint b { color:var(--text); }

.form-grid { display:grid; grid-template-columns:1fr 100px 140px; gap:12px; }
.form-group { display:flex; flex-direction:column; gap:4px; }
.form-group.full { grid-column:1 / -1; }
.form-label { font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; }
.form-input { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; color:var(--text); background:var(--surface); }
.form-input:focus { outline:none; border-color:var(--accent); }
.form-input:disabled { background:var(--bg); color:var(--text-light); }

.form-error { margin-top:12px; padding:8px 12px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }

.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-secondary, .btn-primary { padding:7px 16px; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; cursor:pointer; }
.btn-secondary { background:transparent; border:1px solid var(--border); color:var(--text-mid); }
.btn-secondary:hover { background:var(--bg); }
.btn-primary { background:var(--accent); border:1px solid var(--accent); color:white; }
.btn-primary:hover:not(:disabled) { filter:brightness(0.9); }
.btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
</style>
