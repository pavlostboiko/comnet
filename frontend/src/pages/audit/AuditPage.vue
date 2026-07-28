<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Журнал змін</span>
          <div class="filters">
            <select class="fi" v-model="filters.entity_type" @change="reload">
              <option value="">Усі сутності</option>
              <option v-for="t in meta.entity_types" :key="t" :value="t">{{ entLabel(t) }}</option>
            </select>
            <select class="fi" v-model="filters.action" @change="reload">
              <option value="">Усі дії</option>
              <option v-for="a in meta.actions" :key="a" :value="a">{{ actLabel(a) }}</option>
            </select>
            <label class="dt">з <input class="fi" type="date" v-model="filters.date_from" @change="reload" /></label>
            <label class="dt">по <input class="fi" type="date" v-model="filters.date_to" @change="reload" /></label>
          </div>
        </div>

        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="col-ts">Час</th><th class="col-u">Користувач</th>
              <th class="col-act">Дія</th><th>Сутність</th>
              <th class="col-id">ID</th><th>Зміни</th>
            </tr></thead>
            <tbody>
              <tr v-if="loading"><td colspan="6" class="empty">Завантаження…</td></tr>
              <tr v-else-if="!items.length"><td colspan="6" class="empty">Немає записів</td></tr>
              <template v-for="a in items" :key="a.id">
                <tr class="row" @click="toggle(a.id)">
                  <td class="td-mono td-dim">{{ fmtTs(a.ts) }}</td>
                  <td>{{ a.username || '—' }}</td>
                  <td><span class="act" :class="`act-${a.action}`">{{ actLabel(a.action) }}</span></td>
                  <td>{{ entLabel(a.entity_type) }}</td>
                  <td class="td-mono td-dim">{{ a.entity_id ?? '—' }}</td>
                  <td class="td-dim">{{ summary(a) }}</td>
                </tr>
                <tr v-if="open.has(a.id)" class="detail-row">
                  <td colspan="6">
                    <table class="diff">
                      <tr v-for="(pair, field) in a.changes" :key="field">
                        <td class="diff-field">{{ field }}</td>
                        <td class="diff-old">{{ fmtVal(pair[0]) }}</td>
                        <td class="diff-arrow">→</td>
                        <td class="diff-new">{{ fmtVal(pair[1]) }}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div class="t-foot">
          <span>Показано <b>{{ items.length }}</b> з <b>{{ total }}</b></span>
          <button v-if="items.length < total" class="btn-more" :disabled="loading" @click="loadMore">Ще</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getAudit, getAuditMeta } from '../../api/audit.js'

const ENT = {
  Nomenclature: 'Номенклатура', Instance: 'Екземпляр', CustodyMovement: 'Рух',
  Assignment: 'Видача', CustodyDocument: 'Документ', Service: 'Служба',
  Unit: 'Підрозділ', Group: 'Група', Warehouse: 'Склад', Person: 'Особа',
  Mvo: 'МВО', User: 'Користувач',
}
const ACT = { create: 'Створено', update: 'Змінено', delete: 'Видалено' }
const entLabel = (t) => ENT[t] || t
const actLabel = (a) => ACT[a] || a

const LIMIT = 100
const items = ref([])
const total = ref(0)
const loading = ref(true)
const meta = reactive({ entity_types: [], actions: [] })
const open = reactive(new Set())
const filters = reactive({ entity_type: '', action: '', date_from: '', date_to: '' })

function fmtTs(s) { return s ? s.replace('T', ' ').slice(0, 19) : '—' }
function fmtVal(v) {
  if (v === null || v === undefined) return '∅'
  return String(v)
}
function summary(a) {
  const keys = Object.keys(a.changes || {})
  if (a.action === 'update') return keys.join(', ')
  return `${keys.length} полів`
}
function toggle(id) { open.has(id) ? open.delete(id) : open.add(id) }

function params(offset = 0) {
  const p = { limit: LIMIT, offset }
  if (filters.entity_type) p.entity_type = filters.entity_type
  if (filters.action) p.action = filters.action
  if (filters.date_from) p.date_from = filters.date_from
  if (filters.date_to) p.date_to = `${filters.date_to}T23:59:59`
  return p
}
async function reload() {
  loading.value = true
  open.clear()
  const { data } = await getAudit(params(0))
  items.value = data.items
  total.value = data.total
  loading.value = false
}
async function loadMore() {
  loading.value = true
  const { data } = await getAudit(params(items.value.length))
  items.value.push(...data.items)
  total.value = data.total
  loading.value = false
}

onMounted(async () => {
  meta.entity_types = (await getAuditMeta()).data.entity_types
  meta.actions = (await getAuditMeta()).data.actions
  await reload()
})
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
.tile-title { font-weight:700; font-size:15px; }
.filters { display:flex; gap:8px; align-items:center; margin-left:auto; flex-wrap:wrap; }
.fi { border:1px solid var(--border); border-radius:var(--radius-sm); padding:5px 8px; font-family:inherit; font-size:13px; color:var(--text); background:var(--surface); }
.dt { display:flex; align-items:center; gap:4px; font-size:12px; color:var(--text-light); }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:8px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.col-ts { width:170px; } .col-u { width:130px; } .col-act { width:110px; } .col-id { width:70px; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; } .td-dim { color:var(--text-light); }
.row { cursor:pointer; } .row:hover { background:var(--bg); }
.act { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.act-create { background:#dcfce7; color:#166534; }
.act-update { background:#e0e7ff; color:#3730a3; }
.act-delete { background:#fee2e2; color:#991b1b; }
.detail-row td { background:var(--bg); padding:6px 20px 12px; }
.diff { width:auto; }
.diff td { border:none; padding:2px 10px 2px 0; font-size:12.5px; }
.diff-field { font-weight:600; color:var(--text-mid); font-family:'DM Mono',monospace; }
.diff-old { color:#991b1b; } .diff-arrow { color:var(--text-light); } .diff-new { color:#166534; }
.empty { text-align:center; padding:24px; color:var(--text-light); font-style:italic; }
.t-foot { padding:12px 20px; display:flex; align-items:center; gap:16px; font-size:12.5px; color:var(--text-light); }
.btn-more { border:1px solid var(--border); background:var(--surface); border-radius:var(--radius-sm); padding:5px 14px; cursor:pointer; font-family:inherit; font-size:13px; }
</style>
