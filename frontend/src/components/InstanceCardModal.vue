<template>
  <div class="overlay" :class="{ open }" @click.self="$emit('close')">
    <div v-if="open" class="modal">
      <div class="modal-head">
        <span class="modal-title">Картка: {{ row.name }}</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-body">
        <div class="ro-grid">
          <div><span class="rl">Серійний №</span><span class="rv mono">{{ row.serial_no || '—' }}</span></div>
          <div><span class="rl">№ картки</span><span class="rv mono">{{ row.card_number || '—' }}</span></div>
          <div><span class="rl">Тип</span><span class="rv">{{ row.is_official ? 'облік' : 'ндм' }}</span></div>
          <div><span class="rl">Склад</span><span class="rv">{{ warehouseName || '—' }}</span></div>
          <div><span class="rl">На кому</span><span class="rv">{{ row.holder || '— на складі' }}</span></div>
        </div>

        <label class="fl">Точка зберігання</label>
        <select class="fi" :value="pointId ?? ''" :disabled="row.state !== 'stock'" @change="onPointChange">
          <option value="">— не вказано —</option>
          <option v-for="p in points" :key="p.id" :value="p.id">{{ p.name }}</option>
          <option v-if="createPoint" value="__new__">+ нова точка…</option>
        </select>
        <p v-if="row.state !== 'stock'" class="hint">Майно на руках — точка ставиться, коли воно на складі.</p>

        <label class="fl">Примітка</label>
        <textarea class="fi ta" v-model="note" rows="3" placeholder="напр. загублено ремінь"></textarea>

      </div>
      <div class="modal-foot">
        <button class="btn-sec" @click="$emit('close')">Скасувати</button>
        <button class="btn-pri" :disabled="busy" @click="save">Зберегти</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  row: { type: Object, default: () => ({}) },   // рядок «Залишків» (серійний)
  points: { type: Array, default: () => [] },   // точки поточного складу
  warehouseName: String,
  busy: Boolean,
  createPoint: { type: Function, default: null },   // null → створювати не можна (не admin)
})
const emit = defineEmits(['close', 'save'])

const note = ref('')
const pointId = ref(null)

// Модалка тримає власну копію — правки застосовуються лише на «Зберегти».
watch(() => [props.open, props.row], () => {
  if (!props.open) return
  note.value = props.row.note || ''
  pointId.value = props.row.storage_point_id || null
}, { immediate: true, deep: true })

// Точку можна завести на місці — інакше довелось би йти в Довідники й пам'ятати склад.
async function onPointChange(ev) {
  const val = ev.target.value
  if (val !== '__new__') { pointId.value = val ? Number(val) : null; return }
  ev.target.value = pointId.value ?? ''
  const name = prompt(`Нова точка на складі «${props.warehouseName || ''}»:`)
  if (!name || !name.trim()) return
  try {
    const point = await props.createPoint(name)
    pointId.value = point.id
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось створити точку')
  }
}

// Зберігає батько (він володіє даними складу) — модалка лише віддає значення.
function save() {
  emit('save', { note: note.value.trim() || null, storage_point_id: pointId.value || null })
}
</script>

<style scoped>
.overlay { position:fixed; inset:0; background:rgba(15,23,42,.45); display:none; align-items:center; justify-content:center; z-index:60; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow); width:min(520px,94vw); display:flex; flex-direction:column; }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:12px; }
.modal-title { font-weight:700; font-size:14px; flex:1; }
.modal-close { border:none; background:transparent; cursor:pointer; font-size:15px; color:var(--text-light); }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:6px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border-light); display:flex; justify-content:flex-end; gap:8px; }
.ro-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px 16px; margin-bottom:10px; }
.rl { display:block; font-size:11px; color:var(--text-light); text-transform:uppercase; letter-spacing:.04em; }
.rv { font-size:13.5px; color:var(--text); }
.mono { font-family:'DM Mono',monospace; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:6px; }
.fi { border:1px solid var(--border); border-radius:var(--radius-sm); padding:7px 10px; font-family:inherit; font-size:14px; color:var(--text); background:var(--surface); }
.ta { resize:vertical; }
.hint { margin:2px 0 0; font-size:11.5px; color:var(--text-light); }
.btn-sec, .btn-pri { border-radius:var(--radius-sm); padding:7px 16px; cursor:pointer; font-family:inherit; font-size:13px; border:1px solid var(--border); background:var(--surface); color:var(--text-mid); }
.btn-pri { background:var(--accent); color:#fff; border-color:var(--accent); }
.btn-pri:disabled { opacity:.6; cursor:not-allowed; }
</style>
