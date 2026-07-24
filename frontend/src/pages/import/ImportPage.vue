<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">Імпорт</span>
          <button class="btn-wipe" @click="doWipe">Очистити інвентар</button>
        </div>
        <div class="body">
          <p class="flow">Порядок: <b>1.</b> Каталог (Items) → <b>2.</b> Переміщення (розміщення по складах) → далі видача вручну.</p>

          <!-- 1. Каталог -->
          <div class="block">
            <div class="block-title">1. Каталог — Items</div>
            <p class="hint">Номенклатура + серійні екземпляри. Колонки: <b>Назва</b>, <b>Служба</b>, Серійний номер, Од. виміру, Вартість. Розміщення НЕ робиться.</p>
            <div class="upload-row">
              <input type="file" accept=".xlsx" @change="e => pick('items', e)" />
              <button class="btn-pri" :disabled="!files.items || busy" @click="run('items')">Імпортувати каталог</button>
            </div>
            <Result :data="results.items" :err="errors.items" />
          </div>

          <!-- 2. Переміщення -->
          <div class="block">
            <div class="block-title">2. Переміщення</div>
            <p class="hint">Рухи склад→склад (той самий формат, що раніше). Розставляє майно по складах служб і підрозділів. «склад» / назва служби → склад служби.</p>
            <div class="upload-row">
              <input type="file" accept=".xlsx" @change="e => pick('movements', e)" />
              <button class="btn-pri" :disabled="!files.movements || busy" @click="run('movements')">Імпортувати переміщення</button>
            </div>
            <Result :data="results.movements" :err="errors.movements" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, h } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { importItems, importMovements, wipeV2 } from '../../api/importV2.js'

const files = reactive({ items: null, movements: null })
const results = reactive({ items: null, movements: null })
const errors = reactive({ items: '', movements: '' })
let busy = false

function pick(kind, e) {
  files[kind] = e.target.files?.[0] || null
  results[kind] = null
  errors[kind] = ''
}
async function run(kind) {
  if (!files[kind]) return
  busy = true
  errors[kind] = ''
  results[kind] = null
  try {
    const fn = kind === 'items' ? importItems : importMovements
    const { data } = await fn(files[kind])
    results[kind] = data
  } catch (e) {
    errors[kind] = e?.response?.data?.detail || 'Помилка імпорту'
  } finally {
    busy = false
  }
}
async function doWipe() {
  if (!confirm('Очистити весь v2-інвентар (номенклатура, рухи, видачі, екземпляри)? Довідники лишаться.')) return
  try {
    await wipeV2()
    alert('Інвентар очищено')
    results.items = null; results.movements = null
  } catch (e) {
    alert(e?.response?.data?.detail || 'Помилка')
  }
}

// Inline result renderer
const Result = (props) => {
  if (props.err) return h('div', { class: 'err' }, props.err)
  if (!props.data) return null
  const d = props.data
  const cells = Object.entries(d).filter(([k]) => k !== 'errors')
    .map(([k, v]) => h('div', { class: 'res-cell' }, [h('span', k), h('b', String(v))]))
  const errs = (d.errors || []).length
    ? h('div', { class: 'res-errors' }, [
        h('div', { class: 'res-title' }, `Помилки (${d.errors.length})`),
        h('ul', {}, d.errors.map(e => h('li', {}, e))),
      ])
    : null
  return h('div', { class: 'result' }, [h('div', { class: 'res-grid' }, cells), errs])
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; }
.tile-title { font-weight:700; font-size:15px; }
.btn-wipe { margin-left:auto; padding:6px 12px; background:transparent; border:1px solid #dc2626; color:#dc2626; border-radius:var(--radius-sm); font-family:inherit; font-size:12.5px; cursor:pointer; }
.body { padding:20px; }
.flow { font-size:13px; color:var(--text-mid); margin:0 0 20px; }
.block { border:1px solid var(--border-light); border-radius:var(--radius-sm); padding:16px; margin-bottom:16px; }
.block-title { font-weight:700; font-size:14px; margin-bottom:6px; }
.hint { font-size:12.5px; color:var(--text-light); line-height:1.5; margin:0 0 12px; }
.upload-row { display:flex; align-items:center; gap:12px; }
.btn-pri { padding:8px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
:deep(.err) { margin-top:12px; padding:10px 12px; background:#fee2e2; color:#991b1b; font-size:13px; border-radius:var(--radius-sm); }
:deep(.result) { margin-top:14px; }
:deep(.res-grid) { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; }
:deep(.res-cell) { background:var(--bg); border:1px solid var(--border-light); border-radius:var(--radius-sm); padding:10px 12px; display:flex; flex-direction:column; gap:3px; }
:deep(.res-cell span) { font-size:11.5px; color:var(--text-light); }
:deep(.res-cell b) { font-size:18px; font-family:'DM Mono',monospace; color:var(--text); }
:deep(.res-errors) { margin-top:16px; }
:deep(.res-title) { font-size:12px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:700; margin-bottom:8px; }
:deep(.res-errors ul) { margin:0; padding-left:18px; font-size:12.5px; color:#b45309; max-height:200px; overflow-y:auto; }
</style>
