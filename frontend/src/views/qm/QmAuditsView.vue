<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <div class="text-h4">🔍 Audits</div>
      <q-space />
      <q-btn unelevated color="primary" icon="add" label="Neues Audit" @click="showCreate = true" />
    </div>

    <!-- Audit Liste -->
    <q-table
      :rows="store.audits"
      :columns="columns"
      row-key="id"
      :loading="store.loading"
      flat bordered
      @row-click="(_evt: Event, row: any) => openAudit(row.id)"
      class="cursor-pointer"
    >
      <template v-slot:body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="props.row.status === 'Abgeschlossen' ? 'green' : 'orange'">
            {{ props.row.status }}
          </q-badge>
        </q-td>
      </template>
      <template v-slot:body-cell-completion_percentage="props">
        <q-td :props="props">
          <q-linear-progress :value="props.row.completion_percentage / 100" size="20px" :color="props.row.completion_percentage === 100 ? 'green' : 'orange'" class="q-border-radius-sm">
            <div class="absolute-full flex flex-center">
              <q-badge color="white" text-color="dark" :label="`${props.row.completion_percentage.toFixed(0)}%`" />
            </div>
          </q-linear-progress>
        </q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat round dense icon="delete" color="negative" @click.stop="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Audit Detail Dialog -->
    <q-dialog v-model="showDetail" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card v-if="store.currentAudit">
        <q-bar class="bg-primary text-white">
          <div class="text-weight-bold">{{ store.currentAudit.title }}</div>
          <q-space />
          <q-badge color="white" :text-color="store.currentAudit.status === 'Abgeschlossen' ? 'green' : 'orange'">
            {{ store.currentAudit.status }}
          </q-badge>
          <q-btn dense flat icon="close" v-close-popup class="q-ml-sm" />
        </q-bar>

        <q-card-section class="q-pa-lg">
          <div class="row q-col-gutter-md q-mb-lg">
            <div class="col-auto">
              <q-chip icon="person" color="primary" text-color="white">{{ store.currentAudit.auditor }}</q-chip>
            </div>
            <div class="col-auto">
              <q-chip icon="percent">{{ store.currentAudit.completion_percentage.toFixed(0) }}% beantwortet</q-chip>
            </div>
          </div>

          <!-- Fragen -->
          <div class="text-h6 q-mb-md">Fragenkatalog</div>
          <q-list bordered separator>
            <q-item v-for="q in store.currentAudit.questions" :key="q.question_id">
              <q-item-section>
                <q-item-label>{{ q.question_text }}</q-item-label>
                <q-item-label caption>
                  <q-badge :color="categoryColor(q.category)" class="q-mr-xs">{{ q.category }}</q-badge>
                </q-item-label>
                <q-item-label v-if="q.notes" caption class="q-mt-xs text-italic">📝 {{ q.notes }}</q-item-label>
              </q-item-section>
              <q-item-section side v-if="store.currentAudit.status !== 'Abgeschlossen'">
                <div class="q-gutter-xs">
                  <q-btn :flat="q.answer !== 'Ja'" :unelevated="q.answer === 'Ja'" dense
                    color="green" label="Ja" size="sm"
                    @click="answer(q.question_id, 'Ja')" />
                  <q-btn :flat="q.answer !== 'Nein'" :unelevated="q.answer === 'Nein'" dense
                    color="red" label="Nein" size="sm"
                    @click="answer(q.question_id, 'Nein')" />
                  <q-btn flat dense icon="edit_note" size="sm" @click="openNotes(q)" />
                </div>
              </q-item-section>
              <q-item-section side v-else>
                <q-badge :color="q.answer === 'Ja' ? 'green' : q.answer === 'Nein' ? 'red' : 'grey'">
                  {{ q.answer || '—' }}
                </q-badge>
              </q-item-section>
            </q-item>
          </q-list>

          <!-- Finalize -->
          <div v-if="store.currentAudit.status !== 'Abgeschlossen'" class="q-mt-lg text-center">
            <q-btn unelevated color="green" icon="check_circle" label="Audit finalisieren"
              size="lg" @click="finalize" :loading="finalizing"
              :disable="store.currentAudit.completion_percentage < 100" />
            <div v-if="store.currentAudit.completion_percentage < 100" class="text-caption text-grey-7 q-mt-sm">
              Alle Fragen müssen beantwortet sein
            </div>
          </div>

          <!-- Findings & Actions -->
          <template v-if="store.currentAudit.findings?.length">
            <div class="text-h6 q-mt-xl q-mb-md">⚠️ Findings</div>
            <q-list bordered separator>
              <q-item v-for="(f, i) in store.currentAudit.findings" :key="i">
                <q-item-section>
                  <q-item-label>{{ f.finding }}</q-item-label>
                  <q-item-label v-if="f.notes" caption>{{ f.notes }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </template>

          <template v-if="store.currentAudit.actions?.length">
            <div class="text-h6 q-mt-lg q-mb-md">📋 Maßnahmen</div>
            <q-list bordered separator>
              <q-item v-for="(a, i) in store.currentAudit.actions" :key="i">
                <q-item-section>
                  <q-item-label>{{ a.action }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </template>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Create Dialog -->
    <q-dialog v-model="showCreate">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Neues Audit</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="newAudit.title" label="Titel" outlined class="q-mb-md" />
          <q-input v-model="newAudit.auditor" label="Auditor" outlined />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup />
          <q-btn unelevated color="primary" label="Erstellen" @click="create" :loading="creating" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Notes Dialog -->
    <q-dialog v-model="showNotes">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Notiz</div>
          <div class="text-caption">{{ notesQuestion?.question_text }}</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="notesText" label="Notizen" outlined type="textarea" rows="4" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup />
          <q-btn unelevated color="primary" label="Speichern" @click="saveNotes" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQmStore } from '@/stores/qm'
import { Notify, useQuasar } from 'quasar'

const store = useQmStore()
const $q = useQuasar()

const showCreate = ref(false)
const showDetail = ref(false)
const showNotes = ref(false)
const creating = ref(false)
const finalizing = ref(false)
const newAudit = ref({ title: '', auditor: '' })
const notesQuestion = ref<any>(null)
const notesText = ref('')

const columns = [
  { name: 'title', label: 'Titel', field: 'title', align: 'left' as const, sortable: true },
  { name: 'auditor', label: 'Auditor', field: 'auditor', align: 'left' as const },
  { name: 'status', label: 'Status', field: 'status', align: 'center' as const },
  { name: 'completion_percentage', label: 'Fortschritt', field: 'completion_percentage', align: 'center' as const },
  { name: 'created_at', label: 'Erstellt', field: (row: any) => new Date(row.created_at).toLocaleDateString('de-DE'), align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const }
]

onMounted(() => store.fetchAudits())

async function openAudit(id: number) {
  await store.fetchAudit(id)
  showDetail.value = true
}

async function create() {
  if (!newAudit.value.title || !newAudit.value.auditor) return
  creating.value = true
  try {
    const audit = await store.createAudit(newAudit.value)
    showCreate.value = false
    newAudit.value = { title: '', auditor: '' }
    Notify.create({ type: 'positive', message: 'Audit erstellt mit 10 Fragen' })
    await openAudit(audit.id)
  } finally {
    creating.value = false
  }
}

async function answer(questionId: string, ans: string) {
  if (!store.currentAudit) return
  await store.answerQuestion(store.currentAudit.id, questionId, { answer: ans })
}

function openNotes(q: any) {
  notesQuestion.value = q
  notesText.value = q.notes || ''
  showNotes.value = true
}

async function saveNotes() {
  if (!store.currentAudit || !notesQuestion.value) return
  await store.answerQuestion(store.currentAudit.id, notesQuestion.value.question_id, {
    answer: notesQuestion.value.answer || 'Überspringen',
    notes: notesText.value
  })
  showNotes.value = false
}

async function finalize() {
  if (!store.currentAudit) return
  finalizing.value = true
  try {
    await store.finalizeAudit(store.currentAudit.id)
    Notify.create({ type: 'positive', message: 'Audit finalisiert' })
  } finally {
    finalizing.value = false
  }
}

function confirmDelete(audit: any) {
  $q.dialog({
    title: 'Audit löschen',
    message: `"${audit.title}" wirklich löschen?`,
    cancel: true, persistent: true
  }).onOk(async () => {
    await store.deleteAudit(audit.id)
    Notify.create({ type: 'info', message: 'Audit gelöscht' })
  })
}

function categoryColor(cat: string): string {
  const map: Record<string, string> = {
    'Patientenorientierung': 'blue', 'Mitarbeiterorientierung': 'purple',
    'Prozessorientierung': 'teal', 'Führung und Verantwortung': 'deep-orange',
    'Fehlerkultur': 'red', 'Kommunikation': 'cyan'
  }
  return map[cat] || 'grey'
}
</script>
