<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <div class="text-h4">✅ Compliance</div>
      <q-space />
      <q-btn unelevated color="primary" icon="add" label="Neuer Check" @click="showCreate = true" />
    </div>

    <!-- Filter -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-4">
        <q-select v-model="filterCategory" label="Kategorie" outlined clearable dense
          :options="categories" @update:model-value="loadData" />
      </div>
      <div class="col-12 col-md-4">
        <q-select v-model="filterFulfilled" label="Status" outlined clearable dense
          :options="[{ label: 'Erfüllt', value: true }, { label: 'Nicht erfüllt', value: false }]"
          emit-value map-options @update:model-value="loadData" />
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div v-for="cat in categories" :key="cat" class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center">
              <q-badge :color="categoryColor(cat)" size="lg" class="q-mr-sm">{{ cat }}</q-badge>
              <q-space />
              <q-badge :color="catRate(cat) >= 80 ? 'green' : catRate(cat) >= 50 ? 'amber' : 'red'">
                {{ catRate(cat).toFixed(0) }}%
              </q-badge>
            </div>
            <q-linear-progress :value="catRate(cat) / 100" class="q-mt-sm"
              :color="catRate(cat) >= 80 ? 'green' : catRate(cat) >= 50 ? 'amber' : 'red'" size="8px" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Table -->
    <q-table
      :rows="store.complianceChecks"
      :columns="columns"
      row-key="id"
      :loading="store.loading"
      flat bordered
    >
      <template v-slot:body-cell-fulfilled="props">
        <q-td :props="props">
          <q-badge :color="props.row.fulfilled ? 'green' : 'red'">
            {{ props.row.fulfilled ? '✅ Erfüllt' : '❌ Offen' }}
          </q-badge>
        </q-td>
      </template>
      <template v-slot:body-cell-category="props">
        <q-td :props="props">
          <q-badge :color="categoryColor(props.row.category)">{{ props.row.category }}</q-badge>
        </q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat round dense icon="check_circle" color="green" @click="toggleFulfilled(props.row)"
            :disable="props.row.fulfilled" />
          <q-btn flat round dense icon="edit" color="primary" @click="editCheck(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Create/Edit Dialog -->
    <q-dialog v-model="showCreate">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">{{ editingId ? 'Check bearbeiten' : 'Neuer Compliance-Check' }}</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="form.title" label="Titel" outlined class="q-mb-md" />
          <q-select v-model="form.category" label="Kategorie" outlined :options="categories" class="q-mb-md" />
          <q-input v-model="form.requirement" label="Anforderung" outlined type="textarea" rows="3" class="q-mb-md" />
          <q-input v-model="form.due_date" label="Fällig am" outlined type="date" class="q-mb-md" />
          <q-input v-if="editingId" v-model="form.evidence" label="Nachweis" outlined type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup />
          <q-btn unelevated color="primary" :label="editingId ? 'Speichern' : 'Erstellen'" @click="submit" :loading="submitting" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQmStore } from '@/stores/qm'
import { Notify, useQuasar } from 'quasar'

const store = useQmStore()
const $q = useQuasar()

const showCreate = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const filterCategory = ref<string | null>(null)
const filterFulfilled = ref<boolean | null>(null)

const categories = [
  'Patientenorientierung', 'Mitarbeiterorientierung', 'Prozessorientierung',
  'Führung und Verantwortung', 'Fehlerkultur', 'Kommunikation'
]

const form = ref({ title: '', category: '', requirement: '', due_date: '', evidence: '' })

const columns = [
  { name: 'title', label: 'Titel', field: 'title', align: 'left' as const, sortable: true },
  { name: 'category', label: 'Kategorie', field: 'category', align: 'left' as const },
  { name: 'requirement', label: 'Anforderung', field: 'requirement', align: 'left' as const, style: 'max-width: 300px; white-space: normal;' },
  { name: 'fulfilled', label: 'Status', field: 'fulfilled', align: 'center' as const },
  { name: 'due_date', label: 'Fällig', field: (row: any) => row.due_date || '—', align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const }
]

onMounted(() => loadData())

function loadData() {
  const params: any = {}
  if (filterCategory.value) params.category = filterCategory.value
  if (filterFulfilled.value !== null) params.fulfilled = filterFulfilled.value
  store.fetchCompliance(params)
}

function catRate(cat: string): number {
  const items = store.complianceChecks.filter((c: any) => c.category === cat)
  if (items.length === 0) return 100
  return (items.filter((c: any) => c.fulfilled).length / items.length) * 100
}

function categoryColor(cat: string): string {
  const map: Record<string, string> = {
    'Patientenorientierung': 'blue', 'Mitarbeiterorientierung': 'teal',
    'Prozessorientierung': 'cyan', 'Führung und Verantwortung': 'deep-orange',
    'Fehlerkultur': 'red', 'Kommunikation': 'light-blue'
  }
  return map[cat] || 'grey'
}

async function toggleFulfilled(check: any) {
  await store.updateCompliance(check.id, { fulfilled: true })
  Notify.create({ type: 'positive', message: 'Als erfüllt markiert' })
}

function editCheck(check: any) {
  editingId.value = check.id
  form.value = {
    title: check.title, category: check.category,
    requirement: check.requirement, due_date: check.due_date || '',
    evidence: check.evidence || ''
  }
  showCreate.value = true
}

async function submit() {
  if (!form.value.title || !form.value.category || !form.value.requirement) return
  submitting.value = true
  try {
    if (editingId.value) {
      await store.updateCompliance(editingId.value, form.value)
    } else {
      await store.createCompliance(form.value)
    }
    showCreate.value = false
    editingId.value = null
    form.value = { title: '', category: '', requirement: '', due_date: '', evidence: '' }
    Notify.create({ type: 'positive', message: editingId.value ? 'Gespeichert' : 'Erstellt' })
  } finally {
    submitting.value = false
  }
}

function confirmDelete(check: any) {
  $q.dialog({
    title: 'Check löschen',
    message: `"${check.title}" wirklich löschen?`,
    cancel: true, persistent: true
  }).onOk(async () => {
    await store.deleteCompliance(check.id)
    Notify.create({ type: 'info', message: 'Gelöscht' })
  })
}
</script>
