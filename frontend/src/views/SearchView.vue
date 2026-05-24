<template>
  <q-page class="q-pa-md">
    <div class="search-container">
      <!-- Search Header -->
      <div class="text-h4 text-center q-mb-md">Dokumentensuche</div>
      <div class="text-subtitle1 text-grey-7 text-center q-mb-xl">
        Natürliche Sprachsuche - einfach eingeben, was Sie suchen
      </div>

      <!-- Search Input -->
      <q-input
        v-model="searchQuery"
        outlined
        placeholder='z.B. "Dienstvertrag Bianca Müller" oder "Rechnungen Januar 2026"'
        class="search-input"
        autofocus
        @keyup.enter="handleSearch"
      >
        <template v-slot:prepend>
          <q-icon name="search" size="md" />
        </template>
        <template v-slot:append>
          <q-btn
            unelevated
            color="primary"
            label="Suchen"
            @click="handleSearch"
            :disable="!searchQuery.trim()"
          />
        </template>
      </q-input>

      <!-- Quick Suggestions -->
      <div v-if="!searchPerformed && !loading" class="q-mt-lg">
        <div class="text-subtitle2 text-grey-7 q-mb-md">Beliebte Suchen:</div>
        <div class="q-gutter-sm">
          <q-chip
            v-for="suggestion in suggestions"
            :key="suggestion"
            clickable
            color="grey-3"
            text-color="grey-8"
            @click="searchQuery = suggestion; handleSearch()"
          >
            {{ suggestion }}
          </q-chip>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center q-py-xl">
        <q-spinner-hourglass color="primary" size="60px" />
        <div class="text-grey-7 q-mt-md">Suche läuft...</div>
      </div>

      <!-- Results -->
      <div v-else-if="searchPerformed" class="q-mt-xl">
        <div class="text-h6 q-mb-md">
          Ergebnisse für "{{ lastSearchQuery }}"
          <span class="text-grey-7">({{ results.length }})</span>
        </div>

        <div v-if="results.length > 0" class="row q-col-gutter-md">
          <div
            v-for="doc in results"
            :key="doc.id"
            class="col-12 col-sm-6 col-md-4"
          >
            <q-card
              flat
              bordered
              class="result-card cursor-pointer"
              @click="router.push(`/documents/${doc.id}`)"
            >
              <q-card-section class="result-thumbnail bg-grey-3 flex flex-center">
                <q-icon name="description" size="60px" color="primary" />
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
                <div v-if="doc.ocr_text" class="text-caption text-grey-6 q-mt-sm ellipsis-3-lines">
                  {{ doc.ocr_text.substring(0, 150) }}...
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <div v-else class="text-center q-py-xl">
          <q-icon name="search_off" size="100px" color="grey-5" />
          <div class="text-h6 text-grey-7 q-mt-md">Keine Ergebnisse gefunden</div>
          <div class="text-body2 text-grey-6 q-mt-sm">
            Versuchen Sie es mit anderen Suchbegriffen
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'

const router = useRouter()
const route = useRoute()
const documentsStore = useDocumentsStore()

const searchQuery = ref('')
const lastSearchQuery = ref('')
const searchPerformed = ref(false)
const loading = ref(false)
const results = ref([])

const suggestions = [
  'Rechnungen 2026',
  'Verträge',
  'Lieferscheine Januar',
  'Alle PDFs',
  'Dokumente von heute'
]

onMounted(() => {
  // Check if query parameter exists
  const queryParam = route.query.q as string
  if (queryParam) {
    searchQuery.value = queryParam
    handleSearch()
  }
})

async function handleSearch() {
  if (!searchQuery.value.trim()) return

  loading.value = true
  searchPerformed.value = true
  lastSearchQuery.value = searchQuery.value

  try {
    await documentsStore.searchDocuments(searchQuery.value)
    results.value = documentsStore.documents || []
  } catch (error) {
    console.error('Search error:', error)
    results.value = []
  } finally {
    loading.value = false
  }
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
.search-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-top: 40px;
}

.search-input {
  font-size: 18px;
}

.result-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.result-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.result-thumbnail {
  height: 120px;
}

.ellipsis-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ellipsis-3-lines {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
