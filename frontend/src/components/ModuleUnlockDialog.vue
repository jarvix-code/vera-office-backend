<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card style="min-width: 420px; max-width: 480px;">

      <!-- Header -->
      <q-card-section class="row items-center q-pb-none">
        <q-icon
          :name="step === 'pin' ? 'lock_person' : 'redeem'"
          color="purple"
          size="sm"
          class="q-mr-sm"
        />
        <div class="text-h6">
          {{ step === 'pin' ? 'Modul-Zugang' : 'Modul freischalten' }}
        </div>
        <q-space />
        <q-btn icon="close" flat round dense @click="onCancel" />
      </q-card-section>

      <!-- Step 1: Name + PIN -->
      <template v-if="step === 'pin'">
        <q-card-section>
          <p class="text-body2 text-grey-7 q-mb-md">
            <strong>{{ moduleLabel }}</strong> ist geschützt.<br>
            Bitte gib deinen Namen und deine Modul-PIN ein.
          </p>

          <q-input
            v-model="username"
            label="Dein Name (Benutzername)"
            outlined
            dense
            autofocus
            class="q-mb-sm"
            :error="!!pinError"
            @keyup.enter="usernameField && pinField.focus()"
            ref="usernameField"
          />

          <q-input
            v-model="pin"
            label="6-stellige PIN"
            outlined
            dense
            type="password"
            maxlength="6"
            :error="!!pinError"
            :error-message="pinError"
            @keyup.enter="onVerifyPin"
            ref="pinField"
          />
        </q-card-section>

        <q-card-actions align="right" class="q-pt-none">
          <q-btn flat label="Abbrechen" color="grey" @click="onCancel" />
          <q-btn
            unelevated
            label="Bestätigen"
            color="purple"
            icon-right="arrow_forward"
            :loading="loading"
            :disable="!username || pin.length !== 6"
            @click="onVerifyPin"
          />
        </q-card-actions>
      </template>

      <!-- Step 2: Promo Code -->
      <template v-if="step === 'promo'">
        <q-card-section>
          <p class="text-body2 text-grey-7 q-mb-md">
            Hallo <strong>{{ sessionUsername }}</strong>! Du hast noch keinen Zugang zu
            <strong>{{ moduleLabel }}</strong>.
          </p>
          <p class="text-body2 text-grey-7 q-mb-md">
            Hast du einen Promo-Code? Gib ihn hier ein um das Modul freizuschalten.
          </p>

          <q-input
            v-model="promoCode"
            label="Promo-Code (z.B. VERA-DEMO-2026)"
            outlined
            dense
            autofocus
            :error="!!promoError"
            :error-message="promoError"
            @keyup.enter="onRedeemPromo"
          />
        </q-card-section>

        <q-card-actions align="right" class="q-pt-none">
          <q-btn flat label="Abbrechen" color="grey" @click="onCancel" />
          <q-btn
            unelevated
            label="Freischalten"
            color="purple"
            icon-right="lock_open"
            :loading="loading"
            :disable="!promoCode"
            @click="onRedeemPromo"
          />
        </q-card-actions>
      </template>

    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useModuleAuthStore } from '@/stores/moduleAuth'
import { invalidateModuleLicenseCache } from '@/router/index'

const router = useRouter()
const $q = useQuasar()
const moduleAuth = useModuleAuthStore()

// Local state
const username = ref('')
const pin = ref('')
const pinError = ref('')
const promoCode = ref('')
const promoError = ref('')
const loading = ref(false)

const usernameField = ref<any>(null)
const pinField = ref<any>(null)

// Dialog visibility
const isOpen = computed(() => moduleAuth.dialogStep !== null)

// Current step
const step = computed(() => moduleAuth.dialogStep)

// Module display name
const MODULE_LABELS: Record<string, string> = {
  qm: 'Qualitätsmanagement (QM)',
  erp: 'ERP / Finanzen',
  datev: 'DATEV-Export',
}
const moduleLabel = computed(() =>
  MODULE_LABELS[moduleAuth.pendingModule ?? ''] ?? moduleAuth.pendingModule ?? 'Modul'
)

// Session username (after PIN step)
const sessionUsername = computed(() => moduleAuth.getSessionUsername() ?? username.value)

// Reset form when dialog closes
watch(isOpen, (open) => {
  if (!open) {
    username.value = ''
    pin.value = ''
    pinError.value = ''
    promoCode.value = ''
    promoError.value = ''
  }
})

// Pre-fill username from existing session if we're on promo step
watch(step, (s) => {
  if (s === 'pin') {
    const existing = moduleAuth.getSessionUsername()
    if (existing) username.value = existing
  }
})

async function onVerifyPin() {
  if (!username.value || pin.value.length !== 6) return

  pinError.value = ''
  loading.value = true

  const result = await moduleAuth.verifyPin(username.value, pin.value)
  loading.value = false

  if (!result.success) {
    pinError.value = result.error ?? 'Name oder PIN ungültig'
    return
  }

  // PIN korrekt → prüfe ob Modul freigeschaltet
  const modules = result.modules ?? []
  const pending = moduleAuth.pendingModule ?? ''

  if (modules.includes(pending)) {
    // Zugang gewährt → navigiere zur ursprünglichen Route
    const route = moduleAuth.pendingRoute ?? '/dashboard'
    moduleAuth.closeDialog()
    invalidateModuleLicenseCache()
    router.push(route)
  } else {
    // Modul nicht freigeschaltet → zeige Promo-Code Dialog
    moduleAuth.dialogStep = 'promo'
  }
}

async function onRedeemPromo() {
  if (!promoCode.value) return

  promoError.value = ''
  loading.value = true

  const result = await moduleAuth.redeemPromoCode(promoCode.value)
  loading.value = false

  if (!result.success) {
    promoError.value = result.error ?? 'Ungültiger Promo-Code'
    return
  }

  const modules = result.modules ?? []
  const pending = moduleAuth.pendingModule ?? ''

  if (modules.includes(pending)) {
    $q.notify({
      type: 'positive',
      message: `${moduleLabel.value} wurde freigeschaltet!`,
      icon: 'lock_open'
    })
    const route = moduleAuth.pendingRoute ?? '/dashboard'
    moduleAuth.closeDialog()
    invalidateModuleLicenseCache()
    router.push(route)
  } else {
    promoError.value = 'Dieser Code schaltet das Modul nicht frei'
  }
}

function onCancel() {
  moduleAuth.closeDialog()
  // Navigiere zum Dashboard wenn abgebrochen
  router.push('/dashboard')
}
</script>
