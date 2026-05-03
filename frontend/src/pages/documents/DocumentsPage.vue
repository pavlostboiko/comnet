<template>
  <div class="page-wrap">
    <TopBar>
      <template #actions>
        <div class="create-menu" ref="menuRef">
          <button class="btn-primary" @click="menuOpen = !menuOpen">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Новий документ
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <div v-if="menuOpen" class="dropdown-menu">
            <div class="dropdown-item" @click="createNew('надходження')">Надходження</div>
            <div class="dropdown-item" @click="createNew('переміщення')">Переміщення</div>
            <div class="dropdown-item" @click="createNew('накладна_25')">Накладна (Дод. 25)</div>
          </div>
        </div>
      </template>
    </TopBar>

    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Документи</span>
          <span class="tile-count">{{ filtered.length }}</span>
          <div class="tile-tabs">
            <button
              v-for="opt in typeOptions" :key="opt.value"
              class="tt-btn" :class="{ on: typeFilter === opt.value }"
              @click="typeFilter = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div v-if="loading" class="empty-state">Завантаження…</div>
        <div v-else-if="!filtered.length" class="empty-state">Документів немає</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Тип</th>
                <th>№</th>
                <th>Дата</th>
                <th>Звідки</th>
                <th>Куди</th>
                <th style="text-align:center">Позицій</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in filtered" :key="doc.id" @click="open(doc)">
                <td>
                  <span class="type-badge" :class="typeClass(doc.doc_type)">{{ typeLabel(doc.doc_type) }}</span>
                  <div v-if="doc.doc_type_label && doc.doc_type_label !== doc.doc_type" class="doc-type-label">{{ doc.doc_type_label }}</div>
                </td>
                <td class="td-mono">{{ doc.doc_number || '—' }}</td>
                <td class="td-mono">{{ doc.doc_date || '—' }}</td>
                <td class="td-unit">{{ doc.from_unit || '—' }}</td>
                <td class="td-unit">{{ doc.to_unit || '—' }}</td>
                <td class="td-center">{{ doc.items_count }}</td>
                <td><span class="status-badge" :class="doc.status">{{ statusLabel(doc.status) }}</span></td>
                <td class="td-acts" @click.stop>
                  <div class="acts">
                    <button class="act e" title="Відкрити" @click="open(doc)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                        <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button class="act d" title="Видалити" @click="remove(doc)" :disabled="doc.status !== 'draft'">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="t-foot">{{ docs.length }} документів</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getDocuments, deleteDocument, createDocument } from '../../api/documents'
import TopBar from '../../components/TopBar.vue'

const router  = useRouter()
const docs    = ref([])
const loading = ref(false)
const typeFilter = ref('')
const menuOpen   = ref(false)
const menuRef    = ref(null)

const typeOptions = [
  { value: '',            label: 'Всі' },
  { value: 'надходження', label: 'Надходження' },
  { value: 'переміщення', label: 'Переміщення' },
  { value: 'накладна_25', label: 'Накладна' },
]

const filtered = computed(() => {
  const list = typeFilter.value
    ? docs.value.filter(d => d.doc_type === typeFilter.value)
    : docs.value
  return [...list].sort((a, b) => {
    const da = a.doc_date || ''
    const db = b.doc_date || ''
    return da < db ? 1 : da > db ? -1 : b.id - a.id
  })
})

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

function open(doc) { router.push(`/documents/${doc.id}`) }

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
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.content-scroll::-webkit-scrollbar { width:6px; }
.content-scroll::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

/* TopBar slot */
.btn-primary { display:flex; align-items:center; gap:5px; padding:8px 14px; background:var(--accent); border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; font-weight:600; color:white; cursor:pointer; transition:all 0.15s; white-space:nowrap; }
.btn-primary:hover { background:var(--accent-dark); }
.create-menu { position:relative; }
.dropdown-menu { position:absolute; right:0; top:calc(100% + 6px); z-index:200; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow-xl); min-width:180px; overflow:hidden; }
.dropdown-item { padding:10px 14px; cursor:pointer; font-size:13.5px; color:var(--text-mid); transition:background 0.1s; }
.dropdown-item:hover { background:var(--bg); color:var(--text); }

/* Tile */
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden; }
.tile-header { padding:12px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); }
.tile-title { font-size:15px; font-weight:700; }
.tile-count { font-family:'DM Mono',monospace; font-size:11.5px; font-weight:500; background:var(--accent-light); color:var(--accent); padding:2px 8px; border-radius:var(--radius-sm); }
.tile-tabs { display:flex; gap:2px; background:var(--bg); padding:3px; border-radius:var(--radius-sm); border:1px solid var(--border-light); margin-left:auto; }
.tt-btn { padding:5px 13px; border:none; background:transparent; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; transition:all 0.12s; }
.tt-btn:hover { color:var(--text-mid); }
.tt-btn.on { background:var(--surface); color:var(--text); box-shadow:0 1px 2px rgba(0,0,0,0.06); font-weight:600; }

/* Table */
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; }
thead tr { background:var(--bg); }
th { padding:9px 12px; text-align:left; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-light); border-bottom:1px solid var(--border); white-space:nowrap; }
th:first-child { padding-left:20px; }
th:last-child { padding-right:20px; width:80px; }
tbody tr { border-bottom:1px solid var(--border-light); transition:background 0.1s; cursor:pointer; }
tbody tr:last-child { border-bottom:none; }
tbody tr:nth-child(even) { background:#f8fafc; }
tbody tr:hover { background:var(--row-hover) !important; }
td { padding:10px 12px; font-size:14px; color:var(--text-mid); vertical-align:middle; }
td:first-child { padding-left:20px; }
td:last-child { padding-right:20px; }
.td-mono  { font-family:'DM Mono',monospace; font-size:13px; }
.td-unit  { max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; }
.td-center { text-align:center; font-family:'DM Mono',monospace; font-size:13px; }
.td-acts  { white-space:nowrap; width:64px; }
.acts { display:flex; gap:2px; opacity:0; transition:opacity 0.12s; justify-content:flex-end; }
tbody tr:hover .acts { opacity:1; }
.act { width:28px; height:28px; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer; color:var(--text-light); display:flex; align-items:center; justify-content:center; transition:all 0.12s; }
.act svg { width:14px; height:14px; }
.act.e:hover { background:var(--accent-light); color:var(--accent); }
.act.d:hover:not(:disabled) { background:var(--red-bg); color:var(--red); }
.act:disabled { opacity:0.3; cursor:default; }

/* Badges */
.type-badge { display:inline-block; padding:2px 8px; border-radius:var(--radius-sm); font-size:12px; font-weight:600; }
.type-badge.incoming { background:#d1fae5; color:#065f46; }
.type-badge.transfer { background:#dbeafe; color:#1e40af; }
.type-badge.invoice  { background:#fef3c7; color:#92400e; }
.doc-type-label { font-size:11.5px; color:var(--text-light); margin-top:2px; }

.status-badge { display:inline-block; padding:2px 8px; border-radius:var(--radius-sm); font-size:12px; font-weight:500; }
.status-badge.draft           { background:var(--bg); color:var(--text-light); border:1px solid var(--border); }
.status-badge.signed          { background:#d1fae5; color:#065f46; font-weight:600; }
.status-badge.receiver_signed { background:#ede9fe; color:#5b21b6; font-weight:600; }


.empty-state { color:var(--text-light); padding:48px; text-align:center; font-size:14px; }
.t-foot { padding:9px 20px; border-top:1px solid var(--border-light); font-size:13px; color:var(--text-light); background:var(--bg); }
</style>
