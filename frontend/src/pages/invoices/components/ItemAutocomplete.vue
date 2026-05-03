<template>
  <div class="autocomplete-wrap">
    <input
      v-model="query"
      class="cell-input"
      :placeholder="modelValue || 'Назва майна...'"
      @focus="open = true"
      @blur="onBlur"
      @input="open = true"
      @keydown.esc="open = false"
      @keydown.enter.prevent="selectFirst"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
    />
    <div v-if="open && filtered.length" class="dropdown">
      <div
        v-for="(item, i) in filtered"
        :key="item.id"
        class="dropdown-item"
        :class="{ active: i === highlighted }"
        @mousedown.prevent="select(item)"
      >
        <span class="item-name">{{ item.name }}</span>
        <span class="item-meta">{{ item.number }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: String,
  items: Array,
})
const emit = defineEmits(['update:modelValue', 'select'])

const query = ref(props.modelValue || '')
const open = ref(false)
const highlighted = ref(0)

watch(() => props.modelValue, v => { if (v !== query.value) query.value = v || '' })

const filtered = computed(() => {
  if (!query.value || query.value.length < 2) return []
  const q = query.value.toLowerCase()
  return (props.items || [])
    .filter(it => (it.name || '').toLowerCase().includes(q) || (it.number || '').toLowerCase().includes(q))
    .slice(0, 10)
})

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

function moveDown() {
  highlighted.value = Math.min(highlighted.value + 1, filtered.value.length - 1)
}
function moveUp() {
  highlighted.value = Math.max(highlighted.value - 1, 0)
}

watch(filtered, () => { highlighted.value = 0 })
</script>

<style scoped>
.autocomplete-wrap { position: relative; }
.cell-input {
  width: 100%; border: none; background: transparent; padding: 4px;
  font-size: 13px; outline: none;
}
.cell-input:focus { background: #eff6ff; border-radius: 3px; }
.dropdown {
  position: absolute; top: 100%; left: 0; z-index: 200;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,.12); min-width: 280px; max-height: 220px; overflow-y: auto;
}
.dropdown-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; font-size: 13px;
}
.dropdown-item:hover, .dropdown-item.active { background: #eff6ff; }
.item-name { flex: 1; }
.item-meta { color: #94a3b8; font-size: 11px; margin-left: 8px; }
</style>
