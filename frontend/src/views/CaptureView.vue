<template>
  <q-page class="flex flex-center bg-grey-2">
    <!-- Tab Selection -->
    <div v-if="!cameraActive && !capturedImage && !uploading" class="full-width">
      <q-tabs
        v-model="activeTab"
        dense
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="justify"
      >
        <q-tab name="camera" label="Kamera" icon="camera_alt" />
        <q-tab name="scanner" label="Scanner" icon="scanner" />
        <q-tab name="file" label="Datei" icon="upload_file" />
      </q-tabs>

      <q-separator />

      <q-tab-panels v-model="activeTab" animated>
        <!-- Camera Tab -->
        <q-tab-panel name="camera" class="text-center q-pa-lg">
          <q-btn
            unelevated
            color="primary"
            size="xl"
            icon="camera_alt"
            label="Kamera starten"
            @click="startCamera"
            style="min-height: 80px; min-width: 300px"
          />
          
          <!-- iOS native camera fallback -->
          <div v-if="isIOS" class="q-mt-lg">
            <div class="text-grey-7 q-mb-md">iOS: Native Kamera nutzen</div>
            <q-btn
              unelevated
              color="secondary"
              icon="photo_camera"
              label="Foto aufnehmen (iOS)"
              @click="triggerIOSCamera"
            />
            <input
              ref="iosCameraInput"
              type="file"
              accept="image/*"
              capture="environment"
              style="display: none"
              @change="handleFileUpload"
            />
          </div>
        </q-tab-panel>

        <!-- Scanner Tab -->
        <q-tab-panel name="scanner" class="q-pa-lg">
          <div v-if="!scannersLoaded" class="text-center">
            <q-btn
              unelevated
              color="primary"
              icon="search"
              label="Scanner suchen"
              @click="discoverScanners"
              :loading="scannerDiscovering"
            />
          </div>

          <div v-else-if="availableScanners.length === 0" class="text-center">
            <q-icon name="scanner" size="64px" color="grey-5" />
            <div class="text-h6 q-mt-md text-grey-7">Keine Scanner gefunden</div>
            <q-btn
              flat
              color="primary"
              label="Erneut suchen"
              icon="refresh"
              @click="discoverScanners"
              class="q-mt-md"
            />
          </div>

          <q-list v-else bordered separator>
            <q-item
              v-for="scanner in availableScanners"
              :key="scanner.id"
              clickable
              @click="selectedScanner = scanner"
              :active="selectedScanner?.id === scanner.id"
              active-class="bg-primary text-white"
            >
              <q-item-section avatar>
                <q-icon name="scanner" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ scanner.name }}</q-item-label>
                <q-item-label caption>{{ scanner.ip }}:{{ scanner.port }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <div v-if="selectedScanner" class="text-center q-mt-lg">
            <q-btn
              unelevated
              color="primary"
              size="lg"
              icon="scanner"
              label="Scannen starten"
              @click="startScan"
              :loading="scanning"
            />
          </div>
        </q-tab-panel>

        <!-- File Tab -->
        <q-tab-panel name="file" class="text-center q-pa-lg">
          <q-btn
            unelevated
            color="primary"
            size="xl"
            icon="upload_file"
            label="Datei auswählen"
            @click="triggerFileInput"
            style="min-height: 80px; min-width: 300px"
          />
          <input
            ref="fileInput"
            type="file"
            accept="image/*,application/pdf"
            style="display: none"
            @change="handleFileUpload"
          />
        </q-tab-panel>
      </q-tab-panels>
    </div>

    <!-- Camera View -->
    <div v-if="cameraActive" class="camera-container">
      <video
        ref="videoElement"
        autoplay
        playsinline
        class="camera-video"
      ></video>
      
      <div class="camera-controls">
        <q-btn
          fab
          color="negative"
          icon="close"
          @click="stopCamera"
          class="q-mr-md"
        />
        <q-btn
          v-if="cameras.length > 1"
          fab
          color="white"
          text-color="primary"
          icon="flip_camera_ios"
          @click="switchCamera"
          class="q-mr-md"
        />
        <q-btn
          fab
          color="primary"
          icon="camera"
          size="xl"
          @click="capturePhoto"
        />
      </div>
    </div>

    <!-- Preview -->
    <div v-if="capturedImage && !uploading" class="preview-container">
      <img :src="capturedImage" alt="Vorschau" class="preview-image" />
      
      <div class="preview-controls">
        <q-btn
          unelevated
          color="grey-7"
          label="Nochmal"
          icon="refresh"
          @click="retakePhoto"
          class="q-mr-md"
        />
        <q-btn
          unelevated
          color="primary"
          label="Übernehmen"
          icon="check"
          @click="uploadImage"
        />
      </div>
    </div>

    <!-- Uploading -->
    <div v-if="uploading" class="text-center">
      <q-spinner-hourglass color="primary" size="80px" />
      <div class="text-h6 q-mt-md">Dokument wird hochgeladen...</div>
      <div class="text-caption text-grey-7">Wird klassifiziert und verarbeitet</div>
    </div>

    <!-- Camera Permission Dialog -->
    <q-dialog v-model="showPermissionDialog" persistent>
      <q-card style="min-width: 350px">
        <q-card-section class="text-center">
          <q-icon name="videocam_off" size="64px" color="negative" />
          <div class="text-h6 q-mt-md">Kamerazugriff nicht erlaubt</div>
        </q-card-section>

        <q-card-section>
          <div class="text-body2 text-grey-8">
            {{ permissionErrorMessage }}
          </div>
          <div v-if="isIOS" class="text-caption text-grey-7 q-mt-sm">
            Einstellungen → Safari → Kamera → Erlauben
          </div>
        </q-card-section>

        <q-card-actions align="center" vertical>
          <q-btn
            v-if="canOpenSettings"
            unelevated
            color="primary"
            label="Einstellungen öffnen"
            icon="settings"
            @click="openSettings"
            class="full-width q-mb-sm"
          />
          <q-btn
            unelevated
            color="primary"
            label="Erneut versuchen"
            icon="refresh"
            @click="retryCamera"
            class="full-width q-mb-sm"
          />
          <q-btn
            flat
            color="grey-7"
            label="Datei hochladen"
            icon="upload_file"
            @click="fallbackToFileUpload"
            class="full-width"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'
import { Notify } from 'quasar'
import { scannerApi } from '@/services/api'

const router = useRouter()
const documentsStore = useDocumentsStore()

const activeTab = ref('camera')
const videoElement = ref<HTMLVideoElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const iosCameraInput = ref<HTMLInputElement | null>(null)
const cameraActive = ref(false)
const capturedImage = ref<string | null>(null)
const uploading = ref(false)
const stream = ref<MediaStream | null>(null)

// Camera selection
const cameras = ref<MediaDeviceInfo[]>([])
const currentCameraIndex = ref(0)

// Permission handling
const showPermissionDialog = ref(false)
const permissionErrorMessage = ref('')
const isIOS = ref(false)
const canOpenSettings = ref(false)

// Scanner
const availableScanners = ref<any[]>([])
const selectedScanner = ref<any>(null)
const scannersLoaded = ref(false)
const scannerDiscovering = ref(false)
const scanning = ref(false)

onMounted(() => {
  detectIOS()
  enumerateCameras()
})

function detectIOS() {
  const ua = navigator.userAgent
  isIOS.value = /iPad|iPhone|iPod/.test(ua) && !(window as any).MSStream
}

async function enumerateCameras() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices.filter(device => device.kind === 'videoinput')
    
    // Prefer back camera
    const backCameraIndex = cameras.value.findIndex(camera =>
      camera.label.toLowerCase().includes('back') ||
      camera.label.toLowerCase().includes('rear') ||
      camera.label.toLowerCase().includes('environment')
    )
    if (backCameraIndex !== -1) {
      currentCameraIndex.value = backCameraIndex
    }
  } catch (error) {
    console.error('Failed to enumerate cameras:', error)
  }
}

