<template>
  <div class="rc-wrap">
    <input
      ref="inputRef"
      v-model="query"
      class="rc-input"
      :placeholder="placeholder || 'Прізвище…'"
      @focus="onFocus"
      @blur="onBlur"
      @input="open = true"
      @keydown.esc="open = false"
      @keydown.enter.prevent="onEnter"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
    />
    <Teleport to="body">
      <div v-if="open" class="rc-dropdown" :style="dropdownStyle">
        <div
          v-for="(r, i) in filtered" :key="r.id"
          class="rc-item"
          :class="{ active: i === highlighted }"
          @mousedown.prevent="select(r)"
        >
          <span class="rc-callsign">{{ r.callsign }}</span>
          <span v-if="!r.is_active" class="rc-inactive">архів</span>
        </div>
        <!-- Inline-create: visible when query non-empty and no exact match -->
        <div
          v-if="canCreate"
          class="rc-item rc-create"
          :class="{ active: highlighted === filtered.length }"
          @mousedown.prevent="createInline"
        >
          + Створити «{{ query.trim() }}»
        </div>
        <div v-if="!filtered.length && !canCreate" class="rc-empty">— нічого не знайдено —</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { createRecipient } from '../api/recipients.js'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },          // selected recipient id
  recipients: { type: Array, default: () => [] },                // full list (parent fetches)
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'created'])

const inputRef = ref(null)
const query = ref('')
const open = ref(false)
const highlighted = ref(0)
const dropdownStyle = ref({})

// Sync input text with selected recipient (parent passes recipients[])
function refreshFromModel() {
  if (props.modelValue == null) { query.value = ''; return }
  const r = (props.recipients || []).find(x => x.id === props.modelValue)
  query.value = r ? r.callsign : ''
}
watch(() => [props.modelValue, props.recipients], refreshFromModel, { immediate: true })

const filtered = computed(() => {
  const q = (query.value || '').trim().toLowerCase()
  if (!q) return props.recipients.slice(0, 30)
  return props.recipients
    .filter(r => (r.callsign || '').toLowerCase().includes(q))
    .slice(0, 30)
})

const canCreate = computed(() => {
  const q = (query.value || '').trim()
  if (!q) return false
  // Show «Створити» only if no exact-case-insensitive match exists
  return !props.recipients.some(r => (r.callsign || '').toLowerCase() === q.toLowerCase())
})

function updatePosition() {
  if (!inputRef.value) return
  const rect = inputRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    top:   `${rect.bottom + 2}px`,
    left:  `${rect.left}px`,
    width: `${Math.max(rect.width, 240)}px`,
  }
}

function onFocus() { open.value = true; nextTick(updatePosition) }
function onBlur() {
  setTimeout(() => { open.value = false }, 150)
}

function select(r) {
  emit('update:modelValue', r.id)
  query.value = r.callsign
  open.value = false
}

async function createInline() {
  const callsign = query.value.trim()
  if (!callsign) return
  try {
    const { data } = await createRecipient({ callsign })
    emit('created', data)         // parent appends to its recipients list
    emit('update:modelValue', data.id)
    query.value = data.callsign
    open.value = false
  } catch (e) {
    alert(e?.response?.data?.detail || 'Помилка створення')
  }
}

function onEnter() {
  // If a recipient is highlighted → pick it; else if canCreate → create
  if (filtered.value.length > 0 && highlighted.value < filtered.value.length) {
    select(filtered.value[highlighted.value])
  } else if (canCreate.value) {
    createInline()
  }
}

function moveDown() {
  const max = filtered.value.length + (canCreate.value ? 1 : 0) - 1
  highlighted.value = Math.min(highlighted.value + 1, max)
}
function moveUp()   { highlighted.value = Math.max(highlighted.value - 1, 0) }

watch(filtered, () => { highlighted.value = 0; if (open.value) nextTick(updatePosition) })
watch(open,     v => { if (v) nextTick(updatePosition) })

onMounted(() => {
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
})

// Clear: if user empties the input → unset selection
watch(query, (v) => {
  if (!v && props.modelValue != null) emit('update:modelValue', null)
})
</script>

<style scoped>
.rc-wrap { position: relative; }
.rc-input {
  width: 100%; border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 7px 10px; font-size: 13.5px; font-family: inherit; background: var(--surface);
  color: var(--text); outline: none;
}
.rc-input:focus { border-color: var(--accent); }
</style>

<style>
.rc-dropdown {
  position: fixed; z-index: 10000;
  background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .18);
  max-height: 320px; overflow-y: auto;
  font-family: inherit;
}
.rc-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; cursor: pointer; font-size: 13px;
  color: #1e293b; border-bottom: 1px solid #f1f5f9;
}
.rc-item:last-child { border-bottom: none; }
.rc-item:hover, .rc-item.active { background: #eff6ff; }
.rc-callsign { font-weight: 500; }
.rc-inactive { color: #94a3b8; font-size: 11px; font-style: italic; }
.rc-create { color: #2563eb; font-weight: 600; }
.rc-create:hover, .rc-create.active { background: #dbeafe; }
.rc-empty { padding: 10px 12px; color: #94a3b8; font-size: 12px; font-style: italic; }
</style>
