<template>
  <div class="nakl-wrap">
    <!-- PAGE 1 -->
    <div class="nakl-page">
      <!-- Unit header -->
      <table class="header-table">
        <tr>
          <td class="unit-name" rowspan="2">{{ unitName }}</td>
          <td class="validity-cell">Термін дії накладної: {{ invoice.validity_date || '_________' }}</td>
        </tr>
        <tr>
          <td class="edrpou-cell">ЄДРПОУ: {{ edrpou }}</td>
        </tr>
      </table>

      <h1 class="doc-title">НАКЛАДНА (ВИМОГА) № {{ invoice.doc_number || '___' }}</h1>

      <div class="header-info">
        <div class="info-row">
          <span>Місце складання: <b>{{ invoice.composed_location || locationFallback }}</b></span>
          <span>« ___ » ____________ {{ year }} р.</span>
        </div>
        <div class="info-row">
          <span>Операцій від « ___ » ____________ {{ year }} р.</span>
          <span></span>
        </div>
        <div class="info-row">
          <span>Служба: <b>{{ invoice.service || '____________' }}</b></span>
          <span>Вид операції: <b>{{ invoice.op_type_text || '____________' }}</b></span>
        </div>
        <div class="info-row">
          <span>Підстава: <b>{{ invoice.basis || '____________' }}</b></span>
        </div>
        <div class="info-row">
          <span>Звідки: <b>{{ invoice.from_unit || '____________' }}</b></span>
          <span>Куди: <b>{{ invoice.to_unit || '____________' }}</b></span>
        </div>
        <div class="info-row">
          <span>Передає: <b>{{ personLabel(invoice.sender_id) }}</b></span>
          <span>Приймає: <b>{{ personLabel(invoice.receiver_id) }}</b></span>
        </div>
        <div v-if="invoice.responsible_recipient" class="info-row">
          <span>Відповідальна особа-отримувач: <b>{{ invoice.responsible_recipient }}</b></span>
        </div>
      </div>

      <!-- Items table -->
      <table class="items-table">
        <thead>
          <tr>
            <th rowspan="2" style="width:4%">№<br>з/п</th>
            <th rowspan="2" style="width:22%">Назва майна або однорідна група</th>
            <th rowspan="2" style="width:11%">Код номен-клатури</th>
            <th rowspan="2" style="width:7%">Одиниця виміру</th>
            <th rowspan="2" style="width:8%">Кате-горія (сорт)</th>
            <th rowspan="2" style="width:10%">Вартість за одиницю (грн.)</th>
            <th colspan="2" style="width:16%">Кількість</th>
            <th rowspan="2" style="width:10%">Сума (грн.)</th>
            <th rowspan="2" style="width:12%">Примітка</th>
          </tr>
          <tr>
            <th style="width:8%">відправлено</th>
            <th style="width:8%">прийнято</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, idx) in sortedItems" :key="idx">
            <td class="center">{{ idx + 1 }}</td>
            <td>{{ it.item_name }}</td>
            <td class="center">{{ it.nomenclature_code }}</td>
            <td class="center">{{ it.unit_of_measure }}</td>
            <td class="center">{{ it.category }}</td>
            <td class="right">{{ fmt(it.price) }}</td>
            <td class="center">{{ it.quantity }}</td>
            <td class="center">{{ it.qty_received }}</td>
            <td class="right">{{ fmt(it.amount) }}</td>
            <td>{{ it.notes }}</td>
          </tr>
          <!-- filler rows to minimum height -->
          <tr v-for="i in Math.max(0, 8 - sortedItems.length)" :key="`fill-${i}`" class="filler-row">
            <td></td><td></td><td></td><td></td><td></td>
            <td></td><td></td><td></td><td></td><td></td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="6" class="right"><b>Разом:</b></td>
            <td class="center"><b>{{ totalQty }}</b></td>
            <td></td>
            <td class="right"><b>{{ fmt(totalAmount) }}</b></td>
            <td></td>
          </tr>
        </tfoot>
      </table>

      <!-- Footer -->
      <div class="footer-block">
        <div class="sign-row">
          <span class="sign-label">Керівник:</span>
          <span class="sign-pos">{{ personPosition(invoice.commander_id) }}</span>
          <span class="sign-line">________________</span>
          <span class="sign-name">{{ personShortName(invoice.commander_id) }}</span>
        </div>
        <div class="total-words">
          Всього передано <b>{{ invoice.total_qty_words || '___' }}</b> одиниць,
          на суму <b>{{ invoice.total_amount_words || '___' }}</b> гривень.
        </div>
      </div>
    </div>

    <!-- PAGE 2 -->
    <div class="nakl-page page-break">
      <h2 class="page2-title">ЗВОРОТНІЙ БІК</h2>

      <div class="sign-block">
        <div class="sign-row">
          <span class="sign-label">МВО здав:</span>
          <span class="sign-pos">{{ personPosition(invoice.mvo_from_id) }}</span>
          <span class="sign-line">________________</span>
          <span class="sign-name">{{ personShortName(invoice.mvo_from_id) }}</span>
        </div>

        <div class="sign-row" style="margin-top: 32px">
          <span class="sign-label">МВО прийняв:</span>
          <span class="sign-pos">{{ personPosition(invoice.mvo_to_id) }}</span>
          <span class="sign-line">________________</span>
          <span class="sign-name">{{ personShortName(invoice.mvo_to_id) }}</span>
        </div>
      </div>

      <div class="fin-section">
        <h3>Фінансово-економічна відмітка</h3>
        <table class="fin-table">
          <thead>
            <tr>
              <th>Дебет</th>
              <th>Кредит</th>
              <th>Сума (грн.)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in 3" :key="i"><td>&nbsp;</td><td></td><td></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  invoice: Object,
  unitSettings: Object,
  persons: Array,
})

