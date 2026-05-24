<template>
  <q-page class="chat-page">
    <!-- Centered Container -->
    <div class="chat-centered-container">
      
      <!-- Header with VERA branding -->
      <div class="chat-header">
        <div class="vera-brand">
          <div class="vera-logo">
            <img src="/vera-logo.svg" alt="VERA" style="width: 48px; height: 48px; object-fit: contain;" />
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
            <img src="/vera-icon.svg?v=3" alt="VERA Office" style="width: 120px; height: 120px; object-fit: contain;" />
          </div>
          <div class="welcome-title">Hey! Ich bin VERA 👋</div>
          <div class="welcome-text">
            Deine intelligente Assistentin für Praxis-Management.
            Wähle ein Modul oder stelle mir eine Frage.
          </div>

          <!-- Module Cards Grid -->
          <div class="module-cards">
            <div 
              v-for="module in modules" 
              :key="module.label"
              class="module-card"
              @click="handleModuleClick(module)"
            >
              <div class="module-header">
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

      <!-- Input Area -->
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

// Module Cards (VERA Office Features)
const modules = [
  { 
    label: 'Chat mit VERA', 
    icon: 'forum', 
    color: '#0EA5A0',
    description: 'Stelle Fragen und lass dir helfen',
    badge: null,
    action: () => {
      // Bereits auf Chat-Seite, fokussiere Input
      const input = document.querySelector('.message-input input') as HTMLInputElement
      input?.focus()
    }
  },
  { 
    label: 'Dokumente', 
    icon: 'folder_open', 
    color: '#085E6A',
    description: 'Verwalte alle Praxis-Dokumente',
    badge: null,
    action: () => router.push('/documents')
  },
  { 
    label: 'KI-Erfassung', 
    icon: 'document_scanner', 
    color: '#0EA5A0',
    description: 'Scanne & erkenne Dokumente',
    badge: 'OCR',
    action: () => router.push('/capture')
  },
  { 
    label: 'Volltext-Suche', 
    icon: 'search', 
    color: '#2E3B8E',
    description: 'Finde alles in Sekunden',
    badge: null,
    action: () => router.push('/search')
  },
  { 
    label: 'Einstellungen', 
    icon: 'settings', 
    color: '#085E6A',
    description: 'Passe VERA an deine Praxis an',
    badge: null,
    action: () => router.push('/settings')
  },
  { 
    label: 'Zuletzt bearbeitet', 
    icon: 'history', 
    color: '#0EA5A0',
    description: 'Schnellzugriff auf Letzte',
    badge: null,
    action: () => router.push('/recent')
  }
]

onMounted(async () => {
  chatStore.generateSessionId()

  // Router-Guard leitet unauthentifizierte Nutzer zu /login um –
  // kein startAuthFlow() hier nötig (würde /api/auth/chat aufrufen, existiert nicht).
  if (!authStore.isAuthenticated) {
    return
  }

  await onboardingStore.checkStatus()

  // Vorschläge laden (Fehler stumm schlucken – keine Fehlermeldung beim Start)
  if (onboardingStore.isComplete) {
    try {
      await chatStore.loadSuggestions()
    } catch {
      // LLM noch nicht bereit – kein Problem, Nutzer sieht Welcome-Screen
    }
  }
  // Onboarding nicht abgeschlossen: statischer Welcome-Screen genügt.
  // Kein sendMessage('') – das würde ein Leerzeichen schicken und ggf. LLM blockieren.

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
    // Zeige freundliche Nachricht statt roter Fehler-Notification
    const isServerError = error?.response?.status >= 500
    if (isServerError && chatStore.messages.at(-1)?.role !== 'assistant') {
      chatStore.messages.push({
        role: 'assistant',
        content: 'Einen Moment – ich starte gerade. Das kann beim ersten Mal 10–30 Sekunden dauern. Bitte gleich nochmal versuchen! ⏳',
        timestamp: new Date()
      })
    }
  }
}

