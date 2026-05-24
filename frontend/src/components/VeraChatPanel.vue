<template>
  <div class="vera-chat-panel">
    
    <!-- Header -->
    <div class="chat-header">
      <q-avatar size="40px" color="primary" text-color="white" icon="auto_awesome" />
      <div class="q-ml-sm">
        <div class="text-h6 text-weight-bold">VERA</div>
        <div class="text-caption text-grey-6">Intelligent Assistant</div>
      </div>
      <q-space />
      
      <!-- Toggle Button (Mobile) -->
      <q-btn 
        v-if="$q.screen.lt.md"
        flat 
        round
        dense
        icon="close" 
        @click="$emit('close')"
      />
    </div>

    <!-- Chat Messages -->
    <q-scroll-area 
      ref="scrollArea"
      class="chat-messages"
      :thumb-style="thumbStyle"
    >
      <div 
        v-for="msg in messages" 
        :key="msg.id"
        class="q-mb-md"
      >
        <q-chat-message
          :name="msg.role === 'assistant' ? 'VERA' : 'Du'"
          :text="[msg.content]"
          :sent="msg.role === 'user'"
          :bg-color="msg.role === 'user' ? 'primary' : 'grey-3'"
          :text-color="msg.role === 'user' ? 'white' : 'dark'"
          :stamp="formatTime(msg.timestamp)"
        >
          <template v-slot:avatar v-if="msg.role === 'assistant'">
            <q-avatar color="primary" text-color="white" icon="auto_awesome" />
          </template>
        </q-chat-message>
      </div>
      
      <!-- Typing Indicator -->
      <div v-if="isTyping" class="typing-indicator q-pa-md">
        <q-spinner-dots color="primary" size="30px" />
        <span class="q-ml-sm text-grey-6">VERA tippt...</span>
      </div>

      <!-- Empty State -->
      <div v-if="messages.length === 0" class="empty-state">
        <q-icon name="chat" size="64px" color="grey-4" />
        <div class="text-h6 text-grey-6 q-mt-md">Starte ein Gespräch mit VERA</div>
        <div class="text-caption text-grey-5 q-mt-sm">
          Frage mich zu Dokumenten, Aufgaben oder Workflows
        </div>
      </div>
    </q-scroll-area>

    <!-- Input -->
    <div class="chat-input">
      <q-input
        v-model="input"
        placeholder="Frage VERA..."
        dense
        outlined
        autogrow
        :max-height="100"
        @keyup.enter.exact="send"
        @keydown.enter.shift.prevent
        class="chat-input-field"
      >
        <template v-slot:prepend>
          <q-icon name="chat_bubble_outline" color="grey-6" />
        </template>
        <template v-slot:append>
          <q-btn 
            flat 
            round 
            dense
            icon="send" 
            color="primary"
            @click="send"
            :disable="!input.trim() || isTyping"
          />
        </template>
        <template v-slot:hint>
          <span class="text-caption">Enter zum Senden, Shift+Enter für neue Zeile</span>
        </template>
      </q-input>

      <!-- Quick Actions -->
      <div class="quick-actions q-mt-sm">
        <q-btn 
          v-for="action in quickActions"
          :key="action.label"
          size="xs"
          flat
          dense
          :label="action.label"
          :icon="action.icon"
          color="grey-7"
          class="q-mr-xs"
          @click="sendQuickAction(action.text)"
        />
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const messages = ref<Message[]>([])
const input = ref('')
const isTyping = ref(false)
const scrollArea = ref<any>(null)

const thumbStyle = {
  right: '2px',
  borderRadius: '5px',
  backgroundColor: '#85dfde',
  width: '5px',
  opacity: 0.5
}

const quickActions = [
  { label: 'Dokumente', icon: 'folder', text: 'Zeige mir die neuesten Dokumente' },
  { label: 'Aufgaben', icon: 'task_alt', text: 'Was sind meine offenen Aufgaben?' },
  { label: 'Suche', icon: 'search', text: 'Suche nach ' }
]

function formatTime(date: Date): string {
  return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

async function scrollToBottom() {
  await nextTick()
  if (scrollArea.value) {
    const scrollTarget = scrollArea.value.getScrollTarget()
    const duration = 300
    scrollArea.value.setScrollPosition('vertical', scrollTarget.scrollHeight, duration)
  }
}

async function send() {
  if (!input.value.trim() || isTyping.value) return
  
  // Add user message
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: input.value.trim(),
    timestamp: new Date()
  })
  
  const userInput = input.value.trim()
  input.value = ''
  
  await scrollToBottom()
  
  // Show typing
  isTyping.value = true
  
  try {
    // API Call to VERA
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: userInput,
        session_id: 'vera-chat-panel'
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    // Add VERA response
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: data.response || data.message || 'Keine Antwort erhalten.',
      timestamp: new Date()
    })
    
  } catch (e) {
    console.error('VERA Chat Error:', e)
    
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: 'Entschuldigung, ein Fehler ist aufgetreten. Bitte versuche es erneut.',
      timestamp: new Date()
    })
    
    $q.notify({
      type: 'negative',
      message: 'VERA konnte nicht erreicht werden',
      caption: String(e),
      position: 'top'
    })
  } finally {
    isTyping.value = false
    await scrollToBottom()
  }
}

function sendQuickAction(text: string) {
  input.value = text
  if (!text.endsWith(' ')) {
    // If action is complete (like "Show documents"), send immediately
    send()
  }
  // Otherwise leave it in input for user to complete
}

// Load welcome message on mount
onMounted(async () => {
  messages.value.push({
    id: 1,
    role: 'assistant',
    content: 'Hallo! Ich bin VERA, dein intelligenter Office-Assistent. Wie kann ich dir heute helfen?',
    timestamp: new Date()
  })
  await scrollToBottom()
})

// Emit close event for mobile
defineEmits<{
  (e: 'close'): void
}>()
</script>

<style scoped>
.vera-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #FAFAFA;
}

body.body--dark .vera-chat-panel {
  background: #1A1A1A;
}

.chat-header {
  padding: 16px;
  border-bottom: 1px solid #E0E0E0;
  display: flex;
  align-items: center;
  background: white;
}

body.body--dark .chat-header {
  background: #2D2D2D;
  border-bottom-color: #3D3D3D;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 32px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  padding-left: 16px;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #E0E0E0;
  background: white;
}

body.body--dark .chat-input {
  background: #2D2D2D;
  border-top-color: #3D3D3D;
}

.chat-input-field {
  background: white;
}

body.body--dark .chat-input-field {
  background: #1A1A1A;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* Responsive: Mobile Full-Screen */
@media (max-width: 1023px) {
  .vera-chat-panel {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 3000;
  }
}
</style>