async function startCamera() {
  try {
    const constraints: MediaStreamConstraints = {
      video: {
        facingMode: 'environment',
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    }

    // If we have multiple cameras, use deviceId
    if (cameras.value.length > 0 && cameras.value[currentCameraIndex.value]) {
      constraints.video = {
        deviceId: { exact: cameras.value[currentCameraIndex.value].deviceId },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    }

    stream.value = await navigator.mediaDevices.getUserMedia(constraints)
    
    if (videoElement.value) {
      videoElement.value.srcObject = stream.value
      cameraActive.value = true
    }
  } catch (error: any) {
    console.error('Camera access error:', error)
    handleCameraError(error)
  }
}

function handleCameraError(error: any) {
  if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
    permissionErrorMessage.value = 'Bitte erlaube den Kamerazugriff in den Browser-Einstellungen.'
    showPermissionDialog.value = true
    
    // Check if we can open settings (limited browser support)
    canOpenSettings.value = isIOS.value || 'permissions' in navigator
  } else if (error.name === 'NotFoundError') {
    permissionErrorMessage.value = 'Keine Kamera gefunden. Bitte prüfe die Hardware-Verbindung.'
    showPermissionDialog.value = true
  } else if (error.name === 'NotReadableError') {
    permissionErrorMessage.value = 'Kamera wird bereits verwendet. Bitte schließe andere Apps.'
    showPermissionDialog.value = true
  } else {
    Notify.create({
      type: 'negative',
      message: `Kamerazugriff fehlgeschlagen: ${error.message}`
    })
  }
}

function openSettings() {
  if (isIOS.value) {
    // Try to open iOS settings (may not work in all browsers)
    window.open('app-settings:')
  } else {
    // For other browsers, show instructions
    Notify.create({
      type: 'info',
      message: 'Bitte öffne die Browser-Einstellungen manuell und erlaube den Kamerazugriff.',
      timeout: 5000
    })
  }
}

function retryCamera() {
  showPermissionDialog.value = false
  startCamera()
}

function fallbackToFileUpload() {
  showPermissionDialog.value = false
  activeTab.value = 'file'
}

function switchCamera() {
  stopCamera()
  currentCameraIndex.value = (currentCameraIndex.value + 1) % cameras.value.length
  startCamera()
}

function stopCamera() {
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop())
    stream.value = null
  }
  cameraActive.value = false
}