function handleCommand(command: string) {
  const cmd = command.toLowerCase().trim()
  
  if (cmd === '/login') {
    if (authStore.isAuthenticated) {
      chatStore.messages.push({
        role: 'assistant',
        content: 'Du bist bereits angemeldet! Nutze /logout um dich abzumelden.',
        timestamp: new Date()
      })
    } else {
      chatStore.startAuthFlow()
    }
  }
  else if (cmd === '/logout') {
    if (!authStore.isAuthenticated) {
      chatStore.messages.push({
        role: 'assistant',
        content: 'Du bist nicht angemeldet! Nutze /login um dich anzumelden.',
        timestamp: new Date()
      })
    } else {
      authStore.logout()
      chatStore.clearChat()
      chatStore.messages.push({
        role: 'assistant',
        content: 'Du wurdest abgemeldet. Bis bald! 👋\n\nNutze /login um dich wieder anzumelden.',
        timestamp: new Date()
      })
    }
  }
  else {
    chatStore.messages.push({
      role: 'assistant',
      content: `Unbekannter Befehl: ${command}\n\nVerfügbare Befehle:\n/login - Anmelden\n/logout - Abmelden`,
      timestamp: new Date()
    })
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
// Design Tokens - Mockup Stil
$teal-primary: #0EA5A0;
$teal-dark: #085E6A;
$navy: #2E3B8E;
$off-white: #F4F6F8;
$card-bg: #FFFFFF;
$text-primary: #1F2937;
$text-secondary: #6B7280;
$card-radius: 16px;
$card-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
$card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.12);

.chat-page {
  background: $off-white;
  min-height: calc(100dvh - 50px);
  display: flex;
  justify-content: center;
  padding: 24px 16px;
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

// Header - Dark Teal
.chat-header {
  padding: 20px 28px;
  background: $teal-dark;
  border-bottom: none;
}

.vera-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.vera-logo {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.vera-info {
  flex: 1;
}

.vera-title {
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: -0.02em;
}

.vera-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 4px;
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
  padding: 40px 20px 32px;
}

.welcome-logo {
  margin: 0 auto 32px;
  display: flex;
  justify-content: center;
  
  img {
    filter: drop-shadow(0 4px 12px rgba(14, 165, 160, 0.2));
  }
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 16px;
  letter-spacing: -0.03em;
}

.welcome-text {
  font-size: 16px;
  color: $text-secondary;
  line-height: 1.6;
  max-width: 480px;
  margin: 0 auto 48px;
  font-weight: 400;
}

// Module Cards - 3×2 Grid (Mockup Stil)
.module-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.module-card {
  background: $card-bg;
  border-radius: $card-radius;
  padding: 24px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: $card-shadow;
  position: relative;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: $card-shadow-hover;
    border-color: $teal-primary;
  }
  
  &:active {
    transform: translateY(-2px);
  }
}

.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.module-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(14, 165, 160, 0.2);
}

.module-badge {
  background: $teal-primary;
  color: white;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.module-title {
  font-size: 17px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 8px;
  letter-spacing: -0.01em;
}

.module-description {
  font-size: 14px;
  color: $text-secondary;
  line-height: 1.5;
  font-weight: 400;
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
      background: $teal-primary;
      color: white;
      border-radius: 18px 18px 4px 18px;
      margin-left: auto;
    }
    
    .message-time {
      color: rgba(255, 255, 255, 0.85);
    }
  }
  
  &.assistant {
    .message-bubble {
      background: $card-bg;
      color: $text-primary;
      border-radius: 18px 18px 18px 4px;
      box-shadow: $card-shadow;
      border: 1px solid rgba(0, 0, 0, 0.04);
    }
  }
}

.message-avatar {
  flex-shrink: 0;
}

.assistant-avatar {
  background: linear-gradient(135deg, $teal-primary 0%, $teal-dark 100%);
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
  font-weight: 400;
}

.message-time {
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.7;
  font-weight: 500;
}

