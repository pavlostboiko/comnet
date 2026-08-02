<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Звіти</span>
          <div class="tabs">
            <button :class="{ on: tab === 'person' }" @click="tab = 'person'">Видане на особу</button>
            <button :class="{ on: tab === 'group' }" @click="tab = 'group'">Видане на групу</button>
          </div>
        </div>

        <!-- Видане на особу -->
        <div v-if="tab === 'person'">
          <div class="sel-row">
            <label class="fl">Особа</label>
            <div class="ac-field">
              <ItemAutocomplete :items="personOpts" placeholder="пошук особи…"
                :model-value="personId ? personName(personId) : ''"
                @select="onPickPerson" />
            </div>
          </div>
          <div class="table-wrap" v-if="personId">
            <table>
              <thead><tr>
                <th>Майно</th><th class="col-serial">Серійний</th><th class="col-off">Тип</th>
                <th class="col-num">К-сть</th><th class="col-uom">Од.</th><th>Склад</th><th class="col-date">Дата</th>
              </tr></thead>
              <tbody>
                <tr v-if="!personRows.length"><td colspan="7" class="empty">Нічого не видано</td></tr>
                <tr v-for="a in personRows" :key="a.id">
                  <td class="td-name">{{ a.nomenclature_name }}</td>
                  <td class="td-mono td-dim">{{ a.serial_no || '—' }}</td>
                  <td><span class="chip" :class="a.is_official ? 'chip-gov' : 'chip-vol'">{{ a.is_official ? 'облік' : 'ндм' }}</span></td>
                  <td class="td-num">{{ fmtQty(a.quantity) }}</td>
                  <td class="td-center">{{ a.unit_of_measure || '—' }}</td>
                  <td class="td-dim">{{ a.warehouse_name || '—' }}</td>
                  <td class="td-mono td-dim">{{ a.issued_date }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Видане на групу -->
        <div v-else>
          <div class="sel-row">
            <label class="fl">Група</label>
            <select class="fi" v-model="groupId" @change="loadGroup">
              <option :value="null" disabled>— оберіть групу —</option>
              <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>
          <div v-if="groupId && group">
            <div v-if="!group.members?.length" class="g-none">
              У групі немає бійців — призначте групу особам у Довідники → Особи.
            </div>
            <div v-else class="g-sub">Всього позицій: <b>{{ group.total_items || 0 }}</b></div>
            <div v-for="m in group.members" :key="m.person_id" class="g-member">
              <div class="g-mhead">
                {{ m.person_name }}
                <span v-if="m.is_commander" class="chip chip-cmd">командир</span>
                <span class="g-count">{{ m.items.length }}</span>
              </div>
              <table v-if="m.items.length">
                <tbody>
                  <tr v-for="(it, i) in m.items" :key="i">
                    <td class="td-name">{{ it.name }}</td>
                    <td class="td-mono td-dim">{{ it.serial_no || '—' }}</td>
                    <td><span class="chip" :class="it.is_official ? 'chip-gov' : 'chip-vol'">{{ it.is_official ? 'облік' : 'ндм' }}</span></td>
                    <td class="td-num">{{ fmtQty(it.quantity) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="g-empty">— нічого не видано</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import ItemAutocomplete from '../../components/ItemAutocomplete.vue'
import { personLabel, personOptions } from '../../utils/person.js'
import { getPersons } from '../../api/settings.js'
import { getGroups } from '../../api/structure.js'
import { personHoldings, groupHoldings } from '../../api/assignments.js'

const tab = ref('person')
const persons = ref([])
const groups = ref([])
const personId = ref(null)
const groupId = ref(null)
const personRows = ref([])
const group = ref(null)

const personOpts = computed(() => personOptions(persons.value))
const personName = (id) => personLabel(persons.value.find(p => p.id === id))
function onPickPerson(item) {
  personId.value = item.id
  loadPerson()
}
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

async function loadPerson() {
  if (!personId.value) return
  personRows.value = (await personHoldings(personId.value)).data
}
async function loadGroup() {
  if (!groupId.value) return
  group.value = (await groupHoldings(groupId.value)).data
}

onMounted(async () => {
  const [p, g] = await Promise.all([getPersons(), getGroups()])
  persons.value = p.data
  groups.value = g.data
})
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:20px; }
.tile-title { font-weight:700; font-size:15px; }
.tabs { display:flex; gap:6px; }
.tabs button { border:1px solid var(--border); background:var(--bg); border-radius:var(--radius-sm); padding:5px 12px; cursor:pointer; font-family:inherit; font-size:13px; color:var(--text-mid); }
.tabs button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.ac-field { border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--surface); min-width:280px; }
.ac-field :deep(.cell-input) { width:100%; box-sizing:border-box; padding:7px 10px; font-size:14px; }
.sel-row { padding:14px 20px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border-light); }
.fl { font-size:12px; color:var(--text-light); font-weight:600; }
.fi { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13.5px; min-width:280px; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-serial { width:150px; } .col-off { width:110px; } .col-num { width:90px; text-align:right; } .col-uom { width:70px; } .col-date { width:120px; }
.td-name { font-weight:600; } .td-dim { color:var(--text-light); } .td-center { text-align:center; }
.td-num { text-align:right; font-family:'DM Mono',monospace; } .td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.empty { text-align:center; padding:28px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.chip-gov { background:#dbeafe; color:#1e40af; } .chip-vol { background:#fef3c7; color:#854d0e; }
.chip-cmd { background:#e0e7ff; color:#3730a3; margin-left:8px; }
.g-none { padding:20px; color:var(--text-light); font-style:italic; font-size:13px; }
.g-sub { padding:12px 20px 0; font-size:13px; color:var(--text-mid); }
.g-member { padding:12px 20px; border-bottom:1px solid var(--border-light); }
.g-mhead { font-weight:600; font-size:14px; margin-bottom:6px; display:flex; align-items:center; }
.g-count { margin-left:auto; font-family:'DM Mono',monospace; font-size:12px; color:var(--text-light); }
.g-empty { font-size:12.5px; color:var(--text-light); font-style:italic; }
</style>
