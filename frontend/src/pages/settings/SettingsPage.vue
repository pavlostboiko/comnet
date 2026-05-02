<template>
  <div class="page-wrap">
    <TopBar />

    <div class="content-scroll">
      <div class="tile">
        <!-- Tile header with tabs and context actions -->
        <div class="tile-header">
          <span class="tile-title">Налаштування</span>
          <div class="tile-tabs">
            <button class="tt-btn" :class="{ on: activeTab === 'general' }" @click="activeTab = 'general'">
              Підрозділ
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'persons' }" @click="activeTab = 'persons'">
              Особи
              <span class="tab-count">{{ persons.length }}</span>
            </button>
            <button class="tt-btn" :class="{ on: activeTab === 'optypes' }" @click="activeTab = 'optypes'">
              Типи операцій
            </button>
          </div>
          <div class="tile-actions">
            <!-- Persons tab actions -->
            <template v-if="activeTab === 'persons'">
              <div class="tile-search" :class="{ expanded: searchFocused }">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  v-model="personSearch"
                  placeholder="Пошук…"
                  @focus="searchFocused = true"
                  @blur="searchFocused = false"
                />
              </div>
              <button class="btn-primary" @click="openPersonModal()">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Додати особу
              </button>
            </template>
            <!-- Op types tab actions -->
            <template v-if="activeTab === 'optypes'">
              <button class="btn-primary" @click="openOptypeModal(null)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Додати тип
              </button>
            </template>
          </div>
        </div>

        <!-- TAB: ПІДРОЗДІЛ -->
        <div v-show="activeTab === 'general'">
          <div class="form-card">
            <div class="form-grid">
              <div class="form-group full">
                <label class="form-label">Найменування <small>повне офіційне</small></label>
                <input v-model="unit.name" class="form-input" placeholder="Назва підрозділу" />
              </div>
              <div class="form-group">
                <label class="form-label">Скорочене найменування</label>
                <input v-model="unit.short_name" class="form-input" placeholder="Скорочена назва" />
              </div>
              <div class="form-group">
                <label class="form-label">Код ЄДРПОУ</label>
                <input v-model="unit.edrpou" class="form-input mono" placeholder="12345678" />
              </div>
              <div class="form-group">
                <label class="form-label">Місце дислокації</label>
                <input v-model="unit.location" class="form-input" placeholder="м. Київ" />
              </div>
            </div>
          </div>
          <div class="form-foot">
            <button class="btn-primary" @click="saveUnit">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
                <polyline points="17 21 17 13 7 13 7 21" />
                <polyline points="7 3 7 8 15 8" />
              </svg>
              Зберегти
            </button>
          </div>
        </div>

        <!-- TAB: ОСОБИ -->
        <div v-show="activeTab === 'persons'">
          <table>
            <thead>
              <tr>
                <th>ПІБ</th>
                <th>Звання</th>
                <th>Посада</th>
                <th>Підрозділ</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in filteredPersons" :key="p.id">
                <td class="td-name">{{ p.search_name || [p.last_name, p.first_name, p.patronymic].filter(Boolean).join(' ') || '—' }}</td>
                <td>{{ p.rank || '—' }}</td>
                <td>{{ p.position || '—' }}</td>
                <td>{{ p.unit || '—' }}</td>
                <td>
                  <span class="status-badge" :class="p.is_active ? 's-active' : 's-inactive'">
                    {{ p.is_active ? 'Активний' : 'Неактивний' }}
                  </span>
                </td>
                <td>
                  <div class="acts">
                    <button class="act e" title="Редагувати" @click="openPersonModal(p)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    </button>
                    <button class="act d" title="Видалити" @click="confirmDeletePerson(p)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-1 14H6L5 6" />
                        <path d="M10 11v6M14 11v6" />
                        <path d="M9 6V4h6v2" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredPersons.length === 0">
                <td colspan="6" style="text-align:center; color:var(--text-light); padding:32px">
                  {{ personSearch ? 'Нічого не знайдено' : 'Немає осіб' }}
                </td>
              </tr>
            </tbody>
          </table>
          <div class="t-foot">{{ persons.length }} осіб</div>
        </div>

        <!-- TAB: ТИПИ ОПЕРАЦІЙ -->
        <div v-show="activeTab === 'optypes'">
          <div v-if="opTypes.length === 0" style="padding:32px; text-align:center; color:var(--text-light)">
            Немає типів операцій
          </div>
          <div v-for="ot in opTypes" :key="ot.id" class="optype-group">
            <div class="optype-parent" @click="toggleOpType(ot.id)">
              <span class="optype-chevron" :class="{ open: openOpTypes.has(ot.id) }">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </span>
              <span class="optype-parent-name">{{ ot.name }}</span>
              <span class="optype-sub-count">{{ ot.details.length }}</span>
              <div class="optype-parent-acts">
                <button class="act e" title="Редагувати" @click.stop="openOptypeModal(ot)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button class="act d" title="Видалити" @click.stop="confirmDeleteOpType(ot)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14H6L5 6" />
                    <path d="M10 11v6M14 11v6" />
                    <path d="M9 6V4h6v2" />
                  </svg>
                </button>
              </div>
            </div>
            <div v-show="openOpTypes.has(ot.id)" class="optype-children">
              <div v-for="d in ot.details" :key="d.id" class="optype-child">
                <span class="optype-child-dot"></span>
                <span class="optype-child-name">{{ d.name }}</span>
                <div class="optype-child-acts">
                  <button class="act e" title="Редагувати" @click="openDetailModal(d, ot)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </button>
                  <button class="act d" title="Видалити" @click="confirmDeleteDetail(d)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14H6L5 6" />
                      <path d="M10 11v6M14 11v6" />
                      <path d="M9 6V4h6v2" />
                    </svg>
                  </button>
                </div>
              </div>
              <button class="btn-add-sub" @click="openDetailModal(null, ot)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Додати підтип
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== PERSON MODAL ====== -->
    <div class="overlay" :class="{ open: personModalOpen }" @click.self="personModalOpen = false">
      <div class="modal-wide">
        <div class="modal-head">
          <span class="modal-title">{{ editingPerson ? 'Редагувати особу' : 'Додати особу' }}</span>
          <button class="modal-close" @click="personModalOpen = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <!-- Name block -->
          <div>
            <div class="fsec">Прізвище, ім'я, по батькові</div>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Прізвище</label>
                <input v-model="pForm.last_name" class="form-input" placeholder="Іваненко"
                  @input="updateSearchName" />
              </div>
              <div class="form-group">
                <label class="form-label">Прізвище <small>(родовий)</small></label>
                <input v-model="pForm.last_name_genitive" class="form-input" placeholder="Іваненка" />
              </div>
              <div class="form-group">
                <label class="form-label">Ім'я</label>
                <input v-model="pForm.first_name" class="form-input" placeholder="Іван"
                  @input="updateSearchName" />
              </div>
              <div class="form-group">
                <label class="form-label">Ім'я <small>(родовий)</small></label>
                <input v-model="pForm.first_name_genitive" class="form-input" placeholder="Івана" />
              </div>
              <div class="form-group">
                <label class="form-label">По батькові</label>
                <input v-model="pForm.patronymic" class="form-input" placeholder="Іванович"
                  @input="updateSearchName" />
              </div>
              <div class="form-group">
                <label class="form-label">По батькові <small>(родовий)</small></label>
                <input v-model="pForm.patronymic_genitive" class="form-input" placeholder="Івановича" />
              </div>
            </div>
          </div>

          <hr class="divider" />

          <!-- Rank/position block -->
          <div>
            <div class="fsec">Звання та посада</div>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Звання</label>
                <input v-model="pForm.rank" class="form-input" placeholder="Капітан" />
              </div>
              <div class="form-group">
                <label class="form-label">Звання <small>(родовий)</small></label>
                <input v-model="pForm.rank_genitive" class="form-input" placeholder="Капітана" />
              </div>
              <div class="form-group">
                <label class="form-label">Посада</label>
                <input v-model="pForm.position" class="form-input" placeholder="Командир роти" />
              </div>
              <div class="form-group">
                <label class="form-label">Посада <small>(родовий)</small></label>
                <input v-model="pForm.position_genitive" class="form-input" placeholder="Командира роти" />
              </div>
            </div>
          </div>

          <hr class="divider" />

          <!-- Unit/status block -->
          <div>
            <div class="fsec">Підрозділ та статус</div>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Підрозділ</label>
                <input v-model="pForm.unit" class="form-input" placeholder="1 рота" />
              </div>
              <div class="form-group">
                <label class="form-label">Підрозділ <small>(місцевий відмінок)</small></label>
                <input v-model="pForm.unit_locative" class="form-input" placeholder="у 1-й роті" />
              </div>
              <div class="form-group">
                <label class="form-label">Скорочення <small>(авто)</small></label>
                <input v-model="pForm.search_name" class="form-input" placeholder="Іваненко І.І." disabled />
                <span class="form-hint">Формується автоматично</span>
              </div>
              <div class="form-group status-group">
                <label class="form-label">Статус</label>
                <div class="toggle-wrap">
                  <button
                    class="toggle"
                    :class="{ on: pForm.is_active }"
                    @click="pForm.is_active = !pForm.is_active"
                  >
                    <div class="toggle-knob"></div>
                  </button>
                  <span class="toggle-label">{{ pForm.is_active ? 'Активний' : 'Неактивний' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn-cancel" @click="personModalOpen = false">Скасувати</button>
          <button class="btn-primary" @click="savePerson">Зберегти</button>
        </div>
      </div>
    </div>

    <!-- ====== OPTYPE MODAL ====== -->
    <div class="overlay" :class="{ open: optypeModalOpen }" @click.self="optypeModalOpen = false">
      <div class="modal-sm-box">
        <div class="modal-head">
          <span class="modal-title">{{ optypeModalTitle }}</span>
          <button class="modal-close" @click="optypeModalOpen = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Назва</label>
            <input v-model="otForm.name" class="form-input" placeholder="Назва типу" @keydown.enter="saveOptype" />
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn-cancel" @click="optypeModalOpen = false">Скасувати</button>
          <button class="btn-primary" @click="saveOptype">Зберегти</button>
        </div>
      </div>
    </div>

    <!-- TOAST -->
    <div class="toast" :class="{ show: toastVisible }">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import TopBar from '../../components/TopBar.vue'
import {
  getUnit, updateUnit,
  getOpTypes, createOpType, updateOpType, deleteOpType,
  createOpTypeDetail, updateOpTypeDetail, deleteOpTypeDetail,
  getPersons, createPerson, updatePerson, deletePerson,
} from '../../api/settings.js'

// ── State ──────────────────────────────────────────────────────────────────

const activeTab = ref('general')

// Unit
const unit = reactive({ name: '', short_name: '', edrpou: '', location: '' })

// Persons
const persons = ref([])
const personSearch = ref('')
const searchFocused = ref(false)

// Op Types
const opTypes = ref([])
const openOpTypes = ref(new Set())

// Toast
const toastMsg = ref('')
const toastVisible = ref(false)
let toastTimer = null

// ── Person modal ───────────────────────────────────────────────────────────

const personModalOpen = ref(false)
const editingPerson = ref(null)
const pForm = reactive({
  last_name: '', last_name_genitive: '',
  first_name: '', first_name_genitive: '',
  patronymic: '', patronymic_genitive: '',
  rank: '', rank_genitive: '',
  position: '', position_genitive: '',
  unit: '', unit_locative: '',
  search_name: '',
  is_active: true,
})

// ── Op type modal ──────────────────────────────────────────────────────────

const optypeModalOpen = ref(false)
const optypeModalTitle = ref('Додати тип операції')
const editingOpType = ref(null)       // parent OpType being edited
const editingDetail = ref(null)       // OpTypeDetail being edited
const detailParentId = ref(null)      // parent id when adding/editing detail
const isDetailMode = ref(false)       // true = editing a detail, false = parent
const otForm = reactive({ name: '' })

// ── Computed ───────────────────────────────────────────────────────────────

const filteredPersons = computed(() => {
  const q = personSearch.value.toLowerCase().trim()
  if (!q) return persons.value
  return persons.value.filter(p => {
    const haystack = [p.search_name, p.last_name, p.first_name, p.patronymic, p.rank, p.position, p.unit]
      .filter(Boolean).join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([loadUnit(), loadPersons(), loadOpTypes()])
})

// ── Loaders ────────────────────────────────────────────────────────────────

async function loadUnit() {
  const { data } = await getUnit()
  Object.assign(unit, data)
}

async function loadPersons() {
  const { data } = await getPersons()
  persons.value = data
}

async function loadOpTypes() {
  const { data } = await getOpTypes()
  opTypes.value = data
}

// ── Unit actions ───────────────────────────────────────────────────────────

async function saveUnit() {
  await updateUnit({ name: unit.name, short_name: unit.short_name, edrpou: unit.edrpou, location: unit.location })
  showToast('Дані підрозділу збережено')
}

// ── Person actions ─────────────────────────────────────────────────────────

function openPersonModal(person = null) {
  editingPerson.value = person
  if (person) {
    Object.assign(pForm, { ...person })
  } else {
    Object.assign(pForm, {
      last_name: '', last_name_genitive: '',
      first_name: '', first_name_genitive: '',
      patronymic: '', patronymic_genitive: '',
      rank: '', rank_genitive: '',
      position: '', position_genitive: '',
      unit: '', unit_locative: '',
      search_name: '',
      is_active: true,
    })
  }
  personModalOpen.value = true
}

function updateSearchName() {
  const parts = [pForm.last_name]
  if (pForm.first_name) parts.push(pForm.first_name[0] + '.')
  if (pForm.patronymic) parts.push(pForm.patronymic[0] + '.')
  pForm.search_name = parts.filter(Boolean).join(' ')
}

async function savePerson() {
  const payload = { ...pForm }
  if (editingPerson.value) {
    await updatePerson(editingPerson.value.id, payload)
    showToast('Особу збережено')
  } else {
    await createPerson(payload)
    showToast('Особу додано')
  }
  personModalOpen.value = false
  await loadPersons()
}

async function confirmDeletePerson(p) {
  if (!confirm(`Видалити "${p.search_name || p.last_name}"?`)) return
  await deletePerson(p.id)
  showToast('Особу видалено')
  await loadPersons()
}

// ── Op Type actions ────────────────────────────────────────────────────────

function toggleOpType(id) {
  const s = new Set(openOpTypes.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  openOpTypes.value = s
}

function openOptypeModal(ot) {
  isDetailMode.value = false
  editingOpType.value = ot
  editingDetail.value = null
  otForm.name = ot ? ot.name : ''
  optypeModalTitle.value = ot ? 'Редагувати тип операції' : 'Додати тип операції'
  optypeModalOpen.value = true
}

function openDetailModal(detail, parentOt) {
  isDetailMode.value = true
  editingDetail.value = detail
  editingOpType.value = null
  detailParentId.value = parentOt.id
  otForm.name = detail ? detail.name : ''
  optypeModalTitle.value = detail ? 'Редагувати підтип' : 'Додати підтип'
  optypeModalOpen.value = true
}

async function saveOptype() {
  if (!otForm.name.trim()) return

  if (isDetailMode.value) {
    // Saving a detail
    if (editingDetail.value) {
      await updateOpTypeDetail(editingDetail.value.id, { name: otForm.name })
      showToast('Підтип збережено')
    } else {
      await createOpTypeDetail({ op_type_id: detailParentId.value, name: otForm.name })
      showToast('Підтип додано')
    }
  } else {
    // Saving a parent op type
    if (editingOpType.value) {
      await updateOpType(editingOpType.value.id, { name: otForm.name })
      showToast('Тип операції збережено')
    } else {
      await createOpType({ name: otForm.name })
      showToast('Тип операції додано')
    }
  }

  optypeModalOpen.value = false
  await loadOpTypes()
}

async function confirmDeleteOpType(ot) {
  if (!confirm(`Видалити тип "${ot.name}" та всі підтипи?`)) return
  await deleteOpType(ot.id)
  showToast('Тип операції видалено')
  await loadOpTypes()
}

async function confirmDeleteDetail(d) {
  if (!confirm(`Видалити підтип "${d.name}"?`)) return
  await deleteOpTypeDetail(d.id)
  showToast('Підтип видалено')
  await loadOpTypes()
}

// ── Toast ──────────────────────────────────────────────────────────────────

function showToast(msg) {
  toastMsg.value = msg
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2500)
}
</script>

<style scoped>
.page-wrap {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.content-scroll::-webkit-scrollbar { width: 6px; }
.content-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* TILE */
.tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  animation: tileIn 0.25s ease-out both;
}

@keyframes tileIn { from { opacity: 0; transform: translateY(5px); } }

.tile-header {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--border-light);
  flex-wrap: wrap;
}

.tile-title { font-size: 15px; font-weight: 700; }

.tile-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg);
  padding: 3px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
}

.tt-btn {
  padding: 5px 13px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-light);
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 5px;
}

