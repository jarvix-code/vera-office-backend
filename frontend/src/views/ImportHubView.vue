<template>
  <q-page padding>
    <div class="q-mb-md">
      <h4 class="q-my-md">📥 Dokumente einpflegen</h4>
      <p class="text-grey-7">
        Wählen Sie eine Methode zum Importieren von Dokumenten.
      </p>
    </div>

    <!-- Kacheln Grid -->
    <div class="row q-col-gutter-md">
      
      <!-- Kachel: Capture (Kamera) -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="import-tile cursor-pointer" @click="goToCapture">
          <q-card-section class="text-center">
            <q-icon name="photo_camera" size="64px" color="primary" />
            <div class="text-h6 q-mt-md">📸 Capture</div>
            <div class="text-caption text-grey-7">
              Dokument mit Kamera scannen
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Kachel: Unklare Dokumente -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card 
          class="import-tile cursor-pointer" 
          :class="{ 'tile-attention': unclearCount > 0 }"
          @click="goToUnclear"
        >
          <q-card-section class="text-center">
            <q-icon name="help_outline" size="64px" color="orange" />
            
            <!-- Badge -->
            <q-badge 
              v-if="unclearCount > 0"
              color="red" 
              :label="unclearCount"
              floating
              rounded
            />
            
            <div class="text-h6 q-mt-md">📋 Unklare Dokumente</div>
            <div class="text-caption text-grey-7">
              {{ unclearCount }} Dokumente brauchen Hilfe
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Kachel: USB Import -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="import-tile cursor-pointer" @click="goToUSB">
          <q-card-section class="text-center">
            <q-icon name="usb" size="64px" color="primary" />
            <div class="text-h6 q-mt-md">💾 USB Import</div>
            <div class="text-caption text-grey-7">
              Dokumente von USB-Stick
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Kachel: Inbox (Hotfolder) -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="import-tile cursor-pointer" @click="goToInbox">
          <q-card-section class="text-center">
            <q-icon name="inbox" size="64px" color="primary" />
            <div class="text-h6 q-mt-md">📤 Inbox</div>
            <div class="text-caption text-grey-7">
              Hotfolder-Überwachung
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Kachel: Upload (optional) -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="import-tile cursor-pointer" @click="goToUpload">
          <q-card-section class="text-center">
            <q-icon name="cloud_upload" size="64px" color="primary" />
            <div class="text-h6 q-mt-md">☁️ Upload</div>
            <div class="text-caption text-grey-7">
              Dateien hochladen
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Kachel: Scanner (optional) -->
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="import-tile cursor-pointer" @click="goToScanner">
          <q-card-section class="text-center">
            <q-icon name="scanner" size="64px" color="primary" />
            <div class="text-h6 q-mt-md">🖨️ Scanner</div>
            <div class="text-caption text-grey-7">
              Netzwerk-Scanner verwenden
            </div>
          </q-card-section>
        </q-card>
      </div>

    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const unclearCount = ref(0)

async function loadUnclearCount() {
  try {
    const response = await fetch('/api/active-learning/unclear-documents/count')
    if (response.ok) {
      const data = await response.json()
      unclearCount.value = data.count
    } else {
      // Fallback: Badge anzeigen (ohne Count) wenn API nicht verfügbar
      unclearCount.value = 0
    }
  } catch (e) {
    console.error('Failed to load unclear count:', e)
    // Graceful degradation: 0 anzeigen statt Fehler
    unclearCount.value = 0
  }
}

// Navigation Functions
const goToCapture = () => router.push('/capture')
const goToUnclear = () => router.push('/unclear')
const goToUSB = () => router.push('/usb-import')
const goToInbox = () => router.push('/inbox')
const goToUpload = () => router.push('/upload')
const goToScanner = () => router.push('/scanner')

onMounted(() => {
  loadUnclearCount()
  // Refresh count every 30s
  setInterval(loadUnclearCount, 30000)
})
</script>

<style scoped>
.import-tile {
  transition: all 0.3s;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.import-tile:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.tile-attention {
  background: linear-gradient(135deg, #fff8f0 0%, #fff 100%);
  border: 2px solid #ff9800;
}

/* Dark Mode Support */
body.body--dark .tile-attention {
  background: linear-gradient(135deg, #4a3a00 0%, #2a2a2a 100%);
  border: 2px solid #ffa726;
}
</style>
