<template>
  <q-page class="q-pa-md">
    <div v-if="loading" class="text-center q-py-xl">
      <q-spinner-hourglass color="primary" size="60px" />
    </div>

    <div v-else-if="document" class="row q-col-gutter-md">
      <!-- PDF Viewer -->
      <div class="col-12 col-md-8">
        <q-card flat bordered>
          <q-card-section class="bg-grey-2" style="min-height: 600px">
            <iframe
              v-if="pdfUrl"
              :src="pdfUrl"
              style="width: 100%; height: 600px; border: none"
            ></iframe>
            <div v-else class="flex flex-center" style="height: 600px">
              <div class="text-center">
                <q-icon name="description" size="120px" color="grey-5" />
                <div class="text-h6 text-grey-7 q-mt-md">Vorschau nicht verfügbar</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Metadata Sidebar -->
      <div class="col-12 col-md-4">
        <q-card flat bordered class="q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-md">{{ document.title || 'Unbenannt' }}</div>
            
            <q-separator class="q-my-md" />

            <div class="metadata-item">
              <div class="text-caption text-grey-7">Dokumenttyp</div>
              <div class="row items-center q-gutter-sm">
                <div class="text-body1 text-weight-medium text-primary">
                  {{ document.category_name || 'Unbekannt' }}
                </div>
                <q-btn
                  flat
                  dense
                  round
                  size="sm"
                  icon="edit"
                  color="primary"
                  @click="showCorrectionDialog = true"
                >
                  <q-tooltip>Kategorie korrigieren</q-tooltip>
                </q-btn>
              </div>
              <div v-if="document.classification_confidence" class="text-caption text-grey-6">
                Konfidenz: {{ (document.classification_confidence * 100).toFixed(0) }}%
              </div>
            </div>

            <div class="metadata-item q-mt-md">
              <div class="text-caption text-grey-7">Hochgeladen am</div>
              <div class="text-body1">{{ formatDate(document.upload_date) }}</div>
            </div>

            <div v-if="document.sender" class="metadata-item q-mt-md">
              <div class="text-caption text-grey-7">Absender</div>
              <div class="text-body1">{{ document.sender }}</div>
            </div>

            <div class="metadata-item q-mt-md">
              <div class="text-caption text-grey-7">Dateigröße</div>
              <div class="text-body1">{{ formatFileSize(document.file_size) }}</div>
            </div>

            <q-separator class="q-my-md" />

            <!-- Actions -->
            <div class="q-gutter-sm">
              <q-btn
                unelevated
                color="primary"
                icon="download"
                label="Herunterladen"
                class="full-width"
                @click="downloadDocument"
              />
              <q-btn
                unelevated
                color="secondary"
                icon="print"
                label="Drucken"
                class="full-width"
                @click="printDocument"
              />
              <q-btn
                unelevated
                color="grey-7"
                icon="email"
                label="Per E-Mail senden"
                class="full-width"
                @click="emailDocument"
              />
              <q-btn
                unelevated
                color="negative"
                icon="delete"
                label="Löschen"
                class="full-width"
                @click="confirmDelete"
              />
            </div>
          </q-card-section>
        </q-card>

        <!-- OCR Text -->
        <q-card v-if="document.ocr_text" flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-sm">OCR-Text</div>
            <q-separator class="q-mb-md" />
            <div class="text-body2" style="max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word;">
              {{ document.ocr_text }}
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div v-else class="text-center q-py-xl">
      <q-icon name="error_outline" size="80px" color="negative" />
      <div class="text-h6 q-mt-md">Dokument nicht gefunden</div>
      <q-btn
        flat
        color="primary"
        label="Zurück zur Übersicht"
        @click="router.push('/documents')"
        class="q-mt-md"
      />
    </div>

    <!-- Correction Dialog -->
    <q-dialog v-model="showCorrectionDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Kategorie korrigieren</div>
          <div class="text-caption text-grey-7">
            Helfen Sie VERA zu lernen - Ihre Korrektur verbessert zukünftige Klassifikationen!
          </div>
        </q-card-section>

        <q-card-section>
          <q-select
            v-model="correctedCategory"
            :options="availableCategories"
            option-label="display_name"
            option-value="name"
            label="Richtige Kategorie"
            outlined
            emit-value
            map-options
          />
          
          <q-input
            v-model="correctionComment"
            type="textarea"
            label="Kommentar (optional)"
            outlined
            class="q-mt-md"
            rows="2"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" color="grey-7" v-close-popup />
          <q-btn
            unelevated
            label="Speichern"
            color="primary"
            @click="submitCorrection"
            :loading="correcting"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'