.tt-btn:hover { color: var(--text-mid); }

.tt-btn.on {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  font-weight: 600;
}

.tab-count {
  font-family: 'DM Mono', monospace;
  font-size: 10.5px;
  color: var(--text-light);
  background: var(--border-light);
  padding: 0 6px;
  border-radius: 3px;
  line-height: 17px;
}

.tile-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
  align-items: center;
}

/* SEARCH */
.tile-search {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  width: 220px;
  transition: all 0.2s;
}

.tile-search.expanded,
.tile-search:focus-within {
  border-color: var(--accent);
  width: 270px;
}

.tile-search input {
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  outline: none;
  width: 100%;
}

.tile-search input::placeholder { color: var(--text-light); }

/* FORM */
.form-card { padding: 20px 24px; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group.full { grid-column: 1 / -1; }

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-mid);
}

.form-label small {
  font-weight: 400;
  color: var(--text-light);
  margin-left: 4px;
}

.form-input {
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 13.5px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  transition: all 0.15s;
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
  background: var(--surface);
}

.form-input::placeholder { color: var(--text-light); }
.form-input:disabled { opacity: 0.5; cursor: not-allowed; }

.form-input.mono {
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.05em;
}

.form-hint { font-size: 11.5px; color: var(--text-light); }

.form-foot {
  padding: 12px 24px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: flex-end;
}

