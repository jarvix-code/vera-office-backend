<template>
  <q-page class="flex flex-center bg-grey-1 module-auth-page">
    <q-card class="module-auth-card" flat bordered>

      <!-- Header -->
      <q-card-section class="chat-header q-py-sm q-px-md">
        <div class="row items-center no-wrap">
          <q-avatar color="primary" text-color="white" size="38px" class="q-mr-sm">
            <q-icon name="lock" size="20px" />
          </q-avatar>
          <div>
            <div class="text-subtitle1 text-weight-bold" style="line-height:1.2">
              {{ moduleDisplayName }} — Zugriff
            </div>
            <div class="text-caption text-grey-5">VERA · Sicherheitsbereich</div>
          </div>
          <q-space />
          <q-btn flat round dense icon="close" @click="goBack" />
        </div>
      </q-card-section>

      <q-separator />

      <!-- Chat Messages -->
      <q-scroll-area ref="scrollArea" class="chat-messages">
        <div class="q-pa-md">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="q-mb-md"
            :class="msg.role === 'user' ? 'text-right' : 'text-left'"
          >
            <div
              class="chat-bubble inline-block q-px-md q-py-sm"
              :class="msg.role === 'user' ? 'bubble-user' : 'bubble-vera'"
              style="max-width: 88%; white-space: pre-wrap; text-align: left;"
            >{{ msg.role === 'user' ? msg.masked : msg.text }}</div>
          </div>

          <div v-if="loading" class="text-left q-mb-md">
            <div class="chat-bubble bubble-vera inline-block q-px-md q-py-sm">
              <q-spinner-dots color="primary" size="22px" />
            </div>
          </div>
        </div>
      </q-scroll-area>

      <q-separator />

      <!-- PIN Input -->
      <q-card-section class="q-pa-sm" v-if="!done">
        <div class="row items-center no-wrap q-gutter-sm">
          <!-- PIN digit buttons (mobile-friendly) -->
          <div class="col">
            <!-- Masked PIN display -->
            <div class="pin-display row items-center justify-center q-mb-sm">
              <div
                v-for="i in expectedLength"
                :key="i"
                class="pin-dot"
                :class="{ filled: pinInput.length >= i }"
              />
            </div>
            <!-- Number pad -->
            <div class="numpad">
              <div class="numpad-row" v-for="row in numpadRows" :key="row.join('')">
                <q-btn
                  v-for="digit in row"
                  :key="digit"
                  :label="digit === 'del' ? '' : digit"
                  :icon="digit === 'del' ? 'backspace' : undefined"
                  flat
                  class="numpad-btn"
                  :class="{ 'del-btn': digit === 'del' }"
                  @click="pressDigit(digit)"
                  :disable="loading"
                />
              </div>
            </div>
          </div>
        </div>
      </q-card-section>

      <!-- Success / Error feedback -->
      <q-card-section v-if="done && !error" class="text-center">
        <q-icon name="check_circle" color="positive" size="48px" />
        <div class="text-subtitle1 q-mt-sm">Zugriff gewährt! Weiterleitung...</div>
      </q-card-section>

      <q-card-section v-if="error" class="text-center">
        <q-banner class="bg-negative text-white" rounded>
          <template v-slot:avatar><q-icon name="error" /></template>
          {{ error }}
        </q-banner>
        <q-btn flat color="primary" label="Nochmal versuchen" class="q-mt-sm" @click="reset" />
      </q-card-section>

    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const module = computed(() => (route.query.module as string) || '')
const mode = computed(() => (route.query.mode as string) || 'pin') // 'pin' | 'unlock'
const redirectTo = computed(() => (route.query.redirect as string) || '/')

const MODULE_NAMES: Record<string, string> = {
  qm: 'QM-Modul',
  erp: 'ERP / Finanzen',
  datev: 'DATEV-Export',
}

const moduleDisplayName = computed(() => MODULE_NAMES[module.value] || module.value.toUpperCase())

interface ChatMessage {
  role: 'vera' | 'user'
  text: string
  masked?: string
}

const messages = ref<ChatMessage[]>([])
const pinInput = ref('')
const loading = ref(false)
const done = ref(false)
const error = ref('')
const scrollArea = ref<any>(null)

// Mode: pin (6 digits) or unlock/master (8 digits)
const isPinMode = computed(() => mode.value === 'pin')
const expectedLength = computed(() => isPinMode.value ? 6 : 8)

