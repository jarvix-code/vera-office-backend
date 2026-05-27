<template>
  <q-page class="chat-page">
    <div class="chat-container">

      <!-- Welcome State: Logo + 6 Module Cards -->
      <div v-if="messages.length === 0 && !loading" class="welcome-state">
        <!-- VERA Branding -->
        <div class="welcome-brand">
          <div class="welcome-avatar">
            <img src="/vera-icon.svg?v=3" alt="VERA" />
          </div>
          <h1 class="welcome-title">Hey! Ich bin VERA</h1>
          <p class="welcome-subtitle">Deine intelligente Assistentin fuer Praxis-Management.<br />Waehle ein Modul oder stelle mir eine Frage.</p>
        </div>

        <!-- 6 Module Cards — 21st.dev clean card style -->
        <div class="module-grid">
          <button
            v-for="mod in modules"
            :key="mod.id"
            class="module-card"
            :class="{ 'module-card--locked': mod.locked }"
            @click="handleModuleClick(mod)"
          >
            <div class="module-card-icon" :style="{ background: mod.color + '18', color: mod.color }">
              <q-icon :name="mod.icon" size="22px" />
            </div>
            <div class="module-card-body">
              <div class="module-card-title">{{ mod.label }}</div>
              <div class="module-card-desc">{{ mod.description }}</div>
            </div>
            <div v-if="mod.locked" class="module-card-lock">
              <q-icon name="lock" size="14px" />
            </div>
            <div v-else-if="mod.badge" class="module-card-badge" :style="{ background: mod.color }">
              {{ mod.badge }}
            </div>
          </button>
        </div>

        <!-- Quick suggestions -->
        <div class="quick-suggestions">
          <button
            v-for="(s, i) in suggestions"
            :key="i"
            class="suggestion-chip"
            @click="sendMessage(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Chat Messages -->
      <div ref="messagesEl" class="messages-area" v-show="messages.length > 0 || loading">
        <transition-group name="msg" tag="div" class="messages-list">
          <div
            v-for="(msg, idx) in messages"
            :key="'m' + idx"
            :class="['msg-row', msg.role]"
          >
            <div v-if="msg.role === 'assistant'" class="msg-avatar">
              <img src="/vera-icon.svg?v=3" alt="VERA" />
            </div>
            <div class="msg-bubble">
              <p class="msg-text">{{ msg.content }}</p>
              <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
          </div>
        </transition-group>

        <!-- Typing indicator -->
        <div v-if="loading" class="msg-row assistant">
          <div class="msg-avatar">
            <img src="/vera-icon.svg?v=3" alt="VERA" />
          </div>
          <div class="typing-bubble">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-row">
          <!-- Camera / upload button -->
          <button class="input-action-btn" @click="handleCapture" title="Dokument scannen">
            <q-icon name="camera_alt" size="20px" />
          </button>

          <!-- Text input -->
          <div class="input-field-wrap">
            <textarea
              ref="inputEl"
              v-model="inputText"
              class="input-field"
              placeholder="Nachricht an VERA..."
              rows="1"
              @keydown.enter.exact.prevent="onEnter"
              @input="autoResize"
            ></textarea>
          </div>

          <!-- Send button -->
          <button
            class="send-btn"
            :class="{ 'send-btn--active': inputText.trim().length > 0 }"
            :disabled="!inputText.trim() || loading"
            @click="onSend"
          >
            <q-icon name="send" size="18px" />
          </button>
        </div>
        <div class="input-hint">Enter zum Senden &middot; Shift+Enter fuer neue Zeile</div>
      </div>

    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useModuleAuthStore } from '@/stores/moduleAuth'
import axios from 'axios'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const router = useRouter()
const moduleAuth = useModuleAuthStore()
const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const inputText = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])

// ── Module definitions ──────────────────────────────────────
const modules = computed(() => [
  {
    id: 'dms',
    label: 'Dokumentenverwaltung',
    description: 'Dokumente verwalten, ablegen und suchen',
    icon: 'folder_open',
    color: '#0EA5A0',
    route: '/documents',
    locked: false,
    badge: null,
  },
  {
    id: 'capture',
    label: 'KI-Erfassung',
    description: 'Dokumente scannen und automatisch erkennen',
    icon: 'document_scanner',
    color: '#6366F1',
    route: '/capture',
    locked: false,
    badge: 'KI',
  },
  {
    id: 'erp',
    label: 'ERP / Finanzen',
    description: 'BWA, Umsatzsteuer und DATEV-Export',
    icon: 'account_balance',
    color: '#F59E0B',
    route: '/finanzen',
    locked: !moduleAuth.isAdminUser() && !moduleAuth.sessionModules.includes('erp'),
    badge: null,
  },
  {
    id: 'qm',
    label: 'Qualitaetsmanagement',
    description: 'Handbuch, Audits, Hygiene und Compliance',
    icon: 'checklist',
    color: '#10B981',
    route: '/qm',
    locked: !moduleAuth.isAdminUser() && !moduleAuth.sessionModules.includes('qm'),
    badge: null,
  },
  {
    id: 'search',
    label: 'Volltextsuche',
    description: 'KI-gestuetzte Suche ueber alle Dokumente',
    icon: 'manage_search',
    color: '#8B5CF6',
    route: '/search',
    locked: false,
    badge: null,
  },
  {
    id: 'datev',
    label: 'DATEV-Export',
    description: 'Steuerberaterdaten exportieren',
    icon: 'file_download',
    color: '#EF4444',
    route: '/finanzen/datev',
    locked: !moduleAuth.isAdminUser() && !moduleAuth.sessionModules.includes('erp'),
    badge: null,
  },
])

