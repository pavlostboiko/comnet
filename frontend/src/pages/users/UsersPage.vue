<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Користувачі</span>
          <button class="btn-add" @click="openAdd">+ Додати</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Логін</th><th class="col-role">Роль</th><th>Зона доступу</th><th class="col-act">Активний</th><th class="col-acts"></th></tr></thead>
            <tbody>
              <tr v-if="!users.length"><td colspan="5" class="empty">Немає користувачів</td></tr>
              <tr v-for="u in users" :key="u.id">
                <td class="td-name">{{ u.username }}</td>
                <td><span class="chip" :class="`role-${u.role}`">{{ roleLabel(u.role) }}</span></td>
                <td class="td-dim">{{ scopeText(u) }}</td>
                <td class="td-center">{{ u.is_active ? '✓' : '—' }}</td>
                <td class="td-acts"><button class="act-del" @click="del(u)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="overlay" :class="{ open: addOpen }" @click.self="addOpen = false">
      <div v-if="addOpen" class="modal">
        <div class="modal-head">
          <span class="modal-title">Новий користувач</span>
          <button class="modal-close" @click="addOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <label class="fl">Логін *</label><input class="fi" v-model="form.username" />
          <label class="fl">Пароль *</label><input class="fi" type="password" v-model="form.password" />
          <label class="fl">Роль *</label>
          <select class="fi" v-model="form.role">
            <option value="admin">Адміністратор</option>
            <option value="service">Служба</option>
            <option value="mvo">МВО</option>
          </select>

          <template v-if="form.role === 'service'">
            <label class="fl">Служба *</label>
            <select class="fi" v-model="form.service_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </template>

          <template v-if="form.role === 'mvo'">
            <label class="fl">Підрозділ *</label>
            <select class="fi" v-model="form.unit_id" @change="syncWarehouse">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="u in units" :key="u.id" :value="u.id">{{ u.name }}</option>
            </select>
            <label class="fl">Склад (авто)</label>
            <input class="fi" :value="warehouseName(form.warehouse_id)" disabled />
            <label class="fl">Особа</label>
            <div class="ac-field">
              <ItemAutocomplete :items="unitPersonOptions" placeholder="пошук особи (опц.)…"
                :model-value="form.person_id ? personName(form.person_id) : ''"
                @select="e => form.person_id = e.id"
                @update:model-value="v => { if (!v) form.person_id = null }" />
            </div>
          </template>

          <div v-if="error" class="err">{{ error }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="addOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="saving" @click="save">Створити</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import ItemAutocomplete from '../../components/ItemAutocomplete.vue'
import { personLabel, personOptions } from '../../utils/person.js'
import { getUsers, createUser, deleteUser } from '../../api/users.js'
import { getServices, getPersons } from '../../api/settings.js'
import { getUnits, getWarehouses } from '../../api/structure.js'

const users = ref([])
const services = ref([])
const units = ref([])
const warehouses = ref([])
const persons = ref([])

const roleLabel = (r) => ({ admin: 'Адміністратор', operator: 'Оператор', service: 'Служба', mvo: 'МВО' }[r] || r)
const serviceName = (id) => services.value.find(s => s.id === id)?.name || '—'
const unitName = (id) => units.value.find(u => u.id === id)?.name || '—'
const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || '—'
const unitPersonOptions = computed(() => personOptions(persons.value.filter(p => p.unit_id === form.unit_id)))
const personName = (id) => personLabel(persons.value.find(p => p.id === id))

function scopeText(u) {
  if (u.role === 'service') return `Служба: ${serviceName(u.service_id)}`
  if (u.role === 'mvo') return `Склад: ${warehouseName(u.warehouse_id)}`
  if (u.role === 'admin') return 'Повний доступ'
  return '—'
}

async function loadAll() {
  const [us, s, u, w, p] = await Promise.all([
    getUsers(), getServices(), getUnits(), getWarehouses(), getPersons(),
  ])
  users.value = us.data
  services.value = s.data
  units.value = u.data
  warehouses.value = w.data
  persons.value = p.data
}
onMounted(loadAll)

const addOpen = ref(false)
const saving = ref(false)
const error = ref('')
const form = reactive({})
function openAdd() {
  error.value = ''
  Object.assign(form, { username: '', password: '', role: 'admin', service_id: null, unit_id: null, warehouse_id: null, person_id: null })
  addOpen.value = true
}
function syncWarehouse() {
  const wh = warehouses.value.find(w => w.type === 'unit' && w.unit_id === form.unit_id)
  form.warehouse_id = wh ? wh.id : null
  form.person_id = null
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    if (!form.username || !form.password) { error.value = 'Логін і пароль обов’язкові'; saving.value = false; return }
    if (form.role === 'service' && !form.service_id) { error.value = 'Оберіть службу'; saving.value = false; return }
    if (form.role === 'mvo' && !form.warehouse_id) { error.value = 'Оберіть підрозділ'; saving.value = false; return }
    await createUser({
      username: form.username, password: form.password, role: form.role, is_active: true,
      service_id: form.role === 'service' ? form.service_id : null,
      unit_id: form.role === 'mvo' ? form.unit_id : null,
      warehouse_id: form.role === 'mvo' ? form.warehouse_id : null,
      person_id: form.role === 'mvo' ? (form.person_id || null) : null,
    })
    addOpen.value = false
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка створення'
  } finally {
    saving.value = false
  }
}

async function del(u) {
  if (!confirm(`Видалити користувача «${u.username}»?`)) return
  try {
    await deleteUser(u.id)
    await loadAll()
  } catch (e) {
    alert(e?.response?.data?.detail || 'Не вдалось видалити')
  }
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; }
.tile-title { font-weight:700; font-size:15px; }
.btn-add { margin-left:auto; padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-role { width:150px; } .col-act { width:90px; text-align:center; } .col-acts { width:50px; }
.td-name { font-weight:600; } .td-dim { color:var(--text-light); } .td-center { text-align:center; } .td-acts { text-align:center; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.act-del { background:transparent; border:none; color:var(--text-light); cursor:pointer; font-size:14px; }
.act-del:hover { color:#dc2626; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.role-admin { background:#ede9fe; color:#5b21b6; } .role-service { background:#fef3c7; color:#854d0e; } .role-mvo { background:#dcfce7; color:#166534; } .role-operator { background:#f1f5f9; color:#475569; }
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:70px 20px; z-index:1200; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(440px,100%); }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-weight:700; font-size:14px; }
.modal-close { border:none; background:transparent; font-size:16px; color:var(--text-light); cursor:pointer; }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
.ac-field { border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--surface); }
.ac-field :deep(.cell-input) { width:100%; box-sizing:border-box; padding:7px 10px; font-size:14px; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:8px; }
.fi { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; }
.fi:disabled { background:var(--bg); color:var(--text-light); }
.err { margin-top:10px; padding:8px 10px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-sec { padding:7px 14px; background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; cursor:pointer; }
.btn-pri { padding:7px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
</style>
