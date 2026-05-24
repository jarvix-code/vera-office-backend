<template>
  <q-page class="chat-page">
    <div class="chat-centered-container">

      <!-- Header: weisser Hintergrund, Logo links, Boris-Branding -->
      <div class="chat-header">
        <div class="vera-brand">
          <div class="vera-logo-wrap">
            <img src="/vera-logo.svg" alt="VERA" class="vera-logo-img" />
          </div>
          <div class="vera-info">
            <div class="vera-title">VERA Office</div>
            <div class="vera-subtitle">Deine intelligente Praxis-Assistentin</div>
          </div>
        </div>
      </div>

      <!-- Messages Area -->
      <div ref="messagesContainer" class="messages-area">
        <!-- Welcome State -->
        <div v-if="messages.length === 0 && !loading" class="welcome-state">
          <div class="welcome-logo">
            <img src="/vera-icon.svg" alt="VERA Office" class="welcome-logo-img" />
          </div>
          <div class="welcome-title">Hey! Ich bin VERA &#x1F44B;</div>
          <div class="welcome-text">
            Deine intelligente Assistentin fuer Praxis-Management.
            Waehle ein Modul oder stelle mir eine Frage.
          </div>

          <!-- 6 Modul-Karten: 2x3 Grid (Boris-Spezifikation) -->
          <div class="module-cards">
            <div
              v-for="module in modules"
              :key="module.label"
              class="module-card"
              @click="handleModuleClick(module)"
            >
              <div class="module-header-row">
                <div class="module-icon" :style="{ background: module.color }">
                  <q-icon :name="module.icon" size="28px" color="white" />
                </div>
                <div class="module-badge" v-if="module.badge">{{ module.badge }}</div>
              </div>
              <div class="module-title">{{ module.label }}</div>
              <div class="module-description">{{ module.description }}</div>
            </div>
          </div>
        </div>

        <!-- Chat Messages -->
        <transition-group name="message" tag="div" class="messages-list">
          <div
            v-for="(message, index) in messages"
            :key="'msg-' + index"
            :class="['message-item', message.role]"
          >
            <div v-if="message.role === 'assistant'" class="message-avatar">
              <q-avatar size="32px" class="assistant-avatar">
                <q-icon name="auto_awesome" size="18px" />
              </q-avatar>
            </div>
            <div class="message-bubble">
              <div class="message-text">{{ message.content }}</div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
        </transition-group>

        <!-- Typing Indicator -->
        <div v-if="loading" class="message-item assistant">
          <div class="message-avatar">
            <q-avatar size="32px" class="assistant-avatar">
              <q-icon name="auto_awesome" size="18px" />
            </q-avatar>
          </div>
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <!-- Suggestions -->
      <div v-if="suggestions.length > 0" class="suggestions-area">
        <div
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-chip"
          @click="sendQuickMessage(suggestion)"
        >
          {{ suggestion }}
        </div>
      </div>

      <!-- Chat-Leiste unten -->
      <div class="input-area">
        <div class="input-container">
          <q-input
            v-model="inputMessage"
            outlined
            dense
            placeholder="Nachricht an VERA..."
            bg-color="white"
            @keyup.enter="sendMessage"
            :disable="loading"
            class="message-input"
          >
            <template v-slot:prepend>
              <q-icon name="edit" size="20px" color="grey-6" />
            </template>
          </q-input>

          <div class="input-actions">
            <q-btn
              round
              flat
              :color="isRecording ? 'red-6' : 'grey-7'"
              :icon="isRecording ? 'mic' : 'mic_none'"
              size="md"
              @click="toggleVoiceInput"
              :disable="loading"
            >
              <q-tooltip>Spracheingabe</q-tooltip>
            </q-btn>

            <q-btn
              round
              unelevated
              color="primary"
              icon="send"
              size="md"
              :disable="!inputMessage.trim() || loading"
              @click="sendMessage"
              class="send-btn"
            />
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useOnboardingStore } from '@/stores/onboarding'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