const suggestions = [
  'Zeig mir neue Dokumente',
  'Was ist heute faellig?',
  'Hygiene-Protokoll erstellen',
  'DATEV exportieren',
]

// ── Event handlers ──────────────────────────────────────────
function handleModuleClick(mod: typeof modules.value[0]) {
  if (mod.locked) {
    moduleAuth.requireAccess(mod.id, mod.route)
    return
  }
  router.push(mod.route)
}

function handleCapture() {
  router.push('/capture')
}

function onEnter() {
  if (inputText.value.trim()) onSend()
}

async function onSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  await sendMessage(text)
}

async function sendMessage(text: string) {
  inputText.value = ''
  autoResize()

  messages.value.push({ role: 'user', content: text, timestamp: new Date() })
  await scrollToBottom()

  loading.value = true
  try {
    const res = await axios.post('/api/chat', {
      message: text,
      history: messages.value.slice(-10).map(m => ({ role: m.role, content: m.content }))
    })
    const reply = res.data?.response || res.data?.message || 'Ich habe Ihre Frage erhalten.'
    messages.value.push({ role: 'assistant', content: reply, timestamp: new Date() })
  } catch {
    messages.value.push({
      role: 'assistant',
      content: 'Entschuldigung, ich bin gerade nicht erreichbar. Bitte versuche es erneut.',
      timestamp: new Date()
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function autoResize() {
  if (!inputEl.value) return
  inputEl.value.style.height = 'auto'
  inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 160) + 'px'
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  inputEl.value?.focus()
})
</script>

<style lang="scss" scoped>
// ============================================================
// ChatView — 21st.dev Chat-First Design
// White background, teal accent, 6 module cards, iPad-first
// ============================================================

.chat-page {
  background: #F8FAFC;
  min-height: calc(100dvh - 56px);
  height: calc(100dvh - 56px);
  overflow: hidden;
  display: flex;
  align-items: stretch;
}

.chat-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  height: 100%;
  background: #FFFFFF;
  border-left: 1px solid #F1F5F9;
  border-right: 1px solid #F1F5F9;
}

// ── Welcome state ────────────────────────────────────────────
.welcome-state {
  flex: 1;
  overflow-y: auto;
  padding: 40px 24px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.welcome-brand {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.welcome-avatar {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: #F0FDFA;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid #CCFBF1;

  img {
    width: 56px;
    height: 56px;
    object-fit: contain;
  }
}

.welcome-title {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.02em;
  margin: 0;
}

.welcome-subtitle {
  font-size: 15px;
  color: #6B7280;
  line-height: 1.5;
  margin: 0;
  text-align: center;
}

// ── Module grid (3x2) ────────────────────────────────────────
.module-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 680px;
}

.module-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;

  &:hover {
    border-color: #D1D5DB;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    transform: translateY(-1px);
  }

  &:active { transform: translateY(0); }

  &.module-card--locked {
    opacity: 0.6;
    &:hover { border-color: #E5E7EB; box-shadow: none; transform: none; }
  }
}

.module-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.module-card-body { flex: 1; min-width: 0; }

.module-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  line-height: 1.2;
  margin-bottom: 3px;
}

.module-card-desc {
  font-size: 11px;
  color: #9CA3AF;
  line-height: 1.3;
}

.module-card-lock {
  position: absolute;
  top: 8px;
  right: 8px;
  color: #D1D5DB;
}

.module-card-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  color: #FFFFFF;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 100px;
  letter-spacing: 0.04em;
}

// ── Quick suggestions ────────────────────────────────────────
.quick-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.suggestion-chip {
  padding: 8px 16px;
  background: #F8FAFC;
  border: 1px solid #E5E7EB;
  border-radius: 100px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: #F0FDFA;
    border-color: #99F6E4;
    color: #0D7380;
  }
}

// ── Messages ─────────────────────────────────────────────────
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  scroll-behavior: smooth;
}

.messages-list { display: flex; flex-direction: column; gap: 12px; }