const unitName = computed(() => props.unitSettings?.name || '')
const edrpou = computed(() => props.unitSettings?.edrpou || '')
const locationFallback = computed(() => props.unitSettings?.location || '')
const year = computed(() => new Date().getFullYear())

const sortedItems = computed(() =>
  [...(props.invoice?.items || [])].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
)

function findPerson(id) {
  if (!id) return null
  return (props.persons || []).find(p => p.id === id) || null
}

function personLabel(id) {
  const p = findPerson(id)
  if (!p) return '____________'
  const parts = []
  if (p.position) parts.push(p.position)
  if (p.rank) parts.push(p.rank)
  parts.push([p.last_name, p.first_name, p.patronymic].filter(Boolean).join(' '))
  return parts.join(' ')
}

function personPosition(id) {
  const p = findPerson(id)
  return p?.position || ''
}

function personShortName(id) {
  const p = findPerson(id)
  if (!p) return ''
  return [
    p.last_name || '',
    p.first_name ? p.first_name[0] + '.' : '',
    p.patronymic ? p.patronymic[0] + '.' : '',
  ].filter(Boolean).join(' ')
}

const totalQty = computed(() =>
  sortedItems.value.reduce((s, it) => s + (Number(it.quantity) || 0), 0)
)
const totalAmount = computed(() =>
  sortedItems.value.reduce((s, it) => s + (Number(it.amount) || 0), 0)
)

function fmt(v) {
  if (v == null || v === '') return ''
  return Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.nakl-wrap { font-family: 'Times New Roman', serif; font-size: 11pt; color: #000; }
.nakl-page { padding: 15mm 15mm 10mm; max-width: 210mm; margin: 0 auto; }
.page-break { page-break-before: always; }

.header-table { width: 100%; border-collapse: collapse; margin-bottom: 6pt; }
.header-table td { padding: 2px 4px; }
.unit-name { font-weight: bold; width: 55%; font-size: 10pt; border-bottom: 1px solid #000; }
.validity-cell, .edrpou-cell { font-size: 10pt; text-align: right; }

.doc-title { text-align: center; font-size: 14pt; font-weight: bold; margin: 8pt 0 6pt; text-transform: uppercase; }

.header-info { margin-bottom: 6pt; }
.info-row { display: flex; justify-content: space-between; margin-bottom: 3pt; font-size: 10pt; }
.info-row span { flex: 1; }
.info-row span:last-child:not(:first-child) { text-align: right; }

.items-table {
  width: 100%; border-collapse: collapse; margin-bottom: 6pt; font-size: 9pt;
}
.items-table th, .items-table td {
  border: 1px solid #000; padding: 3px 4px; vertical-align: middle;
}
.items-table th { text-align: center; font-size: 8.5pt; background: #f0f0f0; }
.filler-row td { height: 18pt; }
.center { text-align: center; }
.right { text-align: right; }

.footer-block { margin-top: 8pt; }
.sign-row { display: flex; align-items: baseline; gap: 6pt; margin-bottom: 4pt; }
.sign-label { font-weight: bold; min-width: 80pt; }
.sign-pos { flex: 1; border-bottom: 1px solid #000; }
.sign-line { min-width: 80pt; border-bottom: 1px solid #000; text-align: center; }
.sign-name { min-width: 100pt; border-bottom: 1px solid #000; }
.total-words { margin-top: 10pt; font-size: 10pt; }

.page2-title { text-align: center; margin-bottom: 16pt; }
.sign-block { margin-bottom: 20pt; }
.fin-section h3 { font-size: 11pt; margin-bottom: 8pt; }
.fin-table { width: 50%; border-collapse: collapse; font-size: 10pt; }
.fin-table th, .fin-table td { border: 1px solid #000; padding: 4px 8px; text-align: center; }
.fin-table th { background: #f0f0f0; }

@media print {
  .nakl-page { padding: 10mm; }
  .page-break { page-break-before: always; }
}
</style>