/* BUTTONS */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-primary:hover { background: var(--accent-dark); }

.btn-cancel {
  padding: 8px 14px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-mid);
  cursor: pointer;
  transition: all 0.12s;
}

.btn-cancel:hover { border-color: var(--text-light); color: var(--text); }

/* TABLE */
table { width: 100%; border-collapse: collapse; }

thead tr { background: var(--bg); }

th {
  padding: 9px var(--cell-pad-x);
  text-align: left;
  font-size: var(--font-header);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-light);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

th:first-child { padding-left: 20px; }
th:last-child { padding-right: 20px; width: 52px; }

tbody tr {
  border-bottom: 1px solid var(--border-light);
  transition: background 0.1s;
}

tbody tr:last-child { border-bottom: none; }
tbody tr:nth-child(even) { background: #f8fafc; }
tbody tr:hover { background: var(--row-hover) !important; }

td {
  padding: var(--row-pad-y) var(--cell-pad-x);
  font-size: var(--font-body);
  color: var(--text-mid);
  vertical-align: middle;
}

td:first-child { padding-left: 20px; }
td:last-child { padding-right: 20px; }

.td-name { font-weight: 600; color: var(--text); }

.t-foot {
  padding: 9px 20px;
  border-top: 1px solid var(--border-light);
  font-size: 13px;
  color: var(--text-light);
  background: var(--bg);
}

/* STATUS BADGE */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11.5px;
  font-weight: 600;
}

