<template>
  <div class="page-wrap">
    <div class="tile">
      <div class="tile-header">
        <h2>Накладні (вимоги)</h2>
        <router-link to="/invoices/new" class="btn-primary">+ Нова накладна</router-link>
      </div>

      <div v-if="loading" class="empty-state">Завантаження...</div>
      <div v-else-if="!invoices.length" class="empty-state">Накладних ще немає</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>№</th>
            <th>Дата</th>
            <th>Звідки</th>
            <th>Куди</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inv in invoices" :key="inv.id">
            <td>{{ inv.doc_number || '—' }}</td>
            <td>{{ inv.doc_date || '—' }}</td>
            <td>{{ inv.from_unit || '—' }}</td>
            <td>{{ inv.to_unit || '—' }}</td>
            <td><span class="status-badge" :class="inv.status">{{ statusLabel(inv.status) }}</span></td>
            <td class="actions-cell">
              <router-link :to="`/invoices/${inv.id}`" class="btn-sm">Відкрити</router-link>
              <button class="btn-sm btn-danger" @click="remove(inv)">Видалити</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getInvoices, deleteInvoice } from '../../api/invoices'

const invoices = ref([])
const loading = ref(false)

function statusLabel(s) {
  return s === 'draft' ? 'Чернетка' : s === 'final' ? 'Фінальна' : s
}

async function load() {
  loading.value = true
  try { invoices.value = await getInvoices() }
  finally { loading.value = false }
}

async function remove(inv) {
  if (!confirm(`Видалити накладну № ${inv.doc_number || inv.id}?`)) return
  await deleteInvoice(inv.id)
  invoices.value = invoices.value.filter(i => i.id !== inv.id)
}

onMounted(load)
</script>

<style scoped>
.page-wrap { padding: 16px; }
.tile { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.tile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.tile-header h2 { margin: 0; font-size: 18px; }
.btn-primary {
  background: #2563eb; color: #fff; border: none; border-radius: 6px;
  padding: 8px 16px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block;
}
.btn-primary:hover { background: #1d4ed8; }
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { background: #f8fafc; padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.data-table tr:hover td { background: #f8fafc; }
.actions-cell { display: flex; gap: 6px; }
.btn-sm {
  padding: 4px 10px; border-radius: 4px; font-size: 13px; cursor: pointer;
  border: 1px solid #cbd5e1; background: #fff; text-decoration: none; color: #334155;
}
.btn-sm:hover { background: #f1f5f9; }
.btn-danger { border-color: #fca5a5; color: #dc2626; }
.btn-danger:hover { background: #fef2f2; }
.status-badge {
  display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px;
}
.status-badge.draft { background: #fef3c7; color: #92400e; }
.status-badge.final { background: #d1fae5; color: #065f46; }
.empty-state { color: #94a3b8; padding: 40px; text-align: center; }
</style>