const router = useRouter()
const chatStore = useChatStore()
const onboardingStore = useOnboardingStore()
const authStore = useAuthStore()
const { messages, loading, suggestions } = storeToRefs(chatStore)

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const isRecording = ref(false)
let recognition: any = null

// 6 Modul-Karten gemaess Boris-Spezifikation (DMS, KI-Erfassung, ERP, QM, Volltext, DATEV)
const modules = [
  {
    label: 'DMS',
    icon: 'folder_open',
    color: '#2980b9',
    description: 'Dokumente verwalten & archivieren',
    badge: null,
    action: () => router.push('/documents')
  },
  {
    label: 'KI-Erfassung',
    icon: 'document_scanner',
    color: '#8e44ad',
    description: 'ScanVERA: Dokumente scannen & erkennen',
    badge: 'OCR',
    action: () => router.push('/capture')
  },
  {
    label: 'ERP',
    icon: 'bar_chart',
    color: '#27ae60',
    description: 'Finanzen & Buchhaltung',
    badge: null,
    action: () => router.push('/finanzen')
  },
  {
    label: 'QM',
    icon: 'check_circle',
    color: '#e67e22',
    description: 'Qualitaetsmanagement & Audits',
    badge: null,
    action: () => router.push('/qm')
  },
  {
    label: 'Volltextsuche',
    icon: 'search',
    color: '#1abc9c',
    description: 'Alles in Sekunden finden',
    badge: null,
    action: () => router.push('/search')
  },
  {
    label: 'DATEV-Export',
    icon: 'download',
    color: '#7f8c8d',
    description: 'Buchungsdaten exportieren',
    badge: null,
    action: () => router.push('/finanzen/datev')
  }
]

onMounted(async () => {
  chatStore.generateSessionId()

  if (!authStore.isAuthenticated) {
    return
  }

  await onboardingStore.checkStatus()

  if (onboardingStore.isComplete) {
    try {
      await chatStore.loadSuggestions()
    } catch {
      // LLM noch nicht bereit
    }
  }

  initVoiceRecognition()
})

