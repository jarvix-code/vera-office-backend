<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">📖 QM Handbuch</div>
    <div class="text-subtitle1 text-grey-7 q-mb-lg">BLZK-konformes Qualitätshandbuch — 13 Kapitel</div>

    <div v-if="store.loading && !store.handbook">
      <q-skeleton type="rect" height="200px" />
    </div>

    <template v-else-if="store.handbook">
      <!-- Kapitel nach Bereichen -->
      <div v-for="(chapters, area) in store.handbook" :key="area" class="q-mb-lg">
        <div class="text-h6 q-mb-sm">
          <q-icon :name="areaIcon(area)" class="q-mr-sm" />
          {{ area }}
        </div>
        <div class="row q-col-gutter-md">
          <div v-for="chapter in chapters" :key="chapter.id" class="col-12 col-md-4">
            <q-card flat bordered class="cursor-pointer hover-card" @click="selectChapter(chapter)">
              <q-card-section>
                <div class="text-subtitle1 text-weight-medium">
                  {{ chapter.order }}. {{ chapter.title }}
                </div>
                <div class="text-caption text-grey-6">{{ chapter.id }}</div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </template>

    <!-- Kapitel-Detail Dialog -->
    <q-dialog v-model="showChapterDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-bar class="bg-primary text-white">
          <div class="text-weight-bold">{{ selectedChapter?.title }}</div>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>
        <q-card-section v-if="chapterLoading" class="q-pa-lg">
          <q-skeleton type="text" v-for="i in 5" :key="i" class="q-mb-sm" />
        </q-card-section>
        <q-card-section v-else-if="chapterDetail" class="q-pa-lg">
          <div class="text-h5 q-mb-md">{{ chapterDetail.chapter.title }}</div>
          <div class="text-caption text-grey-7 q-mb-lg">
            Bereich: {{ chapterDetail.chapter.area }} | ID: {{ chapterDetail.chapter.id }}
          </div>

          <div class="text-h6 q-mb-sm">Verknüpfte Dokumente ({{ chapterDetail.documents.length }})</div>
          <q-list v-if="chapterDetail.documents.length > 0" bordered separator>
            <q-item v-for="doc in chapterDetail.documents" :key="doc.id" clickable @click="goToDocument(doc.id)">
              <q-item-section avatar>
                <q-icon name="description" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ doc.title }}</q-item-label>
                <q-item-label caption>v{{ doc.current_version }} — {{ doc.status }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="statusColor(doc.status)">{{ doc.status }}</q-badge>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-else class="text-grey-6 text-center q-pa-lg">
            Keine Dokumente verknüpft. Erstellen Sie ein QM-Dokument mit Tag "{{ selectedChapter?.id }}".
          </div>

          <q-btn color="primary" icon="add" label="Dokument erstellen" class="q-mt-lg" @click="createDocForChapter" />
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Dokument erstellen Dialog -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Neues QM-Dokument</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="newDoc.title" label="Titel" outlined class="q-mb-md" />
          <q-select v-model="newDoc.main_area" label="Bereich" outlined
            :options="['Arbeitssicherheit', 'Qualitätsmanagement', 'Handbuch']" class="q-mb-md" />
          <q-input v-model="newDoc.content" label="Inhalt (Markdown)" outlined type="textarea" rows="6" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup />
          <q-btn unelevated color="primary" label="Erstellen" @click="submitCreate" :loading="creating" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQmStore } from '@/stores/qm'
import { qmApi } from '@/services/qm-api'
import { Notify } from 'quasar'

const store = useQmStore()
const router = useRouter()

const showChapterDialog = ref(false)
const selectedChapter = ref<any>(null)
const chapterDetail = ref<any>(null)
const chapterLoading = ref(false)

const showCreateDialog = ref(false)
const creating = ref(false)
const newDoc = ref({ title: '', main_area: '', content: '' })

onMounted(() => {
  store.fetchHandbook()
})

function areaIcon(area: string): string {
  const map: Record<string, string> = {
    'Arbeitssicherheit': 'health_and_safety',
    'Qualitätsmanagement': 'verified',
    'Handbuch': 'menu_book'
  }
  return map[area] || 'folder'
}

function statusColor(status: string): string {
  const map: Record<string, string> = {
    'Entwurf': 'grey', 'In Prüfung': 'orange', 'Freigegeben': 'green',
    'Veraltet': 'amber', 'Archiviert': 'blue-grey'
  }
  return map[status] || 'grey'
}

async function selectChapter(chapter: any) {
  selectedChapter.value = chapter
  showChapterDialog.value = true
  chapterLoading.value = true
  try {
    chapterDetail.value = await qmApi.getHandbookChapter(chapter.id)
  } finally {
    chapterLoading.value = false
  }
}

function goToDocument(id: number) {
  showChapterDialog.value = false
  router.push(`/qm/documents/${id}`)
}

function createDocForChapter() {
  showChapterDialog.value = false
  newDoc.value = {
    title: '',
    main_area: selectedChapter.value?.area || '',
    content: ''
  }
  showCreateDialog.value = true
}

async function submitCreate() {
  if (!newDoc.value.title || !newDoc.value.main_area) return
  creating.value = true
  try {
    await store.createDocument({
      ...newDoc.value,
      tags: selectedChapter.value ? [selectedChapter.value.id] : []
    })
    showCreateDialog.value = false
    Notify.create({ type: 'positive', message: 'Dokument erstellt' })
    if (selectedChapter.value) {
      await selectChapter(selectedChapter.value)
      showChapterDialog.value = true
    }
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.hover-card { transition: box-shadow 0.2s; }
.hover-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
</style>
