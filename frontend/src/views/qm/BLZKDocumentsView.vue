<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <div class="text-h4">📄 BLZK Dokumente</div>
      <q-space />
      <q-btn
        icon="settings"
        flat
        round
        class="touch-btn"
        to="/qm/blzk/settings"
      />
    </div>

    <!-- Not configured banner -->
    <q-banner v-if="!credStatus.configured" class="bg-warning text-white q-mb-lg" rounded>
      <template v-slot:avatar><q-icon name="warning" /></template>
      BLZK-Zugangsdaten nicht konfiguriert.
      <template v-slot:action>
        <q-btn flat label="Einrichten" to="/qm/blzk/settings" class="touch-btn" />
      </template>
    </q-banner>

    <!-- Filter -->
    <div class="row q-gutter-sm q-mb-md">
      <q-btn-toggle
        v-model="filter"
        no-caps
        rounded
        toggle-color="primary"
        :options="filterOptions"
        class="q-mb-sm"
      />
      <q-space />
      <q-btn
        v-if="credStatus.configured"
        label="Portal-Dokumente laden"
        icon="cloud_download"
        color="primary"
        outline
        :loading="loadingPortal"
        class="touch-btn"
        @click="loadPortalDocuments"
      />
    </div>

    <!-- Katalog Documents (Cards) -->
    <div v-if="loading" class="row q-col-gutter-md">
      <div v-for="i in 6" :key="i" class="col-12 col-sm-6 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <q-skeleton type="text" width="60%" />
            <q-skeleton type="text" class="q-mt-sm" />
            <q-skeleton type="rect" height="32px" class="q-mt-md" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div v-else class="row q-col-gutter-md">
      <div
        v-for="doc in filteredDocs"
        :key="doc.code"
        class="col-12 col-sm-6 col-md-4"
      >
        <q-card flat bordered class="doc-card">
          <q-card-section>
            <div class="row items-center q-mb-sm">
              <q-badge :color="typColor(doc.typ)" class="q-mr-sm">
                Typ {{ doc.typ }}
              </q-badge>
              <span class="text-caption text-grey-7">{{ doc.code }}</span>
            </div>
            <div class="text-subtitle1 text-weight-medium">{{ doc.name }}</div>
            <div class="text-caption text-grey-7 q-mt-xs">
              {{ doc.kapitel_name }} · {{ doc.turnus }}
            </div>
            <div v-if="doc.beschreibung" class="text-caption q-mt-xs">
              {{ doc.beschreibung }}
            </div>
          </q-card-section>

          <q-separator />

          <q-card-actions>
            <q-chip
              v-for="sd in doc.stammdaten"
              :key="sd"
              size="sm"
              :icon="stammdatenIcon(sd)"
              :label="sd"
            />
            <q-space />
            <q-btn
              v-if="portalDocIds.length"
              flat
              icon="download"
              color="primary"
              class="touch-btn"
              @click="downloadDoc(doc)"
            />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <!-- Bulk Download (Portal) -->
    <q-dialog v-model="showBulkDownload">
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Bulk-Download</div>
          <div class="text-caption q-mt-sm">
            {{ portalDocIds.length }} Dokumente vom BLZK-Portal
          </div>
        </q-card-section>

        <q-card-section v-if="downloading">
          <q-linear-progress
            :value="downloadProgress"
            color="primary"
            class="q-mb-sm"
          />
          <div class="text-caption text-center">
            {{ Math.round(downloadProgress * 100) }}%
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup class="touch-btn" />
          <q-btn
            label="Alle herunterladen"
            color="primary"
            :loading="downloading"
            class="touch-btn"
            @click="bulkDownload"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Empty state -->
    <div v-if="!loading && filteredDocs.length === 0" class="text-center q-pa-xl text-grey-5">
      <q-icon name="folder_open" size="64px" />
      <div class="text-h6 q-mt-md">Keine Dokumente in diesem Bereich</div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { qmApi } from '@/services/qm-api'
import { Notify } from 'quasar'