function capturePhoto() {
  if (!videoElement.value) return

  const canvas = document.createElement('canvas')
  canvas.width = videoElement.value.videoWidth
  canvas.height = videoElement.value.videoHeight
  
  const ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.drawImage(videoElement.value, 0, 0)
    capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)
  }

  stopCamera()
}

function retakePhoto() {
  capturedImage.value = null
  startCamera()
}

function triggerFileInput() {
  fileInput.value?.click()
}

function triggerIOSCamera() {
  iosCameraInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    await uploadFile(file)
  }
}

async function uploadImage() {
  if (!capturedImage.value) return

  uploading.value = true
  try {
    // Convert base64 to blob
    const response = await fetch(capturedImage.value)
    const blob = await response.blob()
    const file = new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' })

    await uploadFile(file)
  } catch (error) {
    console.error('Upload error:', error)
    uploading.value = false
  }
}

async function uploadFile(file: File) {
  uploading.value = true
  try {
    const result = await documentsStore.uploadDocument(file)
    
    Notify.create({
      type: 'positive',
      message: `Dokument erfolgreich hochgeladen: ${result.document_type || 'Unbekannt'}`,
      timeout: 4000
    })

    // Reset and navigate
    capturedImage.value = null
    uploading.value = false
    router.push('/documents')
  } catch (error) {
    console.error('Upload error:', error)
    uploading.value = false
    Notify.create({
      type: 'negative',
      message: 'Upload fehlgeschlagen. Bitte erneut versuchen.'
    })
  }
}

// Scanner functions
async function discoverScanners() {
  scannerDiscovering.value = true
  try {
    const response = await scannerApi.discover()
    availableScanners.value = response.scanners || []
    scannersLoaded.value = true
    
    if (availableScanners.value.length === 0) {
      Notify.create({
        type: 'info',
        message: 'Keine Scanner im Netzwerk gefunden.'
      })
    } else {
      Notify.create({
        type: 'positive',
        message: `${availableScanners.value.length} Scanner gefunden.`
      })
    }
  } catch (error) {
    console.error('Scanner discovery error:', error)
    Notify.create({
      type: 'negative',
      message: 'Scanner-Suche fehlgeschlagen.'
    })
    scannersLoaded.value = true
  } finally {
    scannerDiscovering.value = false
  }
}

async function startScan() {
  if (!selectedScanner.value) return

  scanning.value = true
  try {
    const response = await scannerApi.scan(selectedScanner.value.id, {
      resolution: 300,
      color_mode: 'color',
      format: 'jpeg'
    })

    // Convert response to image preview
    if (response.image_data) {
      capturedImage.value = `data:image/jpeg;base64,${response.image_data}`
    }

    Notify.create({
      type: 'positive',
      message: 'Scan erfolgreich!'
    })
  } catch (error) {
    console.error('Scan error:', error)
    Notify.create({
      type: 'negative',
      message: 'Scan fehlgeschlagen. Bitte erneut versuchen.'
    })
  } finally {
    scanning.value = false
  }
}
</script>

<style scoped>
.camera-container {
  position: relative;
  width: 100%;
  height: 100vh;
  background: black;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-controls {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
}

.preview-container {
  position: relative;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.preview-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.preview-controls {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  gap: 16px;
}
</style>
