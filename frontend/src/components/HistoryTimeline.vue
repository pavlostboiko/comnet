<template>
  <table class="h-table">
    <thead><tr>
      <th class="hc-date">Дата</th><th class="hc-ev">Подія</th><th>Деталі</th><th class="hc-num">К-сть</th>
    </tr></thead>
    <tbody>
      <tr v-if="!events.length"><td colspan="4" class="empty">Історія порожня</td></tr>
      <tr v-for="(e, i) in events" :key="i">
        <td class="mono dim">{{ e.date || '—' }}</td>
        <td><span class="chip" :class="chipClass(e)">{{ label(e) }}</span></td>
        <td>
          {{ details(e) }}
          <span v-if="e.serial_no" class="mono dim"> · {{ e.serial_no }}</span>
          <span v-if="e.doc_number" class="dim"> · накл. {{ e.doc_number }}</span>
        </td>
        <td class="num">{{ fmtQty(e.qty) }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
defineProps({ events: { type: Array, default: () => [] } })

const MOVE = { receipt: 'надходження', transfer: 'переміщення', writeoff: 'списання' }
function label(e) {
  if (e.kind === 'issued') return 'видано'
  if (e.kind === 'returned') return 'повернено'
  return MOVE[e.type] || e.type
}
function chipClass(e) {
  if (e.kind === 'issued') return 'c-issue'
  if (e.kind === 'returned') return 'c-return'
  return `c-${e.type}`
}
function details(e) {
  if (e.kind === 'issued') return `на особу: ${e.person || '—'} (${e.warehouse || '—'})`
  if (e.kind === 'returned') return `від особи: ${e.person || '—'} → ${e.warehouse || '—'}`
  return `${e.from_warehouse || 'ззовні'} → ${e.to_warehouse || '—'}`
}
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}
</script>

<style scoped>
.h-table { width:100%; border-collapse:collapse; }
.h-table th, .h-table td { padding:8px 12px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
.h-table th { color:var(--text-light); font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.hc-date { width:110px; } .hc-ev { width:120px; } .hc-num { width:90px; text-align:right; }
.num { text-align:right; font-family:'DM Mono',monospace; }
.mono { font-family:'DM Mono',monospace; font-size:12px; } .dim { color:var(--text-light); }
.empty { text-align:center; padding:24px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.c-receipt { background:#dcfce7; color:#166534; } .c-transfer { background:#e0e7ff; color:#3730a3; }
.c-writeoff { background:#fee2e2; color:#991b1b; }
.c-issue { background:#fef3c7; color:#854d0e; } .c-return { background:#dcfce7; color:#166534; }
</style>
