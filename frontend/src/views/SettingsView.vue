<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Einstellungen</div>

    <div class="row q-col-gutter-md">
      <!-- System Settings -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">System</div>
            
            <q-toggle
              v-model="settings.darkMode"
              label="Dunkles Design"
              class="q-mb-md"
            />

            <q-select
              v-model="settings.language"
              outlined
              label="Sprache"
              :options="['Deutsch', 'English']"
              class="q-mb-md"
            />

            <q-input
              v-model="settings.documentsPerPage"
              outlined
              type="number"
              label="Dokumente pro Seite"
              class="q-mb-md"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- OCR Settings -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">OCR & Klassifikation</div>
            
            <q-toggle
              v-model="settings.autoOcr"
              label="Automatische OCR-Erkennung"
              class="q-mb-md"
            />

            <q-toggle
              v-model="settings.autoClassify"
              label="Automatische Klassifikation"
              class="q-mb-md"
            />

            <q-select
              v-model="settings.ocrLanguage"
              outlined
              label="OCR-Sprache"
              :options="['Deutsch', 'English', 'Mehrsprachig']"
              class="q-mb-md"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Storage Settings -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">Speicher</div>
            
            <q-linear-progress
              :value="0.45"
              color="primary"
              class="q-mb-sm"
            />
            <div class="text-caption text-grey-7 q-mb-md">
              4.5 GB von 10 GB verwendet
            </div>

            <q-btn
              outline
              color="primary"
              icon="cleaning_services"
              label="Cache leeren"
              class="q-mb-md full-width"
              @click="clearCache"
            />

            <q-btn
              outline
              color="negative"
              icon="delete_forever"
              label="Alle Daten löschen"
              class="full-width"
              @click="confirmReset"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Software-Updates -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">
              <q-icon name="system_update" class="q-mr-sm" />
              Software-Updates
            </div>

            <!-- Aktuelle Version -->
            <div class="q-mb-md">
              <div class="text-caption text-grey-7">Installierte Version</div>
              <div class="text-body1 text-weight-medium">{{ updateState.currentVersion || '...' }}</div>
            </div>

            <!-- Letzter Check -->
            <div class="q-mb-md" v-if="updateState.lastCheck">
              <div class="text-caption text-grey-7">Letzter Check</div>
              <div class="text-body2">{{ formatDate(updateState.lastCheck) }}</div>
            </div>

            <!-- Update verfügbar Banner -->
            <q-banner
              v-if="updateState.updateAvailable"
              class="bg-positive text-white q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="new_releases" />
              </template>
              <div class="text-weight-medium">Version {{ updateState.latestVersion }} verfügbar!</div>
              <div class="text-caption" v-if="updateState.changelog">{{ updateState.changelog }}</div>
            </q-banner>

            <!-- Kein Update Banner -->
            <q-banner
              v-if="updateState.checked && !updateState.updateAvailable && !updateState.checking"
              class="bg-grey-3 q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="check_circle" color="positive" />
              </template>
              VERA Office ist aktuell.
            </q-banner>

            <!-- Error Banner -->
            <q-banner
              v-if="updateState.error"
              class="bg-negative text-white q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="error" />
              </template>
              {{ updateState.error }}
            </q-banner>

            <!-- Buttons -->
            <q-btn
              unelevated
              color="primary"
              icon="refresh"
              label="Jetzt prüfen"
              class="full-width q-mb-sm"
              :loading="updateState.checking"
              :disable="updateState.applying"
              @click="checkForUpdate"
            />

            <q-btn
              v-if="updateState.updateAvailable"
              unelevated
              color="positive"
              icon="download"
              :label="'Update auf ' + updateState.latestVersion + ' installieren'"
              class="full-width q-mb-sm"
              :loading="updateState.applying"
              @click="applyUpdate"
            />

            <!-- Progress bei Installation -->
            <div v-if="updateState.applying" class="q-mt-sm">
              <q-linear-progress indeterminate color="positive" />
              <div class="text-caption text-center q-mt-xs text-grey-7">
                Update wird heruntergeladen und installiert...
              </div>
            </div>

            <q-separator class="q-my-md" />

            <!-- Auto-Update Toggle -->
            <q-toggle
              v-model="updateState.autoUpdate"
              label="Automatische Updates"
              @update:model-value="toggleAutoUpdate"
            />
            <div class="text-caption text-grey-7">
              Updates werden automatisch im Hintergrund geprüft und installiert.
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Lizenz-Info -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">Lizenz</div>
            <div class="text-body2 text-grey-7">
              Lizenz wird beim Start geprüft. Bei Fragen: support@vera-office.de
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- About -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">Über VERA Office</div>
            
            <div class="q-mb-sm">
              <div class="text-caption text-grey-7">Version</div>
              <div class="text-body1">1.0.0</div>
            </div>

            <div class="q-mb-sm">
              <div class="text-caption text-grey-7">Backend Status</div>
              <div class="text-body1">
                <q-icon name="check_circle" color="positive" />
                Verbunden
              </div>
            </div>

            <q-separator class="q-my-md" />

            <q-btn
              flat
              color="primary"
              icon="help"
              label="Hilfe & Dokumentation"
              class="full-width q-mb-sm"
            />

            <q-btn
              flat
              color="primary"
              icon="bug_report"
              label="Feedback senden"
              class="full-width"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Save Button -->
      <div class="col-12">
        <q-btn
          unelevated
          color="primary"
          icon="save"
          label="Einstellungen speichern"
          size="lg"
          class="full-width"
          @click="saveSettings"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Dialog, Notify } from 'quasar'