watch(messages, () => {
  nextTick(() => scrollToBottom())
}, { deep: true })

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTo({
      top: messagesContainer.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

async function sendMessage() {
  if (!inputMessage.value.trim()) return
  const message = inputMessage.value
  inputMessage.value = ''

  if (message.startsWith('/')) {
    handleCommand(message)
    return
  }

  try {
    await chatStore.sendMessage(message)
  } catch (error: any) {
    const isServerError = error?.response?.status >= 500
    if (isServerError && chatStore.messages.at(-1)?.role !== 'assistant') {
      chatStore.messages.push({
        role: 'assistant',
        content: 'Einen Moment - ich starte gerade. Das kann beim ersten Mal 10-30 Sekunden dauern. Bitte gleich nochmal versuchen!',
        timestamp: new Date()
      })
    }
  }
}

function handleCommand(command: string) {
  const cmd = command.toLowerCase().trim()

  if (cmd === '/login') {
    if (authStore.isAuthenticated) {
      chatStore.messages.push({ role: 'assistant', content: 'Du bist bereits angemeldet! Nutze /logout um dich abzumelden.', timestamp: new Date() })
    } else {
      chatStore.startAuthFlow()
    }
  } else if (cmd === '/logout') {
    if (!authStore.isAuthenticated) {
      chatStore.messages.push({ role: 'assistant', content: 'Du bist nicht angemeldet! Nutze /login um dich anzumelden.', timestamp: new Date() })
    } else {
      authStore.logout()
      chatStore.clearChat()
      chatStore.messages.push({ role: 'assistant', content: 'Du wurdest abgemeldet. Bis bald!\n\nNutze /login um dich wieder anzumelden.', timestamp: new Date() })
    }
  } else {
    chatStore.messages.push({ role: 'assistant', content: `Unbekannter Befehl: ${command}\n\nVerfuegbare Befehle:\n/login - Anmelden\n/logout - Abmelden`, timestamp: new Date() })
  }
}

function handleModuleClick(module: any) {
  module.action()
}

function sendQuickMessage(message: string) {
  inputMessage.value = message
  sendMessage()
}

function formatTime(date: Date): string {
  if (!date) return ''
  const d = new Date(date)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return 'Gerade eben'
  if (diff < 3600000) return `Vor ${Math.floor(diff / 60000)} Min`
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function initVoiceRecognition() {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognition) return

  recognition = new SpeechRecognition()
  recognition.lang = 'de-DE'
  recognition.continuous = false
  recognition.interimResults = false

  recognition.onresult = (event: any) => {
    const transcript = event.results[0][0].transcript
    inputMessage.value = transcript
    isRecording.value = false
  }
  recognition.onerror = () => { isRecording.value = false }
  recognition.onend = () => { isRecording.value = false }
}

function toggleVoiceInput() {
  if (!recognition) return
  if (isRecording.value) {
    recognition.stop()
    isRecording.value = false
  } else {
    recognition.start()
    isRecording.value = true
  }
}
</script>

<style scoped lang="scss">
// Boris-Branding Farben (Fact #1298)
$boris-dark:    #1a5276;   // Dunkelblau (Primaer)
$boris-blue:    #2980b9;   // Blau (Mitte)
$boris-teal:    #1abc9c;   // Tuerkis/Cyan (Akzent)
$off-white:     #f5f5f5;
$card-bg:       #FFFFFF;
$text-primary:  #1F2937;
$text-secondary:#6B7280;
$card-radius:   16px;
$card-shadow:   0 2px 8px rgba(0, 0, 0, 0.08);
$card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.14);

.chat-page {
  background: $off-white;
  min-height: calc(100dvh - 50px);
  height: calc(100dvh - 50px);
  display: flex;
  justify-content: center;
  padding: 24px 16px;
  overflow: hidden;
}

.chat-centered-container {
  width: 100%;
  max-width: 1000px;
  height: calc(100dvh - 98px);
  display: flex;
  flex-direction: column;
  background: $card-bg;
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

// Header: weisser Hintergrund, Boris-Branding-Gradient auf Titel
.chat-header {
  padding: 16px 24px;
  background: $card-bg;
  border-bottom: 2px solid rgba(26, 82, 118, 0.10);
  flex-shrink: 0;
}

.vera-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.vera-logo-wrap {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.vera-logo-img {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.vera-info { flex: 1; }

.vera-title {
  font-size: 20px;
  font-weight: 800;
  background: linear-gradient(135deg, $boris-dark 0%, $boris-blue 50%, $boris-teal 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
}

.vera-subtitle {
  font-size: 13px;
  color: $text-secondary;
  margin-top: 2px;
}

// Messages Area
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 32px 28px;
  background: $off-white;
  -webkit-overflow-scrolling: touch;
}

// Welcome State
.welcome-state {
  text-align: center;
  padding: 32px 20px 24px;
}

.welcome-logo {
  margin: 0 auto 28px;
  display: flex;
  justify-content: center;
}

.welcome-logo-img {
  width: 120px;
  height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(26, 82, 118, 0.2));
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 12px;
  letter-spacing: -0.02em;
}

.welcome-text {
  font-size: 15px;
  color: $text-secondary;
  line-height: 1.6;
  max-width: 460px;
  margin: 0 auto 40px;
}

// 2x3 Modul-Karten Grid (Boris-Spezifikation)
.module-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
}

.module-card {
  background: $card-bg;
  border-radius: $card-radius;
  padding: 20px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1.5px solid rgba(0, 0, 0, 0.07);
  box-shadow: $card-shadow;
  text-align: left;
  min-height: 120px;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $card-shadow-hover;
    border-color: $boris-blue;
  }

  &:active { transform: translateY(-2px); }
}

.module-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

// iPad-optimiert: mindestens 48px Touch-Target
.module-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.module-badge {
  background: $boris-teal;
  color: white;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  align-self: flex-start;
}

.module-title {
  font-size: 16px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 6px;
  letter-spacing: -0.01em;
}

.module-description {
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.5;
}

// Messages
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  animation: slideUp 0.3s ease;

  &.user {
    flex-direction: row-reverse;

    .message-bubble {
      background: linear-gradient(135deg, $boris-dark 0%, $boris-blue 100%);
      color: white;
      border-radius: 18px 18px 4px 18px;
      margin-left: auto;
    }

    .message-time { color: rgba(255, 255, 255, 0.85); }
  }

  &.assistant {
    .message-bubble {
      background: $card-bg;
      color: $text-primary;
      border-radius: 18px 18px 18px 4px;
      box-shadow: $card-shadow;
      border: 1px solid rgba(0, 0, 0, 0.05);
    }
  }
}

