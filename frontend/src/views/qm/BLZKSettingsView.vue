<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">🏛️ BLZK Portal</div>

    <!-- Connection Status -->
    <q-card flat bordered class="q-mb-lg">
      <q-card-section>
        <div class="row items-center q-gutter-sm">
          <q-icon
            :name="status.configured ? 'check_circle' : 'warning'"
            :color="status.configured ? 'positive' : 'grey'"
            size="28px"
          />
          <div>
            <div class="text-subtitle1 text-weight-medium">
              {{ status.configured ? 'Verbunden' : 'Nicht konfiguriert' }}
            </div>
            <div v-if="status.username" class="text-caption text-grey-7">
              Benutzer: {{ status.username }}
            </div>
          </div>
          <q-space />
          <q-btn
            v-if="status.configured"
            label="Trennen"
            color="negative"
            outline
            :loading="deleting"
            class="touch-btn"
            @click="deleteCredentials"
          />
        </div>
      </q-card-section>

      <!-- Connection Test Result -->
      <q-card-section v-if="testResult" class="q-pt-none">
        <q-banner
          :class="testResult.success ? 'bg-positive text-white' : 'bg-negative text-white'"
          rounded
        >
          <template v-slot:avatar>
            <q-icon :name="testResult.success ? 'check' : 'error'" />
          </template>
          {{ testResult.message || testResult.error }}
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Credentials Form -->
    <q-card flat bordered class="q-mb-lg">
      <q-card-section>
        <div class="text-h6 q-mb-md">Zugangsdaten</div>

        <q-input
          v-model="form.username"
          label="Benutzername"
          outlined
          class="q-mb-md"
          autocomplete="username"
          input-class="text-body1"
        >
          <template v-slot:prepend>
            <q-icon name="person" />
          </template>
        </q-input>

        <q-input
          v-model="form.password"
          label="Passwort"
          type="password"
          outlined
          class="q-mb-md"
          autocomplete="current-password"
          input-class="text-body1"
        >
          <template v-slot:prepend>
            <q-icon name="lock" />
          </template>
        </q-input>

        <div class="row q-gutter-sm">
          <q-btn
            label="Speichern & Verbinden"
            color="primary"
            :loading="saving"
            :disable="!form.username || !form.password"
            class="touch-btn"
            @click="saveAndTest"
          />
          <q-btn
            v-if="status.configured"
            label="Verbindung testen"
            color="secondary"
            outline
            :loading="testing"
            class="touch-btn"
            @click="testConnection"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Info Card -->
    <q-card flat bordered>
      <q-card-section>
        <div class="text-caption text-grey-7">
          <q-icon name="info" class="q-mr-xs" />
          Die Zugangsdaten werden verschlüsselt auf dem Server gespeichert.
          Sie werden ausschließlich für den Zugriff auf das BLZK QM-Portal verwendet.
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { qmApi } from '@/services/qm-api'
import { Notify } from 'quasar'

const status = ref<{ configured: boolean; username: string | null; has_password: boolean }>({
  configured: false,
  username: null,
  has_password: false,
})

const form = ref({ username: '', password: '' })
const saving = ref(false)
const testing = ref(false)
const deleting = ref(false)
const testResult = ref<{ success: boolean; message?: string; error?: string } | null>(null)

async function loadStatus() {
  try {
    status.value = await qmApi.getBLZKCredentials()
  } catch {
    // Not configured
  }
}

async function saveAndTest() {
  saving.value = true
  testResult.value = null
  try {
    await qmApi.saveBLZKCredentials({
      username: form.value.username,
      password: form.value.password,
    })
    // Test login
    testResult.value = await qmApi.testBLZKLogin({
      username: form.value.username,
      password: form.value.password,
    })
    await loadStatus()
    form.value.password = ''
    if (testResult.value.success) {
      Notify.create({ type: 'positive', message: 'BLZK-Verbindung erfolgreich!' })
    }
  } catch (e: any) {
    testResult.value = { success: false, error: e.response?.data?.detail || 'Fehler beim Speichern' }
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await qmApi.testBLZKLogin()
  } catch (e: any) {
    testResult.value = { success: false, error: e.response?.data?.detail || 'Verbindungsfehler' }
  } finally {
    testing.value = false
  }
}

async function deleteCredentials() {
  deleting.value = true
  try {
    await qmApi.deleteBLZKCredentials()
    status.value = { configured: false, username: null, has_password: false }
    testResult.value = null
    form.value = { username: '', password: '' }
    Notify.create({ type: 'info', message: 'BLZK-Zugangsdaten gelöscht' })
  } catch {
    Notify.create({ type: 'negative', message: 'Fehler beim Löschen' })
  } finally {
    deleting.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.touch-btn {
  min-height: 44px;
  min-width: 44px;
  font-size: 15px;
}
</style>