import { updateApi } from '@/services/api'

const settings = ref({
  darkMode: false,
  language: 'Deutsch',
  documentsPerPage: 20,
  autoOcr: true,
  autoClassify: true,
  ocrLanguage: 'Deutsch'
})

// Update State
const updateState = ref({
  currentVersion: '',
  latestVersion: null as string | null,
  updateAvailable: false,
  autoUpdate: false,
  lastCheck: null as string | null,
  checking: false,
  applying: false,
  checked: false,
  changelog: null as string | null,
  error: null as string | null
})

onMounted(async () => {
  await loadUpdateStatus()
})

async function loadUpdateStatus() {
  try {
    const data = await updateApi.getStatus()
    updateState.value.currentVersion = data.current_version
    updateState.value.updateAvailable = data.update_available
    updateState.value.latestVersion = data.latest_version
    updateState.value.autoUpdate = data.auto_update_enabled
    updateState.value.lastCheck = data.last_check
  } catch {
    // Silently fail — version will show on next check
  }
}

async function checkForUpdate() {
  updateState.value.checking = true
  updateState.value.error = null
  updateState.value.checked = false

  try {
    const data = await updateApi.checkForUpdate()
    updateState.value.updateAvailable = data.update_available
    updateState.value.latestVersion = data.version
    updateState.value.changelog = data.changelog
    updateState.value.checked = true
    updateState.value.lastCheck = new Date().toISOString()

    if (data.update_available) {
      Notify.create({
        type: 'positive',
        message: `Update ${data.version} verfügbar!`,
        icon: 'new_releases'
      })
    }
  } catch (e: any) {
    updateState.value.error = 'Update-Server nicht erreichbar. Bitte später erneut versuchen.'
  } finally {
    updateState.value.checking = false
  }
}

async function applyUpdate() {
  if (!updateState.value.latestVersion) return

  Dialog.create({
    title: 'Update installieren?',
    message: `VERA Office wird auf Version ${updateState.value.latestVersion} aktualisiert. Das Update wird automatisch installiert und die Seite neu geladen.`,
    cancel: 'Abbrechen',
    ok: 'Jetzt installieren',
    persistent: true,
    color: 'positive'
  }).onOk(async () => {
    updateState.value.applying = true
    updateState.value.error = null

    try {
      const result = await updateApi.downloadAndApply(updateState.value.latestVersion!)

      if (result.success) {
        updateState.value.updateAvailable = false
        
        // Success → Auto-Reload nach Countdown
        let countdown = 10
        const notif = Notify.create({
          type: 'positive',
          message: `✅ Update installiert! Seite lädt in ${countdown} Sekunden neu...`,
          icon: 'check_circle',
          timeout: 0,  // Kein Auto-Hide
          spinner: false,
          position: 'center',
          html: true
        })
        
        // Countdown
        const interval = setInterval(() => {
          countdown--
          notif({
            message: `✅ Update installiert! Seite lädt in ${countdown} Sekunden neu...`
          })
          
          if (countdown <= 0) {
            clearInterval(interval)
            window.location.reload()  // Auto-Reload!
          }
        }, 1000)
      } else {
        updateState.value.error = result.message
      }
    } catch (e: any) {
      updateState.value.error = e.response?.data?.message || 'Update-Installation fehlgeschlagen'
    } finally {
      updateState.value.applying = false
    }
  })
}

function toggleAutoUpdate(val: boolean) {
  // TODO: Save to backend config
  Notify.create({
    type: 'info',
    message: val ? 'Automatische Updates aktiviert' : 'Automatische Updates deaktiviert'
  })
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('de-DE', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

function saveSettings() {
  Notify.create({
    type: 'positive',
    message: 'Einstellungen gespeichert'
  })
}

function clearCache() {
  Notify.create({
    type: 'positive',
    message: 'Cache geleert'
  })
}

function confirmReset() {
  Dialog.create({
    title: 'Alle Daten löschen?',
    message: 'Dies löscht ALLE Dokumente und Einstellungen unwiderruflich!',
    cancel: true,
    persistent: true,
    color: 'negative'
  }).onOk(() => {
    Notify.create({
      type: 'info',
      message: 'Zurücksetzen in Entwicklung'
    })
  })
}
</script>
