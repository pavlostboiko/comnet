<template>
  <div class="page-wrap">
    <div class="tile">
      <div class="tile-header">
        <h2>Документи</h2>
        <div class="header-actions">
          <select v-model="typeFilter" class="type-filter">
            <option value="">Всі типи</option>
            <option value="надходження">Надходження</option>
            <option value="переміщення">Переміщення</option>
            <option value="накладна_25">Накладна (Дод. 25)</option>
          </select>
          <div class="create-menu" ref="menuRef">
            <button class="btn-primary" @click="menuOpen = !menuOpen">+ Новий документ ▾</button>
            <div v-if="menuOpen" class="dropdown-menu">
              <div class="dropdown-item" @click="createNew('надходження')">Надходження</div>
              <div class="dropdown-item" @click="createNew('переміщення')">Переміщення</div>
              <div class="dropdown-item" @click="createNew('накладна_25')">Накладна (Дод. 25)</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="empty-state">Завантаження...</div>
      <div v-else-if="!filtered.length" class="empty-state">Документів немає</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Тип</th>
            <th>№</th>
            <th>Дата</th>
            <th>Звідки</th>
            <th>Куди</th>
            <th>Позицій</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in filtered" :key="doc.id" @click="open(doc)" class="clickable-row">
            <td><span class="type-badge" :class="typeClass(doc.doc_type)">{{ typeLabel(doc.doc_type) }}</span></td>
            <td>{{ doc.doc_number || '—' }}</td>
            <td>{{ doc.doc_date || '—' }}</td>
            <td class="unit-cell">{{ doc.from_unit || '—' }}</td>
            <td class="unit-cell">{{ doc.to_unit || '—' }}</td>
            <td class="center">{{ doc.items_count }}</td>
            <td><span class="status-badge" :class="doc.status">{{ statusLabel(doc.status) }}</span></td>
            <td class="actions-cell" @click.stop>
              <button class="btn-sm btn-danger" @click="remove(doc)" :disabled="doc.status !== 'draft'">Видалити</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getDocuments, deleteDocument, createDocument } from '../../api/documents'

const router = useRouter()
const docs = ref([])
const loading = ref(false)
const typeFilter = ref('')
const menuOpen = ref(false)
const menuRef = ref(null)

const filtered = computed(() =>
  typeFilter.value ? docs.value.filter(d => d.doc_type === typeFilter.value) : docs.value
)

function typeLabel(t) {
  return { надходження: 'Надходження', переміщення: 'Переміщення', накладна_25: 'Накладна' }[t] || t
}
function typeClass(t) {
  return { надходження: 'incoming', переміщення: 'transfer', накладна_25: 'invoice' }[t] || ''
}
function statusLabel(s) {
  return { draft: 'Чернетка', signed: 'Підписано', receiver_signed: 'Підписано отримувачем' }[s] || s
}

async function load() {
  loading.value = true
  try { docs.value = await getDocuments() }
  finally { loading.value = false }
}

function open(doc) {
  router.push(`/documents/${doc.id}`)
}

async function createNew(docType) {
  menuOpen.value = false
  const doc = await createDocument({ doc_type: docType, items: [] })
  router.push(`/documents/${doc.id}`)
}

async function remove(doc) {
  if (!confirm(`Видалити документ № ${doc.doc_number || doc.id}?`)) return
  await deleteDocument(doc.id)
  docs.value = docs.value.filter(d => d.id !== doc.id)
}

function onClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}

onMounted(() => { load(); document.addEventListener('click', onClickOutside) })
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.page-wrap { padding: 16px; }
.tile { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.tile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.tile-header h2 { margin: 0; font-size: 18px; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.type-filter {
  border: 1px solid #e2e8f0; border-radius: 6px; padding: 7px 10px;
  font-size: 14px; outline: none; background: #fff;
}
.create-menu { position: relative; }
.btn-primary {
  background: #2563eb; color: #fff; border: none; border-radius: 6px;
  padding: 8px 14px; cursor: pointer; font-size: 14px;
}
.btn-primary:hover { background: #1d4ed8; }
.dropdown-menu {
  position: absolute; right: 0; top: calc(100% + 4px); z-index: 100;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,.12); min-width: 180px; overflow: hidden;
}
.dropdown-item { padding: 10px 14px; cursor: pointer; font-size: 14px; }
.dropdown-item:hover { background: #f1f5f9; }
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { background: #f8fafc; padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 12px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f8fafc; }
.center { text-align: center; }
.unit-cell { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions-cell { white-space: nowrap; }
.btn-sm {
  padding: 4px 10px; border-radius: 4px; font-size: 13px; cursor: pointer;
  border: 1px solid #fca5a5; color: #dc2626; background: #fff;
}
.btn-sm:hover:not(:disabled) { background: #fef2f2; }
.btn-sm:disabled { opacity: 0.4; cursor: default; }
.type-badge {
  display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;
}
.type-badge.incoming { background: #d1fae5; color: #065f46; }
.type-badge.transfer { background: #dbeafe; color: #1e40af; }
.type-badge.invoice  { background: #fef3c7; color: #92400e; }
.status-badge {
  display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px;
}
.status-badge.draft  { background: #f1f5f9; color: #475569; }
.status-badge.signed { background: #d1fae5; color: #065f46; font-weight: 600; }
.status-badge.receiver_signed { background: #ede9fe; color: #5b21b6; font-weight: 600; }
.empty-state { color: #94a3b8; padding: 40px; text-align: center; }
</style>
