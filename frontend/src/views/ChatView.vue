<template>
  <q-page class="chat-view">
    <div class="chat-container">
      <!-- Header -->
      <div class="chat-header q-pa-md bg-primary text-white">
        <div class="row items-center">
          <q-avatar size="48px" class="q-mr-md">
            <q-icon name="support_agent" size="32px" />
          </q-avatar>
          <div>
            <div class="text-h6">VERA</div>
            <div class="text-caption">Deine Dokumenten-Assistentin</div>
          </div>
        </div>
      </div>

      <!-- Messages Area -->
      <div ref="messagesContainer" class="messages-container q-pa-md">
        <!-- Welcome Message -->
        <div v-if="messages.length === 0 && !loading" class="text-center q-pa-xl welcome-fade">
          <q-icon name="support_agent" size="80px" color="primary" />
          <div class="text-h6 q-mt-md">Hey! Ich bin VERA 👋</div>
          <div class="text-body2 text-grey-7 q-mt-sm">
            Deine freundliche Dokumenten-Assistentin. Wie kann ich dir helfen?
          </div>
        </div>

        <!-- Proactive Suggestions (shown at start) -->
        <div v-if="messages.length === 0 && !loading && proactiveSuggestions.length > 0" class="q-mt-md">
          <div class="text-caption text-grey-6 q-mb-sm q-px-sm">💡 Vorschläge für dich:</div>
          <div
            v-for="(sug, i) in proactiveSuggestions"
            :key="i"
            class="proactive-card q-mb-sm q-pa-md cursor-pointer"
            @click="sendQuickMessage(sug.action || sug.title)"
          >
            <div class="row items-center no-wrap">
              <q-icon
                :name="sug.priority === 'high' ? 'warning' : sug.priority === 'medium' ? 'info' : 'lightbulb'"
                :color="sug.priority === 'high' ? 'red' : sug.priority === 'medium' ? 'orange' : 'primary'"
                size="24px"
                class="q-mr-sm"
              />
              <div class="col">
                <div class="text-body2 text-weight-medium">{{ sug.title }}</div>
                <div v-if="sug.description" class="text-caption text-grey-6">{{ sug.description }}</div>
              </div>
              <q-icon name="chevron_right" color="grey-5" />
            </div>
          </div>
        </div>

        <!-- Chat Messages -->
        <transition-group name="message-anim" tag="div">
          <div
            v-for="(message, index) in messages"
            :key="'msg-' + index"
            :class="['message-wrapper', message.role === 'user' ? 'user-message' : 'assistant-message']"
          >
            <div class="message-bubble">
              <div v-if="message.role === 'assistant'" class="message-avatar q-mr-sm">
                <q-avatar size="36px" color="primary" text-color="white">
                  <q-icon name="support_agent" />
                </q-avatar>
              </div>
              <div class="message-content">
                <div class="message-text">{{ message.content }}</div>
                <div class="message-time text-caption text-grey-6">
                  {{ formatTime(message.timestamp) }}
                </div>
              </div>
            </div>
          </div>
        </transition-group>

        <!-- Typing Indicator -->
        <div v-if="loading" class="message-wrapper assistant-message">
          <div class="message-bubble">
            <div class="message-avatar q-mr-sm">
              <q-avatar size="36px" color="primary" text-color="white">
                <q-icon name="support_agent" />
              </q-avatar>
            </div>
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Suggestions -->
      <div v-if="suggestions.length > 0" class="quick-actions q-px-md q-py-sm">
        <q-chip
          v-for="(suggestion, index) in suggestions"
          :key="index"
          clickable
          outline
          color="primary"
          size="md"
          class="suggestion-chip"
          @click="sendQuickMessage(suggestion)"
        >
          {{ suggestion }}
        </q-chip>
      </div>

      <!-- Input Area -->
      <div class="input-area q-pa-md">
        <div class="row items-center q-col-gutter-sm">
          <div class="col">
            <q-input
              v-model="inputMessage"
              outlined
              rounded
              dense
              placeholder="Schreib mir was..."
              bg-color="white"
              @keyup.enter="sendMessage"
              :disable="loading"
              class="chat-input"
            />
          </div>
          <div class="col-auto">
            <q-btn
              round
              flat
              :color="isRecording ? 'red' : 'grey-7'"
              :icon="isRecording ? 'mic' : 'mic_none'"
              size="lg"
              class="touch-btn"
              @click="toggleVoiceInput"
              :disable="loading"
            >
              <q-tooltip>Spracheingabe</q-tooltip>
            </q-btn>
          </div>
          <div class="col-auto">
            <q-btn
              round
              color="primary"
              icon="send"
              size="lg"
              class="touch-btn"
              :disable="!inputMessage.trim() || loading"
              @click="sendMessage"
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
import { storeToRefs } from 'pinia'