const numpadRows = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['0', 'del'],
]

onMounted(() => {
  showIntro()
})

function showIntro() {
  if (isPinMode.value) {
    messages.value.push({
      role: 'vera',
      text: `🔒 **${moduleDisplayName.value}** ist geschützt.\n\nBitte gib deine 6-stellige PIN ein um Zugriff zu erhalten.`
    })
  } else {
    messages.value.push({
      role: 'vera',
      text: `🔑 Modul freischalten: **${moduleDisplayName.value}**\n\nGib dein 8-stelliges Master-Passwort ein um das Modul freizuschalten.`
    })
  }
  scrollToBottom()
}

function pressDigit(digit: string) {
  if (digit === 'del') {
    pinInput.value = pinInput.value.slice(0, -1)
    return
  }
  if (pinInput.value.length >= expectedLength.value) return
  pinInput.value += digit

  if (pinInput.value.length === expectedLength.value) {
    // Auto-submit when full
    submitPin()
  }
}

async function submitPin() {
  const value = pinInput.value
  loading.value = true
  error.value = ''

  // Show masked input in chat
  messages.value.push({
    role: 'user',
    text: value,
    masked: '●'.repeat(value.length)
  })
  await scrollToBottom()

  try {
    let result: { success: boolean; message?: string }

    if (isPinMode.value) {
      result = await authStore.verifyPin(value)
      if (result.success) {
        messages.value.push({ role: 'vera', text: '✅ PIN korrekt! Zugriff gewährt.' })
        await scrollToBottom()
        done.value = true
        setTimeout(() => router.push(redirectTo.value), 800)
      } else {
        error.value = result.message || 'Falsche PIN'
        messages.value.push({ role: 'vera', text: `❌ ${error.value}\n\nBitte versuche es nochmal.` })
        await scrollToBottom()
        pinInput.value = ''
      }
    } else {
      // Unlock mode — master PW
      result = await authStore.unlockModule(module.value, value)
      if (result.success) {
        messages.value.push({
          role: 'vera',
          text: `✅ **${moduleDisplayName.value}** ist jetzt freigeschaltet!\n\nDu kannst es ab sofort nutzen.`
        })
        await scrollToBottom()
        done.value = true
        // Now also verify PIN to get session access
        setTimeout(() => {
          // Switch to PIN mode for immediate access
          router.replace({
            path: '/module-auth',
            query: { module: module.value, mode: 'pin', redirect: redirectTo.value }
          })
        }, 1500)
      } else {
        error.value = result.message || 'Falsches Master-Passwort'
        messages.value.push({ role: 'vera', text: `❌ ${error.value}\n\nBitte versuche es nochmal.` })
        await scrollToBottom()
        pinInput.value = ''
      }
    }
  } finally {
    loading.value = false
  }
}

function reset() {
  pinInput.value = ''
  error.value = ''
  messages.value = []
  done.value = false
  showIntro()
}

function goBack() {
  router.back()
}

async function scrollToBottom() {
  await nextTick()
  if (scrollArea.value) {
    const el = scrollArea.value.$el?.querySelector('.q-scrollarea__container')
    if (el) el.scrollTop = el.scrollHeight
  }
}
</script>

<style scoped>
.module-auth-page {
  min-height: 100vh;
}

.module-auth-card {
  width: 100%;
  max-width: 380px;
  margin: 16px;
}

.chat-header {
  background: #fafafa;
}

.chat-messages {
  height: 220px;
}

.chat-bubble {
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
}

.bubble-vera {
  background: #f0f0f0;
  color: #222;
  border-bottom-left-radius: 4px;
}

.bubble-user {
  background: #1976d2;
  color: white;
  border-bottom-right-radius: 4px;
  font-family: monospace;
  letter-spacing: 0.15em;
}

/* PIN dot display */
.pin-display {
  gap: 12px;
  padding: 8px 0;
}

.pin-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #1976d2;
  background: transparent;
  transition: background 0.15s;
}

.pin-dot.filled {
  background: #1976d2;
}

/* Numpad */
.numpad {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.numpad-row {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.numpad-btn {
  width: 72px;
  height: 52px;
  font-size: 22px;
  font-weight: 500;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.del-btn {
  font-size: 16px;
}
</style>
