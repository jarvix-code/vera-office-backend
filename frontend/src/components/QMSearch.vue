<template>
  <div class="qm-search">
    <!-- Search Input -->
    <q-input
      v-model="query"
      outlined
      placeholder="QM-Dokumente durchsuchen..."
      clearable
      @keyup.enter="search"
      @clear="clearResults"
    >
      <template v-slot:prepend>
        <q-icon name="search" />
      </template>
      <template v-slot:append>
        <q-btn
          round
          dense
          flat
          icon="send"
          @click="search"
          :disable="!query || loading"
        />
      </template>
    </q-input>

    <!-- Loading State -->
    <div v-if="loading" class="q-mt-md text-center">
      <q-spinner-dots color="primary" size="40px" />
      <div class="text-caption text-grey-6 q-mt-sm">Suche läuft...</div>
    </div>

    <!-- Results -->
    <q-list v-else-if="results.length > 0" bordered separator class="q-mt-md rounded-borders">
      <q-item
        v-for="result in results"
        :key="result.doc_id"
        clickable
        v-ripple
        @click="openDocument(result)"
        class="search-result-item"
      >
        <q-item-section>
          <q-item-label class="text-weight-medium">
            {{ result.filename }}
          </q-item-label>
          
          <q-item-label caption class="text-primary q-mt-xs">
            {{ result.category }}
          </q-item-label>
          
          <q-item-label caption class="text-grey-7 q-mt-sm">
            {{ result.preview }}
          </q-item-label>
        </q-item-section>

        <q-item-section side>
          <div class="text-center">
            <q-circular-progress
              :value="result.relevance_score * 100"
              size="50px"
              :thickness="0.15"
              :color="getRelevanceColor(result.relevance_score)"
              track-color="grey-3"
              show-value
              class="q-ma-md"
            >
              <template v-slot:default>
                <div class="text-caption text-weight-bold">
                  {{ Math.round(result.relevance_score * 100) }}%
                </div>
              </template>
            </q-circular-progress>
            <div class="text-caption text-grey-6">Relevanz</div>
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <!-- No Results -->
    <div v-else-if="searched && results.length === 0" class="q-mt-md text-center q-pa-lg">
      <q-icon name="search_off" size="60px" color="grey-5" />
      <div class="text-h6 text-grey-6 q-mt-md">Keine Ergebnisse gefunden</div>
      <div class="text-caption text-grey-5 q-mt-sm">
        Versuchen Sie andere Suchbegriffe
      </div>
    </div>

    <!-- Error State -->
    <q-banner v-if="error" rounded class="bg-negative text-white q-mt-md">
      <template v-slot:avatar>
        <q-icon name="error" />
      </template>
      {{ error }}
    </q-banner>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { qmApi } from '@/services/api'
import { useRouter } from 'vue-router'

const router = useRouter()

// State
const query = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)
const error = ref<string | null>(null)

// Methods
async function search() {
  if (!query.value.trim()) return
  
  loading.value = true
  error.value = null
  searched.value = true
  
  try {
    const response = await qmApi.search(query.value, 5)
    results.value = response.results
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Suche fehlgeschlagen'
    console.error('QM Search Error:', err)
  } finally {
    loading.value = false
  }
}

function clearResults() {
  results.value = []
  searched.value = false
  error.value = null
}

function openDocument(result: any) {
  // TODO: Implementiere Navigation zum Dokument
  // Router-Integration für Dokument-Detail-View
  console.log('Open document:', result)
  // router.push(`/qm/documents/${result.doc_id}`)
}

function getRelevanceColor(score: number): string {
  if (score >= 0.8) return 'positive'
  if (score >= 0.6) return 'warning'
  return 'orange'
}
</script>

<style scoped>
.search-result-item {
  transition: background-color 0.2s;
}

.search-result-item:hover {
  background-color: rgba(124, 58, 237, 0.05);
}
</style>
