<template>
  <q-dialog v-model="visible" persistent>
    <q-card style="min-width: 380px; border-radius: 16px;">

      <!-- Header -->
      <q-card-section class="text-center q-pt-xl q-pb-md">
        <q-icon
          :name="mode === 'unlock' ? 'lock_open' : 'pin'"
          :color="mode === 'unlock' ? 'orange-7' : 'primary'"
          size="48px"
        />
        <div class="text-h6 text-weight-bold q-mt-md">
          {{ mode === 'unlock' ? 'Modul freischalten' : 'Zugriff auf ' + moduleDisplayName }}
        </div>
        <div class="text-caption text-grey-6 q-mt-xs">
          {{ mode === 'unlock'
            ? 'Gib deinen Promo-Code ein um das Modul freizuschalten'
            : 'Wer bist du? Gib deinen Namen und deine 6-stellige PIN ein.' }}
        </div>
      </q-card-section>

      <!-- VERA Hinweis wenn Modul nicht freigeschaltet -->
      <q-card-section v-if="showUnlockOption && mode === 'pin'" class="q-pt-none q-pb-sm">
        <q-banner class="bg-orange-1 rounded-borders" rounded>
          <template v-slot:avatar>
            <q-icon name="info" color="orange-7" />
          </template>
          <div class="text-body2">
            Dieses Modul ist noch nicht für dich freigeschaltet.
          </div>
          <template v-slot:action>
            <q-btn
              flat
              dense
              color="orange-8"
              label="Freischalten"
              @click="mode = 'unlock'"
            />
          </template>
        </q-banner>
      </q-card-section>

      <!-- PIN Eingabe -->
      <q-card-section v-if="mode === 'pin'" class="q-pb-none">
        <q-input
          v-model="nameValue"
          outlined
          label="Dein Name"
          class="q-mb-sm"
          @keyup.enter="focusPin"
          ref="nameInput"
        />
        <q-input
          v-model="inputValue"
          outlined
          label="6-stellige PIN"
          :type="showValue ? 'text' : 'password'"
          maxlength="6"
          @keyup.enter="submit"
          :error="!!errorMsg"
          :error-message="errorMsg"
          ref="pinInput"
        >
          <template v-slot:append>
            <q-icon
              :name="showValue ? 'visibility_off' : 'visibility'"
              class="cursor-pointer"
              @click="showValue = !showValue"
            />
          </template>
        </q-input>
      </q-card-section>

      <!-- Promo-Code Eingabe (Freischaltung) -->
      <q-card-section v-else-if="mode === 'unlock'" class="q-pb-none">
        <q-input
          v-model="inputValue"
          outlined
          label="Promo-Code (z.B. VERA-DEMO-2026)"
          autofocus
          @keyup.enter="submit"
          :error="!!errorMsg"
          :error-message="errorMsg"
        />

        <q-banner class="bg-blue-1 q-mt-md rounded-borders" rounded>
          <template v-slot:avatar>
            <q-icon name="info" color="blue-6" />
          </template>
          <div class="text-caption">
            Nach der Freischaltung kannst du das Modul mit deiner PIN verwenden.
          </div>
        </q-banner>
      </q-card-section>

      <!-- Aktionen -->
      <q-card-actions align="right" class="q-pa-lg q-pt-md">
        <q-btn
          flat
          label="Abbrechen"
          color="grey-7"
          @click="cancel"
        />
        <q-btn
          v-if="mode === 'unlock'"
          flat
          label="Ich hab schon einen Code"
          color="grey-6"
          @click="mode = 'pin'; inputValue = ''; errorMsg = ''"
        />
        <q-btn
          unelevated
          :label="mode === 'unlock' ? 'Freischalten' : 'Bestätigen'"
          :color="mode === 'unlock' ? 'orange-7' : 'primary'"
          :loading="loading"
          :disable="!inputValue"
          @click="submit"
        />
      </q-card-actions>

    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { invalidateModuleLicenseCache } from '@/router'
import { Notify } from 'quasar'

const authStore = useAuthStore()
const router = useRouter()

// Dialog ist sichtbar wenn ein Modul auf Zugriff wartet
const visible = computed(() => !!authStore.pendingModuleAccess)

const moduleDisplayName = computed(() => {
  const names: Record<string, string> = {
    qm: 'QM-System',
    erp: 'ERP / Finanzen',
    datev: 'DATEV-Export'
  }
  return names[authStore.pendingModuleAccess || ''] || authStore.pendingModuleAccess || 'Modul'
})

// Modus: 'pin' = PIN eingeben, 'unlock' = Promo-Code eingeben
const mode = ref<'pin' | 'unlock'>('pin')
const inputValue = ref('')
const nameValue = ref('')
const showValue = ref(false)
const errorMsg = ref('')
const loading = ref(false)
const nameInput = ref<any>(null)
const pinInput = ref<any>(null)

// Zeige "Freischalten" Option wenn Modul nicht in unlockedModules
const showUnlockOption = computed(() => {
  const mod = authStore.pendingModuleAccess
  return mod ? !authStore.unlockedModules.includes(mod) : false
})

// Reset wenn Dialog sich öffnet
watch(visible, (val) => {
  if (val) {
    inputValue.value = ''
    nameValue.value = ''
    errorMsg.value = ''
    showValue.value = false
    // Wenn Modul nicht freigeschaltet → direkt in Unlock-Modus
    if (showUnlockOption.value) {
      mode.value = 'unlock'
    } else {
      mode.value = 'pin'
    }
  }
})

function focusPin() {
  nextTick(() => {
    pinInput.value?.focus()
  })
}

async function submit() {
  if (!inputValue.value) return

  loading.value = true
  errorMsg.value = ''

  try {
    if (mode.value === 'pin') {
      // PIN prüfen (name ist optional/cosmetic)
      const result = await authStore.verifyPin(inputValue.value)
      if (result.success) {
        const greeting = nameValue.value ? `Hallo ${nameValue.value}! ` : ''
        Notify.create({
          type: 'positive',
          message: `${greeting}Zugriff auf ${moduleDisplayName.value} gewährt`,
          position: 'top',
          timeout: 2000
        })
        onSuccess()
      } else {
        errorMsg.value = result.message || 'Falsche PIN'
        inputValue.value = ''
      }
    } else if (mode.value === 'unlock') {
      // Modul per Promo-Code freischalten
      const result = await authStore.unlockModule(inputValue.value)
      if (result.success) {
        Notify.create({
          type: 'positive',
          message: `${moduleDisplayName.value} freigeschaltet!`,
          position: 'top'
        })
        // Cache neu laden
        invalidateModuleLicenseCache()
        // Jetzt PIN eingeben
        mode.value = 'pin'
        inputValue.value = ''
        Notify.create({
          type: 'info',
          message: 'Bitte jetzt deine PIN eingeben',
          position: 'top',
          timeout: 2000
        })
      } else {
        errorMsg.value = result.message || 'Freischaltung fehlgeschlagen'
        inputValue.value = ''
      }
    }
  } finally {
    loading.value = false
  }
}

function onSuccess() {
  const redirectPath = authStore.pendingRedirectPath
  authStore.pendingModuleAccess = null
  authStore.pendingRedirectPath = null

  if (redirectPath) {
    router.push(redirectPath)
  }
}

function cancel() {
  authStore.pendingModuleAccess = null
  authStore.pendingRedirectPath = null
  inputValue.value = ''
  errorMsg.value = ''
}
</script>