import { documentsApi } from '@/services/api'
import { Dialog, Notify } from 'quasar'

const router = useRouter()
const route = useRoute()
const documentsStore = useDocumentsStore()

const loading = ref(true)
const pdfUrl = ref<string | null>(null)
const showCorrectionDialog = ref(false)
const correctedCategory = ref<string | null>(null)
const correctionComment = ref('')
const correcting = ref(false)
const availableCategories = ref<Array<{ name: string; display_name: string }>>([])

const document = computed(() => documentsStore.currentDocument)

onMounted(async () => {
  const id = route.params.id as string
  try {
    await documentsStore.fetchDocument(id)
    
    // Load PDF for preview
    if (document.value) {
      const blob = await documentsApi.download(id)
      pdfUrl.value = window.URL.createObjectURL(blob)
    }

    // Load available categories for correction
    await loadCategories()
  } catch (error) {
    console.error('Failed to load document:', error)
  } finally {
    loading.value = false
  }
})

async function loadCategories() {
  try {
    const response = await fetch('/api/folders/categories')
    if (response.ok) {
      availableCategories.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

async function submitCorrection() {
  if (!document.value || !correctedCategory.value) return

  correcting.value = true
  try {
    const response = await fetch('/api/feedback/correct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_id: document.value.id,
        correct_category: correctedCategory.value,
        comment: correctionComment.value || null
      })
    })

    if (response.ok) {
      const result = await response.json()
      
      Notify.create({
        type: 'positive',
        message: `✅ ${result.message}`,
        caption: '🎓 VERA hat gelernt! Zukünftige Dokumente werden besser klassifiziert.'
      })

      // Reload document to show updated category
      await documentsStore.fetchDocument(document.value.id)
      
      showCorrectionDialog.value = false
      correctedCategory.value = null
      correctionComment.value = ''
    } else {
      throw new Error('Correction failed')
    }
  } catch (error) {
    console.error('Correction error:', error)
    Notify.create({
      type: 'negative',
      message: 'Korrektur fehlgeschlagen'
    })
  } finally {
    correcting.value = false
  }
}

async function downloadDocument() {
  if (!document.value) return
  
  try {
    const blob = await documentsApi.download(document.value.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${document.value.title || 'document'}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
    
    Notify.create({
      type: 'positive',
      message: '✅ Download gestartet'
    })
  } catch (error) {
    console.error('Download error:', error)
  }
}

function printDocument() {
  if (pdfUrl.value) {
    const printWindow = window.open(pdfUrl.value)
    printWindow?.print()
  }
}

function emailDocument() {
  Notify.create({
    type: 'info',
    message: 'E-Mail-Funktion in Entwicklung'
  })
}

function confirmDelete() {
  if (!document.value) return

  Dialog.create({
    title: 'Dokument löschen',
    message: 'Möchten Sie dieses Dokument wirklich unwiderruflich löschen?',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await documentsStore.deleteDocument(document.value!.id)
      Notify.create({
        type: 'positive',
        message: '✅ Dokument gelöscht'
      })
      router.push('/documents')
    } catch (error) {
      console.error('Delete error:', error)
    }
  })
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.metadata-item {
  padding: 8px 0;
}
</style>
