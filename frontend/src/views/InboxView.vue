<template>
  <q-page padding>
    <div class="q-mb-md row items-center">
      <q-btn flat round icon="arrow_back" color="primary" class="q-mr-sm" @click="$router.back()" />
      <div>
        <h4 class="q-my-none">Inbox / Hotfolder</h4>
        <p class="text-grey-7 q-mb-none">Dateien aus dem Hotfolder-Verzeichnis verarbeiten</p>
      </div>
    </div>

    <!-- Status Card -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row items-center justify-between">
          <div>
            <div class="text-subtitle1 text-weight-medium">Inbox-Verzeichnis</div>
            <div class="text-caption text-grey-7">Neue Dokumente (PDF, JPG, PNG, TIFF) werden automatisch verarbeitet</div>
          </div>
          <q-btn
            color="primary"
            icon="play_arrow"
            label="Alle verarbeiten"
            :loading="isProcessing"
            :disable="isProcessing"
            @click="startProcessing"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Progress Card -->
    <q-card v-if="currentJob" class="q-mb-md">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">
          <q-icon name="sync" class="q-mr-xs" :class="{ rotate: isProcessing }" />
          Verarbeitung...
        </div>
        <q-linear-progress
          :value="progressValue"
          color="primary"
          class="q-mb-sm"
          rounded
          size="12px"
        />
        <div class="row justify-between text-caption text-grey-7">
          <span>{{ currentJob.done }} / {{ currentJob.total }} Dateien</span>
          <span v-if="currentJob.errors > 0" class="text-negative">{{ currentJob.errors }} Fehler</span>
          <span v-if="currentJob.current_file">{{ currentJob.current_file }}</span>
        </div>
        <q-banner v-if="currentJob.status === &apos;done&apos;" class="bg-positive text-white q-mt-md" rounded>
          <template #avatar><q-icon name="check_circle" /></template>
          Fertig: {{ currentJob.done }} Dateien ({{ currentJob.errors }} Fehler)
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Empty state -->
    <q-card v-if="!currentJob && !isProcessing" flat bordered>
      <q-card-section class="text-center q-pa-xl">
        <q-icon name="inbox" size="64px" color="grey-4" />
        <div class="text-h6 text-grey-6 q-mt-md">Inbox bereit</div>
        <div class="text-body2 text-grey-5 q-mt-sm">
          Legen Sie Dateien in das Hotfolder-Verzeichnis und klicken Sie auf Alle verarbeiten.
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'

const q = useQuasar()

interface JobProgress {
  job_id: string
  status: string
  total: number
  done: number
  errors: number
  current_file: string | null
}

const isProcessing = ref(false)
const currentJob = ref<JobProgress | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

const progressValue = computed(() => {
  if (!currentJob.value || currentJob.value.total === 0) return 0
  return currentJob.value.done / currentJob.value.total
})

async function startProcessing() {
  isProcessing.value = true
  currentJob.value = null
  try {
    const response = await fetch('/api/inbox/process-all', { method: 'POST' })
    if (!response.ok) throw new Error('HTTP ' + response.status)
    const data = await response.json()
    if (data.job_id === 'none') {
      q.notify({ type: 'info', message: 'Keine Dateien in Inbox gefunden.' })
      isProcessing.value = false
      return
    }
    q.notify({ type: 'positive', message: data.total_files + ' Dateien werden verarbeitet...' })
    pollProgress(data.job_id)
  } catch (e: any) {
    q.notify({ type: 'negative', message: 'Fehler: ' + e.message })
    isProcessing.value = false
  }
}

function pollProgress(jobId: string) {
  pollInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/inbox/process-progress/' + jobId)
      if (!resp.ok) return
      const progress: JobProgress = await resp.json()
      currentJob.value = progress
      if (progress.status === 'done' || progress.status === 'error') {
        clearInterval(pollInterval!)
        pollInterval = null
        isProcessing.value = false
      }
    } catch { /* ignore poll errors */ }
  }, 1500)
}
</script>

<style scoped>
.rotate {
  animation: spin 1.5s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