// Typing Indicator
.typing-indicator {
  background: $card-bg;
  padding: 14px 18px;
  border-radius: 18px;
  box-shadow: $card-shadow;
  border: 1px solid rgba(0, 0, 0, 0.04);
  display: flex;
  gap: 5px;
  
  span {
    width: 8px;
    height: 8px;
    background: $teal-primary;
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
  padding: 16px 28px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: $card-bg;
}

.suggestion-chip {
  padding: 10px 18px;
  background: $off-white;
  border-radius: 24px;
  font-size: 14px;
  color: $text-primary;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid rgba(0, 0, 0, 0.08);
  font-weight: 500;
  
  &:hover {
    background: $teal-primary;
    color: white;
    border-color: $teal-primary;
  }
  
  &:active {
    transform: scale(0.96);
  }
}

// Input Area
.input-area {
  padding: 20px 24px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom, 0px));
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
    
    &:hover {
      border-color: #D1D5DB;
    }
    
    &:focus-within {
      border-color: #0EA5A0;
      box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
    }
  }
  
  :deep(.q-field__native) {
    padding: 0 16px 0 12px;
    font-size: 14px;
  }
}

.input-actions {
  display: flex;
  gap: 8px;
}

.send-btn {
  background: linear-gradient(135deg, #0EA5A0 0%, #0D7380 100%);
  
  &:hover:not(:disabled) {
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
  }
}

// Responsive Design
// Mobile Portrait (< 600px)
@media (max-width: 599px) {
  .chat-page {
    padding: 0;
  }

  .chat-centered-container {
    // 50px App-Header, no padding on mobile
    height: calc(100dvh - 50px);
    border-radius: 0;
    max-width: 100%;
  }
  
  .chat-header {
    padding: 16px 16px;
  }
  
  .vera-logo {
    width: 40px;
    height: 40px;
  }
  
  .vera-title {
    font-size: 18px;
  }
  
  .messages-area {
    padding: 16px;
  }
  
  .welcome-state {
    padding: 40px 16px 32px;
  }
  
  .welcome-icon {
    width: 80px;
    height: 80px;
  }
  
  .welcome-title {
    font-size: 24px;
  }
  
  .action-bubbles {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .action-bubble {
    padding: 16px 12px;
  }
  
  .message-bubble {
    max-width: 85%;
  }
  
  .input-area {
    padding: 16px;
    padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  }
  
  .message-input :deep(.q-field__control) {
    height: 44px;
  }
}

// Mobile Landscape (600px - 767px)
@media (min-width: 600px) and (max-width: 767px) {
  .chat-page {
    padding: 8px;
  }

  .chat-centered-container {
    // 50px App-Header + 16px padding (8px * 2)
    height: calc(100dvh - 66px);
    border-radius: 16px;
  }
  
  .action-bubbles {
    grid-template-columns: repeat(4, 1fr);
  }
}

// Tablet Portrait (768px - 1023px)
@media (min-width: 768px) and (max-width: 1023px) {
  .chat-page {
    padding: 16px;
  }

  .chat-centered-container {
    // 50px App-Header + 32px padding (16px * 2)
    height: calc(100dvh - 82px);
    max-width: 700px;
  }
  
  .action-bubbles {
    grid-template-columns: repeat(4, 1fr);
  }
}

// Tablet Landscape / Desktop (1024px+)
@media (min-width: 1024px) {
  .chat-centered-container {
    max-width: 800px;
  }
  
  .action-bubbles {
    grid-template-columns: repeat(4, 1fr);
  }
}

// Large Desktop (1440px+)
@media (min-width: 1440px) {
  .chat-centered-container {
    max-width: 900px;
  }
}

// Handle orientation changes
@media (orientation: landscape) and (max-height: 600px) {
  .welcome-state {
    padding: 20px 16px;
  }
  
  .welcome-icon {
    width: 64px;
    height: 64px;
  }
  
  .welcome-title {
    font-size: 22px;
    margin-bottom: 8px;
  }
  
  .welcome-text {
    font-size: 14px;
    margin-bottom: 24px;
  }
  
  .action-bubbles {
    gap: 12px;
  }
  
  .action-bubble {
    padding: 12px;
  }
}

// Ensure chat fills available viewport — always subtract App header (50px)
// dvh = dynamic viewport height, solves Safari URL-bar issue
.chat-page {
  min-height: calc(100dvh - 50px);
  height: calc(100dvh - 50px);
  overflow: hidden;
}
</style>
