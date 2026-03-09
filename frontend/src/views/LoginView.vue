<template>
  <q-layout view="lHh lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-grey-2">
        <q-card class="login-card q-pa-lg" style="min-width: 400px">
          <!-- Logo / Header -->
          <q-card-section class="text-center">
            <div class="text-h4 text-weight-bold text-primary q-mb-md">
              VERA Office
            </div>
            <div class="text-subtitle2 text-grey-7">
              Dokumenten-Management-System
            </div>
          </q-card-section>

          <!-- Login-Formular -->
          <q-card-section>
            <q-form @submit.prevent="handleLogin" class="q-gutter-md">
              <q-input
                v-model="username"
                label="Benutzername"
                outlined
                autofocus
                :rules="[val => !!val || 'Benutzername erforderlich']"
                @keyup.enter="handleLogin"
              >
                <template v-slot:prepend>
                  <q-icon name="person" />
                </template>
              </q-input>

              <q-input
                v-model="password"
                label="Passwort"
                type="password"
                outlined
                :rules="[val => !!val || 'Passwort erforderlich']"
                @keyup.enter="handleLogin"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" />
                </template>
              </q-input>

              <!-- Error Message -->
              <q-banner v-if="errorMessage" class="bg-negative text-white" rounded>
                <template v-slot:avatar>
                  <q-icon name="error" />
                </template>
                {{ errorMessage }}
              </q-banner>

              <!-- Login Button -->
              <q-btn
                type="submit"
                label="Anmelden"
                color="primary"
                size="lg"
                class="full-width"
                :loading="authStore.loading"
                :disable="!username || !password"
              />
            </q-form>
          </q-card-section>

          <!-- Footer -->
          <q-card-section class="text-center text-grey-6 text-caption">
            © 2026 VERA Office — On-Premise Dokumenten-Management
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

<style scoped>
.login-card {
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  border-radius: 16px;
}
</style>
