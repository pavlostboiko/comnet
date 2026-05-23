<template>
  <div class="autocomplete-wrap">
    <input
      ref="inputRef"
      v-model="query"
      class="cell-input"
      :placeholder="modelValue || 'Назва майна...'"
      @focus="onFocus"
      @blur="onBlur"
      @input="open = true"
      @keydown.esc="open = false"
      @keydown.enter.prevent="selectFirst"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
    />
    <Teleport to="body">
      <div
        v-if="open && filtered.length"
        class="ac-dropdown"
        :style="dropdownStyle"
      >
        <div
          v-for="(item, i) in filtered"
          :key="item.id"
          class="ac-item"
          :class="{ active: i === highlighted }"
          @mousedown.prevent="select(item)"
        >
          <span class="ac-name">{{ item.name }}</span>
          <span class="ac-meta">{{ item.number }}</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: String,
  items: Array,
})
const emit = defineEmits(['update:modelValue', 'select'])

const inputRef    = ref(null)
const query       = ref(props.modelValue || '')
const open        = ref(false)
const highlighted = ref(0)
const dropdownStyle = ref({})

watch(() => props.modelValue, v => { if (v !== query.value) query.value = v || '' })

const filtered = computed(() => {
  const list = props.items || []
  const q = (query.value || '').trim().toLowerCase()
  if (!q) return list
  return list.filter(it =>
       (it.name   || '').toLowerCase().includes(q)
    || (it.number || '').toLowerCase().includes(q),
  )
})

function updatePosition() {
  if (!inputRef.value) return
  const rect = inputRef.value.getBoundingClientRect()
  const minWidth = Math.max(rect.width, 360)
  dropdownStyle.value = {
    top:    `${rect.bottom + 2}px`,
    left:   `${rect.left}px`,
    width:  `${minWidth}px`,
  }
}

function onFocus() {
  open.value = true
  nextTick(updatePosition)
}

function select(item) {
  query.value = item.name || ''
  emit('update:modelValue', item.name || '')
  emit('select', item)
  open.value = false
}

function selectFirst() {
  if (filtered.value.length) select(filtered.value[highlighted.value] || filtered.value[0])
  else { emit('update:modelValue', query.value); open.value = false }
}

function onBlur() {
  setTimeout(() => {
    open.value = false
    emit('update:modelValue', query.value)
  }, 150)
}

function moveDown() { highlighted.value = Math.min(highlighted.value + 1, filtered.value.length - 1) }
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
</script>

<style scoped>
.autocomplete-wrap { position: relative; }
.cell-input {
  width: 100%; border: none; background: transparent; padding: 4px;
  font-size: 13px; outline: none;
}
.cell-input:focus { background: #eff6ff; border-radius: 3px; }
</style>

<!-- Teleported dropdown lives in <body>, so styles cannot be scoped. -->
<style>
.ac-dropdown {
  position: fixed; z-index: 10000;
  background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .18);
  max-height: 360px; overflow-y: auto;
  font-family: inherit;
}
.ac-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; cursor: pointer; font-size: 13px;
  color: #1e293b;
  border-bottom: 1px solid #f1f5f9;
}
.ac-item:last-child { border-bottom: none; }
.ac-item:hover, .ac-item.active { background: #eff6ff; }
.ac-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px; }
.ac-meta { color: #94a3b8; font-size: 11.5px; font-family: 'DM Mono', monospace; flex-shrink: 0; }
</style>
