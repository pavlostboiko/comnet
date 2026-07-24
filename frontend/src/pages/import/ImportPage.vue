<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header"><span class="tile-title">Імпорт майна</span></div>
        <div class="body">
          <p class="hint">
            Файл Items (XLSX). Колонки: <b>Назва</b>, <b>Служба</b>, Серійний номер,
            Од. виміру, Вартість, Кіл-сть, <b>Де</b> («&lt;підрозділ&gt; людина»), Дата видачі.
            Служби, підрозділи, номенклатура й особи створюються автоматично.
            <br>Порада: заведіть підрозділи заздалегідь — тоді «Де» коректно ділиться на підрозділ + особу.
          </p>

          <div class="upload-row">
            <input ref="fileRef" type="file" accept=".xlsx" @change="onPick" />
            <button class="btn-pri" :disabled="!file || busy" @click="doImport">
              {{ busy ? 'Імпорт…' : 'Імпортувати' }}
            </button>
          </div>

          <div v-if="error" class="err">{{ error }}</div>

          <div v-if="result" class="result">
            <div class="res-title">Готово</div>
            <div class="res-grid">
              <div class="res-cell"><span>Рядків</span><b>{{ result.rows }}</b></div>
              <div class="res-cell"><span>Номенклатура</span><b>{{ result.nomenclature }}</b></div>
              <div class="res-cell"><span>Рухів</span><b>{{ result.movements }}</b></div>
              <div class="res-cell"><span>Видач</span><b>{{ result.assignments }}</b></div>
              <div class="res-cell"><span>Служб створено</span><b>{{ result.services_created }}</b></div>
              <div class="res-cell"><span>Підрозділів створено</span><b>{{ result.units_created }}</b></div>
              <div class="res-cell"><span>Осіб створено</span><b>{{ result.persons_created }}</b></div>
            </div>
            <div v-if="result.errors?.length" class="res-errors">
              <div class="res-title">Помилки ({{ result.errors.length }})</div>
              <ul><li v-for="(e, i) in result.errors" :key="i">{{ e }}</li></ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TopBar from '../../components/TopBar.vue'
import { importItems } from '../../api/importV2.js'

const fileRef = ref(null)
const file = ref(null)
const busy = ref(false)
const error = ref('')
const result = ref(null)

function onPick(e) {
  file.value = e.target.files?.[0] || null
  result.value = null
  error.value = ''
}
async function doImport() {
  if (!file.value) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    const { data } = await importItems(file.value)
    result.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка імпорту'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.page-wrap { height:100vh; display:flex; flex-direction:column; overflow:hidden; }
.content-scroll { flex:1; overflow-y:auto; padding:20px 24px; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }
.tile-header { padding:14px 20px; border-bottom:1px solid var(--border-light); }
.tile-title { font-weight:700; font-size:15px; }
.body { padding:20px; }
.hint { font-size:13px; color:var(--text-mid); line-height:1.6; margin:0 0 18px; }
.upload-row { display:flex; align-items:center; gap:12px; }
.btn-pri { padding:8px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
.err { margin-top:14px; padding:10px 12px; background:#fee2e2; color:#991b1b; font-size:13px; border-radius:var(--radius-sm); }
.result { margin-top:20px; }
.res-title { font-size:12px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-light); font-weight:700; margin-bottom:10px; }
.res-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; }
.res-cell { background:var(--bg); border:1px solid var(--border-light); border-radius:var(--radius-sm); padding:10px 12px; display:flex; flex-direction:column; gap:3px; }
.res-cell span { font-size:11.5px; color:var(--text-light); }
.res-cell b { font-size:18px; font-family:'DM Mono',monospace; color:var(--text); }
.res-errors { margin-top:18px; }
.res-errors ul { margin:0; padding-left:18px; font-size:12.5px; color:#b45309; }
</style>
