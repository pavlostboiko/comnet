<template>
  <div class="overlay" :class="{ open: !!itemId }" @click.self="$emit('close')">
    <div v-if="itemId" class="modal">
      <div class="modal-head">
        <div class="modal-title">
          Історія: <b>{{ itemTitle || `#${itemId}` }}</b>
        </div>
        <button class="modal-close" @click="$emit('close')" title="Закрити">×</button>
      </div>

      <div v-if="loading" class="empty">Завантаження…</div>
      <div v-else-if="!events.length" class="empty">Історія порожня</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-date">Дата</th>
              <th class="col-kind">Подія</th>
              <th class="col-party">Куди / Кому</th>
              <th class="col-qty">К-сть</th>
              <th class="col-doc">Документ</th>
              <th class="col-actor">Виконав</th>
              <th class="col-notes">Примітки</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in events" :key="i" :class="kindClass(e.kind)">
              <td class="td-mono">{{ e.date || '—' }}</td>
              <td><span class="kind-chip" :class="kindClass(e.kind)">{{ kindLabel(e.kind) }}</span></td>
              <td>{{ partyLabel(e) }}</td>
              <td class="td-num">{{ fmtQty(e.qty) }}</td>
              <td class="td-mono td-dim">
                <template v-if="e.doc_number">{{ e.doc_number }}<span v-if="e.doc_date"> ({{ e.doc_date }})</span></template>
                <template v-else>—</template>
              </td>
              <td class="td-dim">{{ e.actor || '—' }}</td>
              <td class="td-notes" :title="e.notes || ''">{{ e.notes || '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getItemHistory } from '../api/items.js'

const props = defineProps({
  itemId: { type: Number, default: null },
  itemTitle: { type: String, default: '' },
})
defineEmits(['close'])

const events = ref([])
const loading = ref(false)

watch(() => props.itemId, async (id) => {
  if (!id) { events.value = []; return }
  loading.value = true
  try {
    events.value = await getItemHistory(id)
  } catch (_e) {
    events.value = []
  } finally {
    loading.value = false
  }
}, { immediate: true })

function kindLabel(k) {
  return { in: 'Надходження', out: 'Переміщення', issued: 'Видано', returned: 'Повернено' }[k] || k
}
function kindClass(k) {
  return `k-${k}`
}
function partyLabel(e) {
  if (e.kind === 'in')  return e.from_unit ? `← ${e.from_unit}` : (e.to_unit ? `→ ${e.to_unit}` : '—')
  if (e.kind === 'out') return e.to_unit ? `→ ${e.to_unit}` : (e.from_unit ? `← ${e.from_unit}` : '—')
  if (e.kind === 'issued' || e.kind === 'returned') return e.recipient || '—'
  return '—'
}
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isInteger(n)) return String(n)
  return n.toLocaleString('uk-UA', { minimumFractionDigits: 0, maximumFractionDigits: 4 })
}
</script>

<style scoped>
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; z-index:1200; padding:60px 20px 20px; overflow-y:auto; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(1000px, 100%); max-height:80vh; display:flex; flex-direction:column; overflow:hidden; }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-size:14px; color:var(--text-mid); }
.modal-title b { color:var(--text); font-weight:700; }
.modal-close { border:none; background:transparent; font-size:22px; line-height:1; color:var(--text-light); cursor:pointer; padding:0 6px; }
.modal-close:hover { color:var(--text); }
.empty { padding:40px; text-align:center; color:var(--text-light); font-style:italic; }

.table-wrap { overflow-y:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 12px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; position:sticky; top:0; z-index:1; }

.col-date  { width:110px; }
.col-kind  { width:130px; }
.col-party { width:22%; }
.col-qty   { width:80px; text-align:right; }
.col-doc   { width:150px; }
.col-actor { width:120px; }
.col-notes { width:22%; }

.td-mono  { font-family:'DM Mono', monospace; font-size:12px; }
.td-num   { text-align:right; font-family:'DM Mono', monospace; }
.td-dim   { color:var(--text-light); }
.td-notes { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text-mid); }

.kind-chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; }
.kind-chip.k-in       { background:#dbeafe; color:#1e40af; }
.kind-chip.k-out      { background:#fee2e2; color:#991b1b; }
.kind-chip.k-issued   { background:#dcfce7; color:#166534; }
.kind-chip.k-returned { background:#fef3c7; color:#854d0e; }
</style>
