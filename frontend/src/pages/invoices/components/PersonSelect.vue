<template>
  <select :value="modelValue" @change="$emit('update:modelValue', Number($event.target.value) || null)" class="person-select">
    <option value="">— не вказано —</option>
    <option v-for="p in persons" :key="p.id" :value="p.id">
      {{ label(p) }}
    </option>
  </select>
</template>

<script setup>
defineProps({ modelValue: [Number, null], persons: Array })
defineEmits(['update:modelValue'])

function label(p) {
  const parts = []
  if (p.rank) parts.push(p.rank)
  parts.push([p.last_name, p.first_name ? p.first_name[0] + '.' : '', p.patronymic ? p.patronymic[0] + '.' : ''].filter(Boolean).join(' '))
  if (p.position) parts.push(`(${p.position})`)
  return parts.join(' ')
}
</script>

<style scoped>
.person-select {
  border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 7px 10px; font-size: 13px; outline: none; width: 100%;
}
.person-select:focus { border-color: #2563eb; }
</style>
