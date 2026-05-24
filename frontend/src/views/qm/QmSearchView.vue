<template>
  <q-page class="q-pa-md">
    <!-- Page Header -->
    <div class="page-header q-mb-lg">
      <div class="row items-center">
        <div class="col">
          <h1 class="text-h4 text-weight-bold q-ma-none">
            <q-icon name="search" size="32px" class="q-mr-sm" color="primary" />
            QM-Wissensdatenbank
          </h1>
          <p class="text-body1 text-grey-7 q-mt-sm q-mb-none">
            Durchsuchen Sie alle QM-Dokumente semantisch und finden Sie relevante Informationen in Sekunden
          </p>
        </div>
        
        <!-- Stats Badge -->
        <div class="col-auto">
          <q-btn
            flat
            round
            icon="info"
            @click="showStats = true"
          >
            <q-tooltip>Statistiken anzeigen</q-tooltip>
          </q-btn>
        </div>
      </div>
    </div>

    <!-- Search Component -->
    <q-card flat bordered class="q-mb-lg">
      <q-card-section>
        <QMSearch />
      </q-card-section>
    </q-card>

    <!-- Example Queries -->
    <q-card flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">
          <q-icon name="lightbulb" class="q-mr-sm" />
          Beispiel-Suchanfragen
        </div>
        
        <div class="row q-col-gutter-sm">
          <div
            v-for="example in examples"
            :key="example.query"
            class="col-12 col-sm-6 col-md-4"
          >
            <q-chip
              clickable
              color="accent"
              text-color="primary"
              icon="search"
              class="full-width"
              @click="searchExample(example.query)"
            >
              {{ example.label }}
            </q-chip>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Stats Dialog -->
    <q-dialog v-model="showStats">
      <q-card style="min-width: 400px">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6">RAG Engine Statistiken</div>
        </q-card-section>

        <q-card-section v-if="stats">
          <q-list>
            <q-item>
              <q-item-section>
                <q-item-label overline>Modell</q-item-label>
                <q-item-label>{{ stats.model }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label overline>Indexierte Dokumente</q-item-label>
                <q-item-label>{{ stats.indexed_documents }} / {{ stats.available_documents }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label overline>Index-Abdeckung</q-item-label>
                <q-item-label>{{ stats.index_coverage }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label overline>Embedding-Dimension</q-item-label>
                <q-item-label>{{ stats.embedding_dimension }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-section v-else>
          <div class="text-center q-py-md">
            <q-spinner-hourglass color="primary" size="40px" />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Schließen" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import QMSearch from '@/components/QMSearch.vue'
import { qmApi } from '@/services/api'

// State
const showStats = ref(false)
const stats = ref<any>(null)

// Example queries
const examples = [
  { label: 'Hygieneplan Desinfektion', query: 'Hygieneplan Desinfektion' },
  { label: 'Notfall Reanimation', query: 'Notfall Reanimation' },
  { label: 'Datenschutz Patientenakte', query: 'Datenschutz Patientenakte' },
  { label: 'Sterilisation Prüfprotokoll', query: 'Sterilisation Prüfprotokoll' },
  { label: 'Arbeitsanweisung Behandlung', query: 'Arbeitsanweisung Behandlung' },
  { label: 'Geräteeinweisung Röntgen', query: 'Geräteeinweisung Röntgen' }
]

// Methods
function searchExample(query: string) {
  // Trigger search in QMSearch component
  // This will be handled via event emitter or ref
  console.log('Search example:', query)
  // TODO: Implement via ref to QMSearch component
}

async function loadStats() {
  try {
    stats.value = await qmApi.getStats()
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

// Watch stats dialog
function watchStatsDialog() {
  if (showStats.value && !stats.value) {
    loadStats()
  }
}

onMounted(() => {
  // Pre-load stats in background (optional)
  // loadStats()
})
</script>

<style scoped>
.page-header h1 {
  display: flex;
  align-items: center;
}
</style>
