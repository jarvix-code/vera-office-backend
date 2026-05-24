<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <!-- Stats Cards -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 text-grey-7">Dokumente gesamt</div>
            <div class="text-h3 text-primary q-mt-sm">{{ stats.total_documents || 0 }}</div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 text-grey-7">Heute erfasst</div>
            <div class="text-h3 text-positive q-mt-sm">{{ stats.today_count || 0 }}</div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 text-grey-7">Offene Aufgaben</div>
            <div class="text-h3 text-warning q-mt-sm">{{ stats.pending_tasks || 0 }}</div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Quick Actions -->
      <div class="col-12">
        <div class="row q-col-gutter-md q-mt-md">
          <div class="col-12 col-md-6">
            <q-btn
              unelevated
              color="primary"
              size="xl"
              class="full-width"
              style="min-height: 80px"
              icon="camera_alt"
              label="Dokument erfassen"
              @click="router.push('/capture')"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-btn
              unelevated
              color="secondary"
              size="xl"
              class="full-width"
              style="min-height: 80px"
              icon="search"
              label="Suchen"
              @click="router.push('/search')"
            />
          </div>
        </div>

        <!-- USB Import Button -->
        <div class="row q-col-gutter-md q-mt-sm">
          <div class="col-12">
            <q-btn
              unelevated
              :color="usbImport.detected ? 'positive' : 'grey-6'"
              size="lg"
              class="full-width"
              style="min-height: 64px"
              :icon="usbImport.importing ? 'hourglass_top' : 'usb'"
              :label="usbButtonLabel"
              :loading="usbImport.scanning"
              :disable="usbImport.importing"
              @click="handleUsbImport"
            />
            <!-- Progress Bar -->
            <q-linear-progress
              v-if="usbImport.importing"
              :value="usbImportProgress"
              color="positive"
              class="q-mt-xs"
              size="12px"
              rounded
            >
              <div class="absolute-full flex flex-center">
                <q-badge color="white" text-color="positive" :label="`${usbImport.done}/${usbImport.total}`" />
              </div>
            </q-linear-progress>
          </div>
        </div>
      </div>


      <!-- VERA Chat Widget -->
      <div class="col-12 q-mt-md">
        <q-card flat bordered class="vera-chat-widget">
          <q-card-section class="bg-primary text-white">
            <div class="row items-center">
              <q-avatar size="40px" class="q-mr-sm">
                <q-icon name="support_agent" size="28px" />
              </q-avatar>
              <div class="col">
                <div class="text-subtitle1 text-weight-bold">Fragen Sie VERA</div>
                <div class="text-caption">Ihre Dokumenten-Assistentin</div>
              </div>
              <q-btn
                flat
                dense
                round
                icon="open_in_new"
                @click="router.push('/chat')"
              />
            </div>
          </q-card-section>
          <q-card-section>
            <q-input
              v-model="veraQuery"
              outlined
              dense
              placeholder="Fragen Sie VERA etwas..."
              @keyup.enter="openChatWithQuery"
              @click="router.push('/chat')"
            >
              <template v-slot:prepend>
                <q-icon name="chat" color="primary" />
              </template>
            </q-input>
            
            <!-- Suggestions -->
            <div v-if="suggestions.length > 0" class="q-mt-sm">
              <div class="text-caption text-grey-7 q-mb-xs">VorschlÃ¤ge:</div>
              <q-chip
                v-for="(suggestion, index) in suggestions.slice(0, 3)"
                :key="index"
                size="sm"
                clickable
                color="primary"
                text-color="white"
                @click="handleSuggestion(suggestion)"
              >
                {{ suggestion.title }}
              </q-chip>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Quick Search -->
      <div class="col-12 q-mt-md">
        <q-input
          v-model="searchQuery"
          outlined
          placeholder="Schnellsuche..."
          clearable
          @keyup.enter="handleQuickSearch"
        >
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
          <template v-slot:append>
            <q-btn flat dense label="Suchen" @click="handleQuickSearch" />
          </template>
        </q-input>
      </div>

      <!-- Recent Documents -->
      <div class="col-12 q-mt-md">
        <div class="text-h5 q-mb-md">Letzte Dokumente</div>
        <q-card v-if="loading" flat bordered>
          <q-card-section>
            <q-skeleton type="text" />
            <q-skeleton type="text" />
          </q-card-section>
        </q-card>
        <div v-else class="row q-col-gutter-md">
          <div
            v-for="doc in recentDocuments"
            :key="doc.id"
            class="col-12 col-sm-6 col-md-4"
          >
            <q-card
              flat
              bordered
              class="cursor-pointer hover-shadow"
              @click="router.push(`/documents/${doc.id}`)"
            >
              <q-card-section>
                <div class="row items-center">
                  <q-icon name="description" size="md" color="primary" class="q-mr-md" />
                  <div class="col">
                    <div class="text-subtitle1 text-weight-medium">{{ doc.title || 'Unbenannt' }}</div>
                    <div class="text-caption text-grey-7">{{ doc.document_type }}</div>
                    <div class="text-caption text-grey-6">{{ formatDate(doc.upload_date) }}</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'
