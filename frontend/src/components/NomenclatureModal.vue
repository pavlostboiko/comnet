<template>
  <div class="overlay" :class="{ open }" @click.self="$emit('close')">
    <div v-if="open" class="modal">
      <div class="modal-head">
        <span class="modal-title">{{ editId ? 'Редагувати' : 'Додати' }} майно</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-body">
        <label class="fl">Назва *</label><input class="fi" v-model="form.name" />
        <label class="fl">Служба *</label>
        <select class="fi" v-model="form.service_id">
          <option :value="null" disabled>— оберіть —</option>
          <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <label class="fl">Категорія</label>
        <input class="fi" v-model="form.category" list="nm-cats" />
        <datalist id="nm-cats"><option v-for="c in categories" :key="c" :value="c" /></datalist>
        <label class="fl">Тип обліку</label>
        <select class="fi" v-model="form.is_official">
          <option :value="true">облік</option>
          <option :value="false">ндм</option>
        </select>
        <label class="fl"><input type="checkbox" v-model="form.is_serialized" /> Серійне майно</label>
        <label class="fl">Одиниця виміру</label><input class="fi" v-model="form.unit_of_measure" placeholder="шт" />
        <label class="fl">Вартість</label><input class="fi" type="number" v-model="form.price" />
        <label class="fl">Код номер</label><input class="fi" v-model="form.code" />
        <div v-if="error" class="err">{{ error }}</div>
      </div>
      <div class="modal-foot">
        <button class="btn-sec" @click="$emit('close')">Скасувати</button>
        <button class="btn-pri" :disabled="saving" @click="save">Зберегти</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { createNomenclature, updateNomenclature } from '../api/nomenclature.js'

const props = defineProps({
  open: Boolean,
  item: { type: Object, default: null },              // null → створення
  services: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  defaultServiceId: { type: [Number, null], default: null },
})
const emit = defineEmits(['close', 'saved'])

const editId = ref(null)
const saving = ref(false)
const error = ref('')
const form = reactive({ name: '', service_id: null, category: '', is_official: true, is_serialized: false, unit_of_measure: '', price: null, code: '' })

watch(() => props.open, (o) => {
  if (!o) return
  error.value = ''
  const n = props.item
  editId.value = n?.id || null
  Object.assign(form, n ? {
    name: n.name, service_id: n.service_id, category: n.category || '', is_official: n.is_official,
    is_serialized: n.is_serialized, unit_of_measure: n.unit_of_measure || '', price: n.price, code: n.code || '',
  } : {
    name: '', service_id: props.defaultServiceId, category: '', is_official: true,
    is_serialized: false, unit_of_measure: '', price: null, code: '',
  })
})

async function save() {
  if (!form.name || !form.service_id) { error.value = 'Назва і служба обов’язкові'; return }
  saving.value = true; error.value = ''
  try {
    const payload = {
      name: form.name, service_id: form.service_id, category: form.category || null,
      is_official: form.is_official !== false, is_serialized: !!form.is_serialized,
      unit_of_measure: form.unit_of_measure || null,
      price: form.price ? Number(form.price) : null, code: form.code || null,
    }
    const { data } = editId.value ? await updateNomenclature(editId.value, payload) : await createNomenclature(payload)
    emit('saved', data)
    emit('close')
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Помилка збереження'
  } finally { saving.value = false }
}
</script>

<style scoped>
.overlay { position:fixed; inset:0; background:rgba(15,23,42,0.35); display:none; align-items:flex-start; justify-content:center; padding:60px 20px; z-index:1300; }
.overlay.open { display:flex; }
.modal { background:var(--surface); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.15); width:min(460px,100%); }
.modal-head { padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; }
.modal-title { flex:1; font-weight:700; font-size:14px; } .modal-close { border:none; background:transparent; font-size:16px; color:var(--text-light); cursor:pointer; }
.modal-body { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
.fl { font-size:12px; color:var(--text-light); font-weight:600; margin-top:8px; }
.fi { padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:14px; }
.err { margin-top:10px; padding:8px 10px; background:#fee2e2; color:#991b1b; font-size:12.5px; border-radius:3px; }
.modal-foot { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }
.btn-sec { padding:7px 14px; background:transparent; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:inherit; font-size:13px; cursor:pointer; }
.btn-pri { padding:7px 16px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.btn-pri:disabled { opacity:0.5; }
</style>