.msg-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;

  &.user {
    flex-direction: row-reverse;
    .msg-bubble {
      background: linear-gradient(135deg, #0EA5A0, #0D7380);
      color: #FFFFFF;
      border-radius: 18px 18px 4px 18px;
      .msg-time { color: rgba(255,255,255,0.7); }
    }
  }
  &.assistant {
    .msg-bubble {
      background: #F8FAFC;
      border: 1px solid #F1F5F9;
      border-radius: 18px 18px 18px 4px;
      color: #111827;
    }
  }
}

.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: #F0FDFA;
  border: 1px solid #CCFBF1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;

  img { width: 22px; height: 22px; object-fit: contain; }
}

.msg-bubble {
  max-width: 72%;
  padding: 10px 14px;
  .msg-text { font-size: 14px; line-height: 1.5; margin: 0 0 4px; white-space: pre-wrap; }
  .msg-time { font-size: 11px; color: #9CA3AF; }
}

// Typing indicator
.typing-bubble {
  padding: 12px 16px;
  background: #F8FAFC;
  border: 1px solid #F1F5F9;
  border-radius: 18px 18px 18px 4px;
  display: flex;
  gap: 4px;
  align-items: center;

  span {
    width: 7px;
    height: 7px;
    background: #9CA3AF;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out;
    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

// Message enter transition
.msg-enter-active { transition: all 0.25s ease; }
.msg-enter-from { opacity: 0; transform: translateY(8px); }

// ── Input area ───────────────────────────────────────────────
.input-area {
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #F1F5F9;
  background: #FFFFFF;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #F8FAFC;
  border: 1.5px solid #E5E7EB;
  border-radius: 16px;
  padding: 8px 8px 8px 12px;
  transition: border-color 0.15s ease;

  &:focus-within {
    border-color: #0EA5A0;
    box-shadow: 0 0 0 3px rgba(14,165,160,0.08);
    background: #FFFFFF;
  }
}

.input-action-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #9CA3AF;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;

  &:hover { background: #F0FDFA; color: #0EA5A0; }
}

.input-field-wrap { flex: 1; }

.input-field {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: #111827;
  line-height: 1.5;
  resize: none;
  max-height: 160px;
  font-family: inherit;
  padding: 4px 0;

  &::placeholder { color: #9CA3AF; }
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: #E5E7EB;
  color: #9CA3AF;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;

  &.send-btn--active {
    background: linear-gradient(135deg, #0EA5A0, #0D7380);
    color: #FFFFFF;
    box-shadow: 0 2px 8px rgba(14,165,160,0.3);
  }

  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.input-hint {
  font-size: 11px;
  color: #D1D5DB;
  text-align: center;
  margin-top: 6px;
}

// ── Responsive: iPad ─────────────────────────────────────────
@media (max-width: 768px) {
  .chat-page {
    height: calc(100dvh - 56px);
  }
  .chat-container {
    border-left: none;
    border-right: none;
    max-width: 100%;
  }
  .module-grid {
    grid-template-columns: repeat(2, 1fr);
    max-width: 100%;
  }
  .welcome-state { padding: 24px 16px 16px; }
  .welcome-title { font-size: 22px; }
}

@media (max-width: 480px) {
  .module-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .module-card { padding: 12px; gap: 8px; }
  .module-card-icon { width: 34px; height: 34px; }
  .module-card-title { font-size: 12px; }
  .module-card-desc { display: none; }
  .welcome-title { font-size: 20px; }
}

// iPad landscape: 3 columns
@media (min-width: 768px) and (max-width: 1024px) {
  .module-grid { grid-template-columns: repeat(3, 1fr); }
}

// Dark mode
.body--dark {
  .chat-page { background: #0F172A; }
  .chat-container { background: #111827; border-color: #1F2937; }
  .welcome-title { color: #F9FAFB; }
  .welcome-subtitle { color: #9CA3AF; }
  .welcome-avatar { background: rgba(14,165,160,0.1); border-color: rgba(14,165,160,0.2); }
  .module-card {
    background: #1F2937; border-color: #374151;
    .module-card-title { color: #F9FAFB; }
    &:hover { border-color: #4B5563; }
  }
  .suggestion-chip { background: #1F2937; border-color: #374151; color: #D1D5DB; &:hover { background: rgba(14,165,160,0.1); border-color: rgba(14,165,160,0.3); color: #5EEAD4; } }
  .msg-row.assistant .msg-bubble { background: #1F2937; border-color: #374151; color: #F9FAFB; }
  .typing-bubble { background: #1F2937; border-color: #374151; }
  .input-area { background: #111827; border-top-color: #1F2937; }
  .input-row { background: #1F2937; border-color: #374151; &:focus-within { border-color: #0EA5A0; background: #1F2937; } }
  .input-field { color: #F9FAFB; &::placeholder { color: #4B5563; } }
  .input-hint { color: #4B5563; }
}
</style>