.message-avatar { flex-shrink: 0; }

.assistant-avatar {
  background: linear-gradient(135deg, $boris-dark 0%, $boris-teal 100%);
  color: white;
}

.message-bubble {
  max-width: 75%;
  padding: 14px 18px;
  word-wrap: break-word;
}

.message-text {
  line-height: 1.6;
  font-size: 15px;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.7;
}

// Typing Indicator
.typing-indicator {
  background: $card-bg;
  padding: 14px 18px;
  border-radius: 18px;
  box-shadow: $card-shadow;
  border: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 5px;

  span {
    width: 8px;
    height: 8px;
    background: $boris-teal;
    border-radius: 50%;
    animation: typing 1.4s infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-8px); opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

// Suggestions
.suggestions-area {
  padding: 14px 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: $card-bg;
  flex-shrink: 0;
}

.suggestion-chip {
  padding: 8px 16px;
  background: $off-white;
  border-radius: 20px;
  font-size: 13px;
  color: $text-primary;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid rgba(0, 0, 0, 0.08);
  font-weight: 500;

  &:hover {
    background: $boris-teal;
    color: white;
    border-color: $boris-teal;
  }
}

// Input Area
.input-area {
  padding: 16px 20px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  background: white;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.input-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.message-input {
  flex: 1;

  :deep(.q-field__control) {
    border-radius: 24px;
    height: 48px;
    border: 2px solid #E5E7EB;
    transition: all 0.2s ease;

    &:hover { border-color: #D1D5DB; }

    &:focus-within {
      border-color: $boris-teal;
      box-shadow: 0 0 0 3px rgba(26, 188, 156, 0.12);
    }
  }

  :deep(.q-field__native) {
    padding: 0 16px 0 12px;
    font-size: 14px;
  }
}

.input-actions { display: flex; gap: 8px; }

.send-btn {
  background: linear-gradient(135deg, $boris-dark 0%, $boris-teal 100%) !important;
}

// iPad-optimiert (768px-1024px)
@media (min-width: 768px) and (max-width: 1024px) {
  .module-card { min-height: 130px; padding: 22px; }
  .module-icon { width: 56px; height: 56px; }
  .module-title { font-size: 17px; }
  .chat-centered-container { max-width: 800px; height: calc(100dvh - 82px); }
  .chat-page { padding: 16px; }
}

// Mobile (<600px)
@media (max-width: 599px) {
  .chat-page { padding: 0; }
  .chat-centered-container { height: calc(100dvh - 50px); border-radius: 0; max-width: 100%; }
  .module-cards { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .module-card { min-height: 100px; padding: 16px; }
  .welcome-title { font-size: 22px; }
  .messages-area { padding: 16px; }
  .chat-header { padding: 12px 16px; }
}

// Desktop (1024px+)
@media (min-width: 1024px) {
  .chat-centered-container { max-width: 900px; }
}
</style>