interface KatalogDoc {
  code: string
  kapitel: string
  kapitel_name: string
  name: string
  typ: string
  turnus: string
  stammdaten: string[]
  beschreibung: string
}

const loading = ref(true)
const loadingPortal = ref(false)
const downloading = ref(false)
const downloadProgress = ref(0)
const showBulkDownload = ref(false)

const docs = ref<KatalogDoc[]>([])
const portalDocIds = ref<string[]>([])
const credStatus = ref<{ configured: boolean; username: string | null }>({ configured: false, username: null })
const filter = ref('alle')

const filterOptions = [
  { label: 'Alle', value: 'alle' },
  { label: 'Arbeitssicherheit', value: 'B' },
  { label: 'Praxisorganisation', value: 'C01' },
  { label: 'Hygiene', value: 'C02' },
  { label: 'Patienten', value: 'C03' },
  { label: 'Mitarbeiter', value: 'C04' },
  { label: 'Fehler', value: 'C05' },
  { label: 'Röntgen', value: 'C06' },
]

const filteredDocs = computed(() => {
  if (filter.value === 'alle') return docs.value
  return docs.value.filter(d => d.kapitel.startsWith(filter.value))
})

function typColor(typ: string): string {
  return typ === 'A' ? 'blue' : typ === 'B' ? 'orange' : 'green'
}

function stammdatenIcon(sd: string): string {
  const map: Record<string, string> = {
    praxis: 'business',
    personal: 'people',
    geraete: 'precision_manufacturing',
  }
  return map[sd] || 'description'
}

async function loadKatalog() {
  try {
    const data = await qmApi.getBLZKKatalog()
    docs.value = data.dokumente || []
  } catch {
    Notify.create({ type: 'negative', message: 'Fehler beim Laden des Katalogs' })
  } finally {
    loading.value = false
  }
}

async function loadCredStatus() {
  try {
    credStatus.value = await qmApi.getBLZKCredentials()
  } catch {
    // ignore
  }
}

async function loadPortalDocuments() {
  loadingPortal.value = true
  try {
    const data = await qmApi.getBLZKPortalDocuments()
    const allIds: string[] = []
    for (const area of Object.values(data.areas || {}) as any[]) {
      allIds.push(...(area.doc_ids || []))
    }
    portalDocIds.value = allIds
    Notify.create({
      type: 'positive',
      message: `${data.total_documents || 0} Dokumente vom Portal geladen`,
    })
    if (allIds.length > 0) {
      showBulkDownload.value = true
    }
  } catch (e: any) {
    Notify.create({
      type: 'negative',
      message: e.response?.data?.detail || 'Portal nicht erreichbar',
    })
  } finally {
    loadingPortal.value = false
  }
}

async function bulkDownload() {
  downloading.value = true
  downloadProgress.value = 0
  try {
    // Simulate progress (actual download is server-side)
    const interval = setInterval(() => {
      if (downloadProgress.value < 0.9) downloadProgress.value += 0.1
    }, 500)

    const result = await qmApi.downloadBLZKDocuments({
      doc_ids: portalDocIds.value,
      filename: 'blzk_komplett',
    })

    clearInterval(interval)
    downloadProgress.value = 1

    if (result.success) {
      Notify.create({ type: 'positive', message: 'Download abgeschlossen!' })
    } else {
      Notify.create({ type: 'warning', message: 'Teilweise heruntergeladen' })
    }
  } catch (e: any) {
    Notify.create({ type: 'negative', message: e.response?.data?.detail || 'Download-Fehler' })
  } finally {
    downloading.value = false
    showBulkDownload.value = false
  }
}

async function downloadDoc(_doc: KatalogDoc) {
  // Single doc download - could map code → portal doc_id
  Notify.create({ type: 'info', message: 'Einzeldownload wird implementiert...' })
}

onMounted(() => {
  loadKatalog()
  loadCredStatus()
})
</script>

<style scoped>
.touch-btn {
  min-height: 44px;
  min-width: 44px;
}

.doc-card {
  transition: box-shadow 0.2s;
}

.doc-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
</style>
