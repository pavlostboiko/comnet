<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Довідники</span>
          <div class="tile-tabs">
            <button v-for="t in tabs" :key="t.key" class="tt-btn"
              :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
          </div>
          <button class="btn-add" @click="openAdd">+ Додати</button>
        </div>

        <!-- ═══ Служби ═══ -->
        <div v-if="tab === 'services'" class="table-wrap">
          <table>
            <thead><tr><th>Назва</th><th class="col-code">Код</th><th>Начальник</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!services.length"><td colspan="4" class="empty">Немає служб</td></tr>
              <tr v-for="s in services" :key="s.id">
                <td class="td-name">{{ s.name }}</td>
                <td>{{ s.code || '—' }}</td>
                <td class="td-dim">{{ s.chief_name || '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del('service', s)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ Підрозділи ═══ -->
        <div v-if="tab === 'units'" class="table-wrap">
          <table>
            <thead><tr><th>Назва</th><th class="col-code">Код</th><th>Місцевий відмінок</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!units.length"><td colspan="4" class="empty">Немає підрозділів</td></tr>
              <tr v-for="u in units" :key="u.id">
                <td class="td-name">{{ u.name }}</td>
                <td>{{ u.code || '—' }}</td>
                <td class="td-dim">{{ u.name_locative || '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del('unit', u)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ Номенклатура ═══ -->
        <div v-if="tab === 'nomenclature'" class="table-wrap">
          <table>
            <thead><tr>
              <th>Назва</th><th>Служба</th><th class="col-ser">Тип</th>
              <th class="col-uom">Од.</th><th class="col-price">Вартість</th><th class="col-acts"></th>
            </tr></thead>
            <tbody>
              <tr v-if="!nomenclature.length"><td colspan="6" class="empty">Немає номенклатури</td></tr>
              <tr v-for="n in nomenclature" :key="n.id">
                <td class="td-name">{{ n.name }}</td>
                <td class="td-dim">{{ serviceName(n.service_id) }}</td>
                <td><span class="chip" :class="n.is_serialized ? 'chip-ser' : 'chip-non'">{{ n.is_serialized ? 'серійне' : 'несерійне' }}</span></td>
                <td class="td-center">{{ n.unit_of_measure || '—' }}</td>
                <td class="td-num">{{ n.price != null ? Number(n.price).toFixed(2) : '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del('nomenclature', n)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ Склади ═══ -->
        <div v-if="tab === 'warehouses'" class="table-wrap">
          <div class="hint">Склади створюються автоматично — один на кожну службу і кожен підрозділ.</div>
          <table>
            <thead><tr><th>Назва</th><th class="col-ser">Тип</th><th>Прив'язка</th></tr></thead>
            <tbody>
              <tr v-if="!warehouses.length"><td colspan="3" class="empty">Немає складів</td></tr>
              <tr v-for="w in warehouses" :key="w.id">
                <td class="td-name">{{ w.name }}</td>
                <td><span class="chip" :class="w.type === 'service' ? 'chip-svc' : 'chip-unit'">{{ w.type === 'service' ? 'служба' : 'підрозділ' }}</span></td>
                <td class="td-dim">{{ w.type === 'service' ? serviceName(w.service_id) : unitName(w.unit_id) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ МВО ═══ -->
        <div v-if="tab === 'mvo'" class="table-wrap">
          <table>
            <thead><tr><th>Особа</th><th>Склад підрозділу</th><th class="col-date">З</th><th class="col-date">По</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!mvo.length"><td colspan="5" class="empty">Немає призначень</td></tr>
              <tr v-for="m in mvo" :key="m.id" :class="{ 'row-dim': m.to_date }">
                <td class="td-name">{{ personName(m.person_id) }}</td>
                <td class="td-dim">{{ warehouseName(m.warehouse_id) }}</td>
                <td class="td-mono">{{ m.from_date }}</td>
                <td class="td-mono">{{ m.to_date || '—' }}</td>
                <td class="td-acts">
                  <button v-if="!m.to_date" class="act-rot" @click="rotate(m)" title="Завершити (ротація)">↩</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ Групи ═══ -->
        <div v-if="tab === 'groups'" class="table-wrap">
          <table>
            <thead><tr><th>Назва</th><th>Підрозділ</th><th>Командир</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!groups.length"><td colspan="4" class="empty">Немає груп</td></tr>
              <tr v-for="g in groups" :key="g.id">
                <td class="td-name">{{ g.name }}</td>
                <td class="td-dim">{{ unitName(g.unit_id) }}</td>
                <td class="td-dim">{{ g.commander_id ? personName(g.commander_id) : '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del('group', g)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ═══ Особи ═══ -->
        <div v-if="tab === 'persons'" class="table-wrap">
          <table>
            <thead><tr><th>ПІБ / позивний</th><th>Підрозділ</th><th>Група</th><th class="col-code">Звання</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!persons.length"><td colspan="5" class="empty">Немає осіб</td></tr>
              <tr v-for="p in persons" :key="p.id">
                <td class="td-name">{{ personLabel(p) }}</td>
                <td class="td-dim">{{ p.unit_id ? unitName(p.unit_id) : '—' }}</td>
                <td class="td-dim">{{ p.group_id ? groupName(p.group_id) : '—' }}</td>
                <td>{{ p.rank || '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del('person', p)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══ Add modal ═══ -->
    <div class="overlay" :class="{ open: addOpen }" @click.self="addOpen = false">
      <div v-if="addOpen" class="modal">
        <div class="modal-head">
          <span class="modal-title">Додати: {{ currentTab.label }}</span>
          <button class="modal-close" @click="addOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <template v-if="tab === 'services'">
            <label class="fl">Назва *</label><input class="fi" v-model="form.name" />
            <label class="fl">Код</label><input class="fi" v-model="form.code" />
            <label class="fl">Начальник (ПІБ)</label><input class="fi" v-model="form.chief_name" />
          </template>
          <template v-else-if="tab === 'units'">
            <label class="fl">Назва *</label><input class="fi" v-model="form.name" />
            <label class="fl">Код</label><input class="fi" v-model="form.code" />
            <label class="fl">Місцевий відмінок («у 1-й роті»)</label><input class="fi" v-model="form.name_locative" />
          </template>
          <template v-else-if="tab === 'nomenclature'">
            <label class="fl">Назва *</label><input class="fi" v-model="form.name" />
            <label class="fl">Служба *</label>
            <select class="fi" v-model="form.service_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <label class="fl"><input type="checkbox" v-model="form.is_serialized" /> Серійне майно</label>
            <label class="fl">Одиниця виміру</label><input class="fi" v-model="form.unit_of_measure" placeholder="шт" />
            <label class="fl">Вартість</label><input class="fi" type="number" v-model="form.price" />
          </template>
          <template v-else-if="tab === 'mvo'">
            <label class="fl">Склад підрозділу *</label>
            <select class="fi" v-model="form.warehouse_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="w in unitWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
            <label class="fl">Особа *</label>
            <select class="fi" v-model="form.person_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
            <label class="fl">Діє з *</label><input class="fi" type="date" v-model="form.from_date" />
          </template>
          <template v-else-if="tab === 'groups'">
            <label class="fl">Назва *</label><input class="fi" v-model="form.name" />
            <label class="fl">Підрозділ *</label>
            <select class="fi" v-model="form.unit_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="u in units" :key="u.id" :value="u.id">{{ u.name }}</option>
            </select>
            <label class="fl">Командир</label>
            <select class="fi" v-model="form.commander_id">
              <option :value="null">— не вказано —</option>
              <option v-for="p in persons" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
          </template>
          <template v-else-if="tab === 'persons'">
            <label class="fl">Прізвище</label><input class="fi" v-model="form.last_name" />
            <label class="fl">Ім'я</label><input class="fi" v-model="form.first_name" />
            <label class="fl">Позивний</label><input class="fi" v-model="form.callsign" />
            <label class="fl">Звання</label><input class="fi" v-model="form.rank" />
            <label class="fl">Підрозділ</label>
            <select class="fi" v-model="form.unit_id">
              <option :value="null">— не вказано —</option>
              <option v-for="u in units" :key="u.id" :value="u.id">{{ u.name }}</option>
            </select>
            <label class="fl">Група</label>
            <select class="fi" v-model="form.group_id">
              <option :value="null">— не вказано —</option>
              <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }} ({{ unitName(g.unit_id) }})</option>
            </select>
          </template>
          <div v-if="error" class="err">{{ error }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="addOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="saving" @click="save">Зберегти</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getServices, createService, deleteService, getPersons, createPerson, deletePerson } from '../../api/settings.js'
import {
  getUnits, createUnit, deleteUnit, getWarehouses,
  getGroups, createGroup, deleteGroup,
  getMvo, createMvo, updateMvo,
} from '../../api/structure.js'
import {
  getNomenclature, createNomenclature, deleteNomenclature,
} from '../../api/nomenclature.js'

const tabs = [
  { key: 'services', label: 'Служби' },
  { key: 'units', label: 'Підрозділи' },
  { key: 'nomenclature', label: 'Номенклатура' },
  { key: 'warehouses', label: 'Склади' },
  { key: 'mvo', label: 'МВО' },
  { key: 'groups', label: 'Групи' },
  { key: 'persons', label: 'Особи' },
]
const tab = ref('services')
const currentTab = computed(() => tabs.find(t => t.key === tab.value))

const services = ref([])
const units = ref([])
const nomenclature = ref([])
const warehouses = ref([])
const mvo = ref([])
const groups = ref([])
const persons = ref([])

const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit'))
const serviceName = (id) => services.value.find(s => s.id === id)?.name || '—'
const unitName = (id) => units.value.find(u => u.id === id)?.name || '—'
const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || '—'
function personLabel(p) {
  const full = [p.last_name, p.first_name].filter(Boolean).join(' ')
  return full || p.callsign || `#${p.id}`
}
const personName = (id) => {
  const p = persons.value.find(x => x.id === id)
  return p ? personLabel(p) : '—'
}
const groupName = (id) => groups.value.find(g => g.id === id)?.name || '—'

async function loadAll() {
  const [s, u, n, w, m, g, p] = await Promise.all([
    getServices(), getUnits(), getNomenclature(), getWarehouses(),
    getMvo(), getGroups(), getPersons(),
  ])
  services.value = s.data
  units.value = u.data
  nomenclature.value = n.data
  warehouses.value = w.data
  mvo.value = m.data
  groups.value = g.data
  persons.value = p.data
}
onMounted(loadAll)

// Add modal
const addOpen = ref(false)
const saving = ref(false)
const error = ref('')
const form = reactive({})
function openAdd() {
  error.value = ''
  Object.keys(form).forEach(k => delete form[k])
  if (tab.value === 'nomenclature') { form.service_id = null; form.is_serialized = false }
  else if (tab.value === 'mvo') { form.warehouse_id = null; form.person_id = null; form.from_date = new Date().toISOString().slice(0, 10) }
  else if (tab.value === 'groups') { form.unit_id = null; form.commander_id = null }
  else if (tab.value === 'persons') { form.unit_id = null; form.group_id = null }
  addOpen.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    if (tab.value === 'services') await createService({ name: form.name, code: form.code || null, chief_name: form.chief_name || null })
    else if (tab.value === 'units') await createUnit({ name: form.name, code: form.code || null, name_locative: form.name_locative || null })
    else if (tab.value === 'nomenclature') {
      if (!form.service_id) { error.value = 'Оберіть службу'; saving.value = false; return }
      await createNomenclature({
        name: form.name, service_id: form.service_id, is_serialized: !!form.is_serialized,
        unit_of_measure: form.unit_of_measure || null, price: form.price ? Number(form.price) : null,
      })
    }
    else if (tab.value === 'mvo') {
      if (!form.warehouse_id || !form.person_id) { error.value = 'Оберіть склад і особу'; saving.value = false; return }
      await createMvo({ warehouse_id: form.warehouse_id, person_id: form.person_id, from_date: form.from_date })
    }
    else if (tab.value === 'groups') {
      if (!form.unit_id) { error.value = 'Оберіть підрозділ'; saving.value = false; return }
      await createGroup({ name: form.name, unit_id: form.unit_id, commander_id: form.commander_id || null })
    }
    else if (tab.value === 'persons') {
      await createPerson({
        last_name: form.last_name || null, first_name: form.first_name || null,
        callsign: form.callsign || null, rank: form.rank || null,
        unit_id: form.unit_id || null, group_id: form.group_id || null,
      })
    }
    addOpen.value = false
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка збереження'
  } finally {
    saving.value = false
  }
}

async function del(kind, row) {
  const label = kind === 'person' ? personLabel(row) : row.name
  if (!confirm(`Видалити «${label}»?`)) return
  try {
    if (kind === 'service') await deleteService(row.id)
    else if (kind === 'unit') await deleteUnit(row.id)
    else if (kind === 'nomenclature') await deleteNomenclature(row.id)
    else if (kind === 'group') await deleteGroup(row.id)
    else if (kind === 'person') await deletePerson(row.id)
    await loadAll()
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось видалити')
  }
}

async function rotate(m) {
  const today = new Date().toISOString().slice(0, 10)
  const to = prompt('Дата завершення призначення (YYYY-MM-DD):', today)
  if (!to) return
  try {
    await updateMvo(m.id, { to_date: to })
    await loadAll()
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось завершити')
  }
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; }
.tile-title { font-weight:700; font-size:15px; }
.tile-tabs { display:flex; gap:2px; background:var(--bg); padding:3px; border-radius:var(--radius-sm); }
.tt-btn { padding:5px 13px; border:none; background:transparent; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:500; color:var(--text-light); cursor:pointer; }
.tt-btn.on { background:var(--surface); color:var(--text); box-shadow:0 1px 2px rgba(0,0,0,0.06); font-weight:600; }
.btn-add { margin-left:auto; padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }

.table-wrap { overflow-x:auto; }
.hint { padding:10px 20px; font-size:12.5px; color:var(--text-light); font-style:italic; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-code { width:100px; } .col-ser { width:120px; } .col-uom { width:70px; } .col-price { width:120px; text-align:right; } .col-acts { width:50px; } .col-date { width:120px; }
.td-name { font-weight:600; color:var(--text); }
.td-dim { color:var(--text-light); }
.td-center { text-align:center; }
.td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.td-acts { text-align:center; }
.row-dim td { opacity:0.55; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.act-del { background:transparent; border:none; color:var(--text-light); cursor:pointer; font-size:14px; }
.act-del:hover { color:#dc2626; }
.act-rot { background:transparent; border:none; color:var(--accent); cursor:pointer; font-size:15px; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.chip-ser { background:#dbeafe; color:#1e40af; } .chip-non { background:#f1f5f9; color:#475569; }
.chip-svc { background:#fef3c7; color:#854d0e; } .chip-unit { background:#dcfce7; color:#166534; }

.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:80px 20px; z-index:1200; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(460px,100%); }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-weight:700; font-size:14px; }
.modal-close { border:none; background:transparent; font-size:16px; color:var(--text-light); cursor:pointer; }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:8px; }
.fi { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; }
.err { margin-top:10px; padding:8px 10px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-sec { padding:7px 14px; background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; cursor:pointer; }
.btn-pri { padding:7px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
</style>