.s-active { background: var(--green-bg); color: var(--green-text); }
.s-inactive { background: var(--accent-light); color: var(--text-light); }

/* ROW ACTIONS */
.acts {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.12s;
  justify-content: flex-end;
}

tbody tr:hover .acts { opacity: 1; }

.act {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-light);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s;
}

.act svg { width: 14px; height: 14px; }
.act:hover.e { background: var(--accent-light); color: var(--accent); }
.act:hover.d { background: var(--red-bg); color: var(--red); }

/* OP TYPES TREE */
.optype-group { border-bottom: 1px solid var(--border-light); }
.optype-group:last-child { border-bottom: none; }

.optype-parent {
  display: flex;
  align-items: center;
  padding: 11px 20px;
  gap: 10px;
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}

.optype-parent:hover { background: var(--row-hover); }

.optype-chevron {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-light);
  transition: transform 0.15s;
  flex-shrink: 0;
}

.optype-chevron.open { transform: rotate(90deg); }

.optype-parent-name { font-size: 14px; font-weight: 600; color: var(--text); flex: 1; }

.optype-sub-count {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--text-light);
  background: var(--border-light);
  padding: 1px 7px;
  border-radius: var(--radius-sm);
}

.optype-parent-acts {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.12s;
}

.optype-parent:hover .optype-parent-acts { opacity: 1; }

