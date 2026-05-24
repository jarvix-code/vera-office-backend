<template>
  <q-layout view="lHh lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center login-page">
        <q-card class="login-card" bordered flat>
          
          <!-- Logo Section -->
          <q-card-section class="text-center q-pt-xl q-pb-lg">
            <div class="login-logo q-mb-lg">
              <img src="/vera-logo.svg" alt="VERA Office" class="logo-image" />
            </div>
            <div class="text-subtitle1 text-grey-7">
              Dokumenten-Management für Ihre Praxis
            </div>
          </q-card-section>

          <!-- Login Form (TOUCH-OPTIMIZED) -->
          <q-card-section class="q-px-xl q-pb-xl">
            <q-form @submit.prevent="handleLogin" class="login-form">
              
              <!-- Username Input -->
              <q-input
                v-model="username"
                label="Benutzername"
                outlined
                autofocus
                class="touch-input q-mb-lg"
                :rules="[val => !!val || 'Benutzername erforderlich']"
                @keyup.enter="handleLogin"
              >
                <template v-slot:prepend>
                  <q-icon name="person" size="md" />
                </template>
              </q-input>

              <!-- Password Input -->
              <q-input
                v-model="password"
                label="Passwort"
                type="password"
                outlined
                class="touch-input q-mb-lg"
                :rules="[val => !!val || 'Passwort erforderlich']"
                @keyup.enter="handleLogin"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" size="md" />
                </template>
              </q-input>

              <!-- Error Message -->
              <q-banner v-if="errorMessage" class="bg-negative text-white q-mb-lg" rounded dense>
                <template v-slot:avatar>
                  <q-icon name="warning" size="sm" />
                </template>
                <div class="text-body2">{{ errorMessage }}</div>
              </q-banner>

              <!-- Login Button (TOUCH-OPTIMIZED) -->
              <q-btn
                type="submit"
                label="Anmelden"
                color="primary"
                unelevated
                no-caps
                class="full-width touch-button"
                :loading="authStore.loading"
                :disable="!username || !password"
              >
                <template v-slot:loading>
                  <q-spinner color="white" size="24px" />
                  <span class="q-ml-sm">Anmeldung läuft...</span>
                </template>
              </q-btn>
            </q-form>
          </q-card-section>

          <!-- Footer -->
          <q-card-section class="text-center q-pb-lg">
            <div class="text-caption text-grey-6">
              © 2026 VERA Office — Praxis-Management-System
            </div>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Notify } from 'quasar'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const errorMessage = ref('')

async function handleLogin() {
  errorMessage.value = ''

  const result = await authStore.login(username.value, password.value)

  if (result.success) {
    Notify.create({
      type: 'positive',
      message: 'Erfolgreich angemeldet!',
      position: 'top'
    })

    // Redirect zur Home-Page oder zur vorherigen Seite
    const redirect = router.currentRoute.value.query.redirect as string || '/'
    router.push(redirect)
  } else {
    errorMessage.value = result.message || 'Anmeldung fehlgeschlagen'
  }
}
</script>

<style scoped lang="scss">
.login-page {
  background: linear-gradient(135deg, #F0F4F8 0%, #E5E9F0 100%);
  min-height: 100vh;
  padding: 24px;
}

.login-card {
  min-width: 480px;
  max-width: 560px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border-radius: 20px;
  background: #FFFFFF;
  border: 1px solid rgba(25, 118, 210, 0.1);
}

.login-logo {
  display: flex;
  justify-content: center;
  align-items: center;
}

.logo-image {
  max-width: 320px;
  height: auto;
  object-fit: contain;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0; /* Gap via q-mb-lg classes */
}

/* ────────────────────────────────────────────────────────────── */
/* TOUCH-OPTIMIZED INPUTS (iPad Medical UI Standard: 56-64px)     */
/* ────────────────────────────────────────────────────────────── */

.touch-input {
  font-size: 18px; /* Größere Schrift für iPad */
}

.touch-input :deep(.q-field__control) {
  min-height: 64px; /* Touch-Target: 64px */
  padding: 0 16px;
}

.touch-input :deep(input) {
  font-size: 18px;
  line-height: 1.5;
}

.touch-input :deep(.q-field__label) {
  font-size: 16px;
}

.touch-input :deep(.q-field__prepend) {
  padding-right: 12px;
}

/* ────────────────────────────────────────────────────────────── */
/* TOUCH-OPTIMIZED BUTTON (Medical Standard: 64px)                */
/* ────────────────────────────────────────────────────────────── */

.touch-button {
  min-height: 64px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 12px;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
  transition: all 0.2s ease;
}

.touch-button:hover {
  box-shadow: 0 6px 16px rgba(25, 118, 210, 0.3);
  transform: translateY(-2px);
}

.touch-button:active {
  transform: translateY(0);
}

/* ────────────────────────────────────────────────────────────── */
/* RESPONSIVE: iPad Landscape → Größeres Logo                     */
/* ────────────────────────────────────────────────────────────── */

@media (min-width: 768px) and (orientation: landscape) {
  .logo-image {
    max-width: 400px;
  }
  
  .login-card {
    min-width: 560px;
    max-width: 640px;
  }
}

/* Mobile/Portrait: Kleinere Card */
@media (max-width: 600px) {
  .login-card {
    min-width: 100%;
    max-width: 100%;
    margin: 0;
  }
  
  .logo-image {
    max-width: 240px;
  }
  
  .login-page {
    padding: 16px;
  }
}
</style>
