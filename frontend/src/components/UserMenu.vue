<template>
  <div>
    <q-btn-dropdown
      flat
      round
      dense
      icon="account_circle"
      no-caps
      :ripple="false"
    >
      <q-list>
      <!-- User Info Header -->
      <q-item class="q-py-md" style="min-width: 200px;">
        <q-item-section avatar>
          <q-avatar color="primary" text-color="white" icon="account_circle" />
        </q-item-section>
        <q-item-section>
          <q-item-label class="text-weight-bold">{{ userName }}</q-item-label>
          <q-item-label caption>{{ userEmail }}</q-item-label>
        </q-item-section>
      </q-item>

      <q-separator />

      <!-- Menu Items -->
      <q-item clickable v-close-popup @click="goToProfile" v-if="profileRouteExists">
        <q-item-section avatar>
          <q-icon name="person" />
        </q-item-section>
        <q-item-section>
          <q-item-label>Profil</q-item-label>
        </q-item-section>
      </q-item>

      <q-item clickable v-close-popup @click="goToSettings">
        <q-item-section avatar>
          <q-icon name="settings" />
        </q-item-section>
        <q-item-section>
          <q-item-label>Einstellungen</q-item-label>
        </q-item-section>
      </q-item>

      <q-item clickable v-close-popup @click="openFeedback">
        <q-item-section avatar>
          <q-icon name="feedback" color="primary" />
        </q-item-section>
        <q-item-section>
          <q-item-label>Feedback senden</q-item-label>
        </q-item-section>
      </q-item>

      <q-separator />

      <q-item clickable v-close-popup @click="handleLogout">
        <q-item-section avatar>
          <q-icon name="logout" color="negative" />
        </q-item-section>
        <q-item-section>
          <q-item-label class="text-negative">Abmelden</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>

  <!-- Feedback Dialog -->
  <FeedbackDialog v-model="showFeedbackDialog" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import FeedbackDialog from './FeedbackDialog.vue'

const authStore = useAuthStore()
const router = useRouter()
const $q = useQuasar()

// Feedback Dialog
const showFeedbackDialog = ref(false)

// User Info aus Auth Store
const userName = computed(() => authStore.user?.username || 'Benutzer')
const userEmail = computed(() => authStore.user?.email || '')

// Prüfe ob /profile Route existiert
const profileRouteExists = ref(false)
try {
  router.hasRoute('profile') // oder router.getRoutes().find(r => r.name === 'profile')
  profileRouteExists.value = true
} catch {
  profileRouteExists.value = false
}

/**
 * Navigation zu Profil (optional, nur wenn Route existiert)
 */
function goToProfile() {
  router.push('/profile')
}

/**
 * Navigation zu Einstellungen
 */
function goToSettings() {
  router.push('/settings')
}

/**
 * Öffne Feedback Dialog
 */
function openFeedback() {
  showFeedbackDialog.value = true
}

/**
 * Logout mit Bestätigung
 */
async function handleLogout() {
  $q.dialog({
    title: 'Abmelden',
    message: 'Möchten Sie sich wirklich abmelden?',
    cancel: {
      label: 'Abbrechen',
      flat: true
    },
    ok: {
      label: 'Abmelden',
      color: 'negative',
      flat: true
    },
    persistent: true
  }).onOk(async () => {
    try {
      // Logout aus Auth Store
      await authStore.logout()
      
      // Redirect zu Login
      router.push('/login')
      
      // Success Notification
      $q.notify({
        type: 'positive',
        message: 'Erfolgreich abgemeldet',
        position: 'top'
      })
    } catch (error) {
      console.error('Logout error:', error)
      $q.notify({
        type: 'negative',
        message: 'Fehler beim Abmelden',
        position: 'top'
      })
    }
  })
}
</script>

<style scoped>
/* Optional: Custom Styling */
</style>