.optype-children {
  background: var(--bg);
  border-top: 1px solid var(--border-light);
}

.optype-child {
  display: flex;
  align-items: center;
  padding: 8px 20px 8px 52px;
  gap: 10px;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.1s;
}

.optype-child:hover { background: var(--row-hover); }

.optype-child-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
}

.optype-child-name { font-size: 13.5px; color: var(--text-mid); flex: 1; }

.optype-child-acts {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.12s;
}

.optype-child:hover .optype-child-acts { opacity: 1; }

.btn-add-sub {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 20px 7px 52px;
  font-size: 12.5px;
  color: var(--text-light);
  cursor: pointer;
  background: none;
  border: none;
  font-family: inherit;
  width: 100%;
  text-align: left;
  transition: color 0.12s;
}

.btn-add-sub:hover { color: var(--accent); }

/* TOGGLE */
.toggle-wrap { display: flex; align-items: center; gap: 10px; }

.toggle {
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: var(--border);
  border: none;
  cursor: pointer;
  position: relative;
  transition: background 0.15s;
  flex-shrink: 0;
  padding: 0;
}

.toggle.on { background: var(--accent); }

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  transition: transform 0.15s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  pointer-events: none;
}

.toggle.on .toggle-knob { transform: translateX(16px); }

.toggle-label { font-size: 13.5px; color: var(--text-mid); }

