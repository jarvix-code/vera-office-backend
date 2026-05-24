<template>
  <q-page class="q-pa-md">
    <!-- Header & Filters -->
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-md-6">
        <q-input
          v-model="searchQuery"
          outlined
          placeholder="Dokumente durchsuchen..."
          clearable
          @update:model-value="handleSearch"
        >
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </div>

      <div class="col-12 col-md-3">
        <q-select
          v-model="filterType"
          outlined
          label="Dokumenttyp"
          :options="documentTypes"
          clearable
          @update:model-value="handleFilter"
        />
      </div>

      <div class="col-12 col-md-3 row q-col-gutter-sm">
        <div class="col-6">
          <q-btn
            unelevated
            color="secondary"
            icon="upload"
            label="Hochladen"
            class="full-width"
            :loading="uploading"
            @click="triggerFileUpload"
            style="height: 56px"
          />
          <!-- Hidden file input for document upload — Bug #668 -->
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
            style="display: none"
            @change="handleFileSelected"
          />
        </div>
        <div class="col-6">
          <q-btn
            unelevated
            color="primary"
            icon="add"
            label="Neu erfassen"
            class="full-width"
            @click="router.push('/capture')"
            style="height: 56px"
          />
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center q-py-xl">
      <q-spinner-hourglass color="primary" size="60px" />
      <div class="text-grey-7 q-mt-md">Dokumente werden geladen...</div>
    </div>

    <!-- Documents Grid -->
    <div v-else-if="documents.length > 0" class="row q-col-gutter-md">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="col-12 col-sm-6 col-md-4 col-lg-3"
      >
        <q-card
          flat
          bordered
          class="document-card cursor-pointer"
          @click="router.push(`/documents/${doc.id}`)"
        >
          <q-card-section class="document-thumbnail bg-grey-3 flex flex-center">
            <q-icon name="description" size="80px" color="primary" />
          </q-card-section>

          <q-card-section>
            <div class="text-subtitle1 text-weight-medium ellipsis-2-lines">
              {{ doc.title || 'Unbenannt' }}
            </div>
            <div class="text-caption text-primary q-mt-xs">
              {{ doc.document_type || 'Unbekannt' }}
            </div>
            <div class="text-caption text-grey-6 q-mt-xs">
              {{ formatDate(doc.upload_date) }}
            </div>
            <div v-if="doc.sender" class="text-caption text-grey-7 q-mt-xs">
              Von: {{ doc.sender }}
            </div>
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat dense icon="more_vert">
              <q-menu>
                <q-list style="min-width: 150px">
                  <q-item clickable v-close-popup @click.stop="downloadDocument(doc.id)">
                    <q-item-section avatar>
                      <q-icon name="download" />
                    </q-item-section>
                    <q-item-section>Download</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click.stop="confirmDelete(doc.id)">
                    <q-item-section avatar>
                      <q-icon name="delete" color="negative" />
                    </q-item-section>
                    <q-item-section class="text-negative">Löschen</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </q-btn>
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center q-py-xl">
      <q-icon name="folder_open" size="120px" color="grey-5" />
      <div class="text-h6 text-grey-7 q-mt-md">Keine Dokumente gefunden</div>
      <q-btn
        unelevated
        color="primary"
        label="Erstes Dokument erfassen"
        icon="camera_alt"
        class="q-mt-md"
        @click="router.push('/capture')"
      />
    </div>

    <!-- Pagination -->
    <div v-if="total > limit" class="flex flex-center q-mt-lg">
      <q-pagination
        v-model="currentPage"
        :max="Math.ceil(total / limit)"
        :max-pages="7"
        direction-links
        boundary-links
        @update:model-value="handlePageChange"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'
import { documentsApi } from '@/services/api'
import { Dialog, Notify } from 'quasar'

const router = useRouter()
const documentsStore = useDocumentsStore()

const searchQuery = ref('')
const filterType = ref<string | null>(null)
const currentPage = ref(1)
const limit = 20
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const documentTypes = [
  'Rechnung',
  'Vertrag',
  'Angebot',
  'Lieferschein',
  'Protokoll',
  'Sonstiges'
]

const documents = computed(() => documentsStore.documents)
const loading = computed(() => documentsStore.loading)
const total = computed(() => documentsStore.total)

onMounted(() => {
  fetchDocuments()
})

async function fetchDocuments() {
  const skip = (currentPage.value - 1) * limit
  await documentsStore.fetchDocuments({
    skip,
    limit,
    search: searchQuery.value || undefined
  })
}

function handleSearch() {
  currentPage.value = 1
  fetchDocuments()
}

function handleFilter() {
  currentPage.value = 1
  fetchDocuments()
}

function handlePageChange() {
  fetchDocuments()
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

async function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    await documentsApi.upload(file)
    Notify.create({
      type: 'positive',
      message: 'Dokument erfolgreich hochgeladen'
    })
    fetchDocuments()
  } catch (error) {
    console.error('Upload error:', error)
    Notify.create({
      type: 'negative',
      message: 'Upload fehlgeschlagen. Bitte erneut versuchen.'
    })
  } finally {
    uploading.value = false
    // Reset so same file can be re-selected
    input.value = ''
  }
}

async function downloadDocument(id: string) {
  try {
    const blob = await documentsApi.download(id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `document-${id}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download error:', error)
  }
}

function confirmDelete(id: string) {
  Dialog.create({
    title: 'Dokument löschen',
    message: 'Möchten Sie dieses Dokument wirklich löschen?',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await documentsStore.deleteDocument(id)
      Notify.create({
        type: 'positive',
        message: 'Dokument gelöscht'
      })
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
    year: 'numeric'
  })
}
</script>

<style scoped>
.document-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.document-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.document-thumbnail {
  height: 180px;
}

.ellipsis-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