import { useChatStore } from '@/stores/chat'
import { systemApi } from '@/services/api'
import axios from 'axios'
import { Notify } from 'quasar'

const router = useRouter()
const documentsStore = useDocumentsStore()
const chatStore = useChatStore()

const searchQuery = ref('')
const veraQuery = ref('')
const suggestions = ref([])
const stats = ref({
  total_documents: 0,
  today_count: 0,
  pending_tasks: 0
})
const recentDocuments = ref([])
const loading = ref(true)

// USB Import State
const usbImport = ref({
  detected: false,
  scanning: false,
  importing: false,
  total: 0,
  done: 0,
  fileCount: 0,
  jobId: '',
})
let usbPollTimer: ReturnType<typeof setInterval> | null = null

const usbButtonLabel = computed(() => {
  if (usbImport.value.importing) return `Importiere... ${usbImport.value.done}/${usbImport.value.total}`
  if (usbImport.value.detected) return `USB-Stick einlesen (${usbImport.value.fileCount} Dateien)`
  return 'USB-Stick einlesen'
})

const usbImportProgress = computed(() => {
  if (usbImport.value.total === 0) return 0
  return usbImport.value.done / usbImport.value.total
})

async function checkUsbDetection() {
  try {
    const res = await axios.get('/api/documents/import-usb/detect')
    usbImport.value.detected = res.data.detected
    usbImport.value.fileCount = res.data.file_count || 0
  } catch { /* USB detection is optional */ }
}

async function handleUsbImport() {
  if (usbImport.value.importing) return

  usbImport.value.scanning = true
  try {
    // First scan
    const scan = await axios.get('/api/documents/import-usb/scan')
    if (!scan.data.mounted || scan.data.file_count === 0) {
      Notify.create({ type: 'warning', message: 'Kein USB-Stick gefunden oder keine Dateien vorhanden.', icon: 'usb_off' })
      usbImport.value.scanning = false
      return
    }

    // Start import
    const res = await axios.post('/api/documents/import-usb')
    usbImport.value.jobId = res.data.job_id
    usbImport.value.total = res.data.total_files
    usbImport.value.done = 0
    usbImport.value.importing = true
    usbImport.value.scanning = false

    // Poll progress
    usbPollTimer = setInterval(async () => {
      try {
        const prog = await axios.get(`/api/documents/import-usb/progress/${usbImport.value.jobId}`)
        usbImport.value.done = prog.data.done
        if (prog.data.status === 'done') {
          clearInterval(usbPollTimer!)
          usbPollTimer = null
          usbImport.value.importing = false
          const errors = prog.data.errors
          Notify.create({
            type: errors > 0 ? 'warning' : 'positive',
            message: `${prog.data.done - errors} Dokumente importiert${errors > 0 ? ` (${errors} Fehler)` : ''}`,
            icon: 'check_circle',
            timeout: 5000,
          })
          // Refresh dashboard
          await documentsStore.fetchDocuments({ limit: 6 })
          recentDocuments.value = documentsStore.documents
          checkUsbDetection()
        }
      } catch { /* ignore poll errors */ }
    }, 1000)
  } catch (err: any) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'USB-Import fehlgeschlagen', icon: 'error' })
    usbImport.value.scanning = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    // Fetch stats
    const statsData = await systemApi.getStats()
    stats.value = statsData

    // Fetch recent documents
    await documentsStore.fetchDocuments({ limit: 6 })
    recentDocuments.value = documentsStore.documents

    // Load VERA suggestions
    const suggestionsData = await chatStore.loadSuggestions()
    suggestions.value = suggestionsData.suggestions || []
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
    // Check USB detection
    checkUsbDetection()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (usbPollTimer) clearInterval(usbPollTimer)
})

function handleQuickSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
  }
}

function openChatWithQuery() {
  if (veraQuery.value.trim()) {
    router.push({ path: '/chat', query: { q: veraQuery.value } })
  } else {
    router.push('/chat')
  }
}

function handleSuggestion(suggestion: any) {
  router.push('/chat')
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}
</script>

<style scoped>
.hover-shadow {
  transition: box-shadow 0.3s;
}
.hover-shadow:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.vera-chat-widget {
  border: 2px solid #1976d2;
  border-radius: 12px;
  overflow: hidden;
}
</style>