const chatStore = useChatStore()
const onboardingStore = useOnboardingStore()
const authStore = useAuthStore()
const { messages, loading, suggestions, proactiveSuggestions, authMode } = storeToRefs(chatStore)

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const isRecording = ref(false)
let recognition: any = null

onMounted(async () => {
  chatStore.generateSessionId()
  
  // Check authentication status first
  if (!authStore.isAuthenticated) {
    // User not authenticated → Start conversational auth flow
    chatStore.startAuthFlow()
    return
  }
  
  // User is authenticated → Proceed with normal onboarding/chat flow
  await onboardingStore.checkStatus()

  if (!onboardingStore.isComplete) {
    // Trigger onboarding greeting
    await chatStore.sendMessage('')
  } else {
    // Load proactive suggestions
    await chatStore.loadSuggestions()
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
  
  // Handle chat commands
  if (message.startsWith('/')) {
    handleCommand(message)
    return
  }
  
  try {
    await chatStore.sendMessage(message)
  } catch (error) {
    console.error('Send message error:', error)
  }
}

function handleCommand(command: string) {
  /**
   * Handle special chat commands:
   * /login - Start auth flow
   * /logout - Logout user
   */
  const cmd = command.toLowerCase().trim()
  
  if (cmd === '/login') {
    // Start auth flow
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
    // Logout user
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
.chat-view {
  height: calc(100vh - 50px);
  display: flex;
  flex-direction: column;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-header {
  flex-shrink: 0;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  background: #f5f5f5;
  -webkit-overflow-scrolling: touch;
}

.welcome-fade {
  animation: fadeIn 0.5s ease-out;
}

.proactive-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: transform 0.15s;
  min-height: 48px;
  &:active { transform: scale(0.98); }
}

// Message animations
.message-anim-enter-active {
  animation: slideUp 0.3s ease-out;
}
.message-anim-leave-active {
  animation: slideUp 0.3s ease-out reverse;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.message-wrapper {
  margin-bottom: 12px;
  display: flex;

  &.user-message {
    justify-content: flex-end;
    .message-content {
      background: #1976d2;
      color: white;
      border-radius: 18px 18px 4px 18px;
      padding: 12px 16px;
    }
    .message-time { color: rgba(255,255,255,0.7); }
  }

  &.assistant-message {
    justify-content: flex-start;
    .message-bubble {
      display: flex;
      align-items: flex-start;
    }
    .message-content {
      background: white;
      border-radius: 18px 18px 18px 4px;
      padding: 12px 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
  }
}

.message-content {
  max-width: 75%;
}

.message-text {
  word-wrap: break-word;
  white-space: pre-wrap;
  line-height: 1.5;
}

.message-time {
  margin-top: 4px;
  font-size: 11px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);

  span {
    height: 8px;
    width: 8px;
    background: #90a4ae;
    border-radius: 50%;
    display: inline-block;
    margin-right: 4px;
    animation: typing 1.4s infinite;
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; margin-right: 0; }
  }
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
  30% { transform: translateY(-10px); opacity: 1; }
}

.quick-actions {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  background: #fafafa;
  border-top: 1px solid rgba(0,0,0,0.08);
}

.suggestion-chip {
  min-height: 44px; // iPad touch target
}

.input-area {
  flex-shrink: 0;
  background: white;
  border-top: 1px solid rgba(0,0,0,0.12);
}

.chat-input {
  :deep(.q-field__control) {
    min-height: 44px;
  }
}

// iPad touch targets >= 44px
.touch-btn {
  min-width: 48px;
  min-height: 48px;
}
</style>
