<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Залишки</span>
          <select class="wh-select" v-model="warehouseId" @change="loadStock">
            <option :value="null" disabled>— оберіть склад —</option>
            <optgroup label="Склади служб">
              <option v-for="w in serviceWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
            <optgroup label="Склади підрозділів">
              <option v-for="w in unitWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
          <button class="btn-add" :disabled="!warehouseId" @click="openMove">+ Рух</button>
        </div>

        <div v-if="!warehouseId" class="empty">Оберіть склад, щоб побачити залишки</div>

        <template v-else>
          <!-- Несерійне -->
          <div class="section-label">Несерійне майно</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Найменування</th><th class="col-off">Тип</th><th class="col-num">К-сть</th><th class="col-uom">Од.</th><th class="col-num">Вартість</th></tr></thead>
              <tbody>
                <tr v-if="!balances.length"><td colspan="5" class="empty">Порожньо</td></tr>
                <tr v-for="(b, i) in balances" :key="i">
                  <td class="td-name">{{ b.name }}</td>
                  <td><span class="chip" :class="b.is_official ? 'chip-gov' : 'chip-vol'">{{ b.is_official ? 'державне' : 'волонтерське' }}</span></td>
                  <td class="td-num">{{ fmtQty(b.qty) }}</td>
                  <td class="td-center">{{ b.unit_of_measure || '—' }}</td>
                  <td class="td-num">{{ b.price != null ? Number(b.price).toFixed(2) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Серійне -->
          <div class="section-label">Серійне майно</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>№ / серійний</th><th>Найменування</th><th class="col-off">Тип</th></tr></thead>
              <tbody>
                <tr v-if="!serial.length"><td colspan="3" class="empty">Порожньо</td></tr>
                <tr v-for="s in serial" :key="s.instance_id">
                  <td class="td-mono">{{ s.serial_no }}</td>
                  <td class="td-name">{{ s.name }}</td>
                  <td><span class="chip" :class="s.is_official ? 'chip-gov' : 'chip-vol'">{{ s.is_official ? 'державне' : 'волонтерське' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Останні рухи цього складу -->
          <div class="section-label">Останні рухи</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th class="col-date">Дата</th><th class="col-off">Тип</th><th>Звідки → Куди</th><th>Номенклатура</th><th class="col-num">К-сть</th></tr></thead>
              <tbody>
                <tr v-if="!whMovements.length"><td colspan="5" class="empty">Немає рухів</td></tr>
                <tr v-for="m in whMovements" :key="m.id">
                  <td class="td-mono">{{ m.date }}</td>
                  <td><span class="chip" :class="`mv-${m.type}`">{{ moveLabel(m.type) }}</span></td>
                  <td class="td-dim">{{ warehouseName(m.from_warehouse_id) }} → {{ warehouseName(m.to_warehouse_id) }}</td>
                  <td>{{ nomName(m.nomenclature_id) }}</td>
                  <td class="td-num">{{ fmtQty(m.quantity) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>

    <!-- ═══ Рух modal ═══ -->
    <div class="overlay" :class="{ open: moveOpen }" @click.self="moveOpen = false">
      <div v-if="moveOpen" class="modal">
        <div class="modal-head">
          <span class="modal-title">Новий рух — {{ warehouseName(warehouseId) }}</span>
          <button class="modal-close" @click="moveOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <label class="fl">Тип</label>
          <select class="fi" v-model="mv.type" @change="onTypeChange">
            <option value="receipt">Надходження (ззовні → цей склад)</option>
            <option value="transfer">Переміщення (цей склад → інший)</option>
            <option value="writeoff">Списання (з цього складу)</option>
          </select>

          <label class="fl">Номенклатура</label>
          <select class="fi" v-model="mv.nomenclature_id" @change="onNomChange">
            <option :value="null" disabled>— оберіть —</option>
            <option v-for="n in nomenclature" :key="n.id" :value="n.id">
              {{ n.name }} ({{ n.is_serialized ? 'серійне' : 'несерійне' }})
            </option>
          </select>

          <template v-if="mv.type === 'transfer'">
            <label class="fl">Куди (склад)</label>
            <select class="fi" v-model="mv.to_warehouse_id">
              <option :value="null" disabled>— оберіть —</option>
              <option v-for="w in otherWarehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </template>

          <template v-if="selectedNom && selectedNom.is_serialized">
            <template v-if="mv.type === 'receipt'">
              <label class="fl">Серійний номер</label>
              <input class="fi" v-model="mv.serial_no" placeholder="напр. SN-12345" />
              <label class="fl"><input type="checkbox" v-model="mv.is_official" /> Державне (інакше — волонтерське)</label>
            </template>
            <template v-else>
              <label class="fl">Екземпляр (на цьому складі)</label>
              <select class="fi" v-model="mv.instance_id">
                <option :value="null" disabled>— оберіть —</option>
                <option v-for="s in serialOfNom" :key="s.instance_id" :value="s.instance_id">{{ s.serial_no }}</option>
              </select>
            </template>
          </template>
          <template v-else-if="selectedNom">
            <label class="fl">Кількість</label>
            <input class="fi" type="number" min="0.0001" step="0.0001" v-model="mv.quantity" />
            <label class="fl"><input type="checkbox" v-model="mv.is_official" /> Державне (інакше — волонтерське)</label>
          </template>

          <label class="fl">Дата</label>
          <input class="fi" type="date" v-model="mv.date" />
          <div v-if="error" class="err">{{ error }}</div>
        </div>
        <div class="modal-foot">
          <button class="btn-sec" @click="moveOpen = false">Скасувати</button>
          <button class="btn-pri" :disabled="saving" @click="saveMove">Провести</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { getWarehouses } from '../../api/structure.js'
import { getNomenclature, createInstance } from '../../api/nomenclature.js'
import { getBalances, getSerialAt, getMovements, createMovement } from '../../api/custody.js'

const warehouses = ref([])
const nomenclature = ref([])
const warehouseId = ref(null)
const balances = ref([])
const serial = ref([])
const movements = ref([])

const serviceWarehouses = computed(() => warehouses.value.filter(w => w.type === 'service'))
const unitWarehouses = computed(() => warehouses.value.filter(w => w.type === 'unit'))
const otherWarehouses = computed(() => warehouses.value.filter(w => w.id !== warehouseId.value))
const whMovements = computed(() => movements.value
  .filter(m => m.from_warehouse_id === warehouseId.value || m.to_warehouse_id === warehouseId.value)
  .slice(0, 20))

const warehouseName = (id) => warehouses.value.find(w => w.id === id)?.name || (id ? `#${id}` : 'ззовні')
const nomName = (id) => nomenclature.value.find(n => n.id === id)?.name || '—'
const selectedNom = computed(() => nomenclature.value.find(n => n.id === mv.nomenclature_id) || null)
const serialOfNom = computed(() => serial.value.filter(s => s.nomenclature_id === mv.nomenclature_id))

function moveLabel(t) { return { receipt: 'надходження', transfer: 'переміщення', writeoff: 'списання' }[t] || t }
function fmtQty(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toLocaleString('uk-UA', { maximumFractionDigits: 4 })
}

async function loadRefs() {
  const [w, n] = await Promise.all([getWarehouses(), getNomenclature()])
  warehouses.value = w.data
  nomenclature.value = n.data
}
async function loadStock() {
  if (!warehouseId.value) return
  const [b, s, m] = await Promise.all([
    getBalances(warehouseId.value), getSerialAt(warehouseId.value), getMovements(),
  ])
  balances.value = b.data
  serial.value = s.data
  movements.value = m.data
}
onMounted(loadRefs)

// Move modal
const moveOpen = ref(false)
const saving = ref(false)
const error = ref('')
const mv = reactive({})
function openMove() {
  error.value = ''
  Object.assign(mv, {
    type: 'receipt', nomenclature_id: null, to_warehouse_id: null,
    instance_id: null, serial_no: '', quantity: null, is_official: true,
    date: new Date().toISOString().slice(0, 10),
  })
  moveOpen.value = true
}
function onTypeChange() { mv.instance_id = null }
function onNomChange() { mv.instance_id = null }

async function saveMove() {
  saving.value = true
  error.value = ''
  try {
    if (!mv.nomenclature_id) { error.value = 'Оберіть номенклатуру'; saving.value = false; return }
    const W = warehouseId.value
    const from = mv.type === 'receipt' ? null : W
    const to = mv.type === 'receipt' ? W : (mv.type === 'transfer' ? mv.to_warehouse_id : null)
    if (mv.type === 'transfer' && !to) { error.value = 'Оберіть склад призначення'; saving.value = false; return }

    let instanceId = mv.instance_id
    if (selectedNom.value?.is_serialized && mv.type === 'receipt') {
      if (!mv.serial_no) { error.value = 'Вкажіть серійний номер'; saving.value = false; return }
      const inst = await createInstance(mv.nomenclature_id, { serial_no: mv.serial_no, is_official: mv.is_official })
      instanceId = inst.data.id
    }

    await createMovement({
      date: mv.date, type: mv.type, nomenclature_id: mv.nomenclature_id,
      from_warehouse_id: from, to_warehouse_id: to,
      instance_id: selectedNom.value?.is_serialized ? instanceId : null,
      quantity: selectedNom.value?.is_serialized ? 1 : Number(mv.quantity),
      is_official: mv.is_official,
    })
    moveOpen.value = false
    await loadStock()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка проведення'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:16px; }
.tile-title { font-weight:700; font-size:15px; }
.wh-select { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; min-width:240px; }
.btn-add { margin-left:auto; padding:6px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-add:disabled { opacity:0.5; }

.section-label { padding:14px 20px 6px; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:600; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:9px 14px; text-align:left; font-size:13px; border-bottom:1px solid var(--border-light); }
th { background:var(--bg); color:var(--text-light); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; }
.col-off { width:130px; } .col-num { width:110px; text-align:right; } .col-uom { width:70px; } .col-date { width:110px; }
.td-name { font-weight:600; color:var(--text); }
.td-dim { color:var(--text-light); }
.td-center { text-align:center; }
.td-num { text-align:right; font-family:'DM Mono',monospace; }
.td-mono { font-family:'DM Mono',monospace; font-size:12px; }
.empty { text-align:center; padding:32px; color:var(--text-light); font-style:italic; }
.chip { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }
.chip-gov { background:#dbeafe; color:#1e40af; } .chip-vol { background:#fef3c7; color:#854d0e; }
.mv-receipt { background:#dcfce7; color:#166534; } .mv-transfer { background:#e0e7ff; color:#3730a3; } .mv-writeoff { background:#fee2e2; color:#991b1b; }

.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:70px 20px; z-index:1200; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(480px,100%); }
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