.status-group { justify-content: flex-end; padding-bottom: 6px; }
.status-group .toggle-wrap { margin-top: auto; }

/* FSEC */
.fsec {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-light);
  margin-bottom: 10px;
}

.divider {
  border: none;
  border-top: 1px solid var(--border-light);
}

/* OVERLAY */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(2px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}

.overlay.open { opacity: 1; pointer-events: all; }

.modal-wide {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xl);
  width: 760px;
  max-width: calc(100vw - 48px);
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  transform: translateY(12px) scale(0.98);
  transition: transform 0.2s;
}

.modal-sm-box {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xl);
  width: 400px;
  max-width: calc(100vw - 48px);
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  transform: translateY(12px) scale(0.98);
  transition: transform 0.2s;
}

.overlay.open .modal-wide,
.overlay.open .modal-sm-box { transform: translateY(0) scale(1); }

.modal-head {
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}

.modal-title { font-size: 17px; font-weight: 700; }

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.modal-foot {
  padding: 14px 24px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  position: sticky;
  bottom: 0;
  background: var(--surface);
}

.modal-close {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-light);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s;
}

.modal-close:hover { background: var(--bg); color: var(--text); }

/* TOAST */
.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(80px);
  background: var(--text);
  color: white;
  padding: 11px 20px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 500;
  box-shadow: var(--shadow-xl);
  z-index: 200;
  opacity: 0;
  transition: all 0.25s;
  white-space: nowrap;
}

.toast.show {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}
</style>
