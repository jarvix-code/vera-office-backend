import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentApi, authChatApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface Suggestion {
  title: string
  description: string
  priority: 'low' | 'medium' | 'high'
  action: string
  action_data?: Record<string, any>
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const suggestions = ref<string[]>([])
  const proactiveSuggestions = ref<Suggestion[]>([])
  const sessionId = ref<string>('default')
  
  // Conversational Auth State
  const authMode = ref(false)  // true = Auth-Flow, false = Normal Chat
  const authSessionId = ref<string>('')

  function addMessage(role: 'user' | 'assistant', content: string) {
    messages.value.push({
      role,
      content,
      timestamp: new Date()
    })
  }

  async function sendMessage(text: string) {
    // Allow empty message for initial greeting (onboarding or auth)
    const isInitialGreeting = text === '' && messages.value.length === 0
    
    if (!isInitialGreeting && !text.trim()) return

    // Add user message (except for initial greeting)
    if (!isInitialGreeting) {
      addMessage('user', text)
    }
    
    loading.value = true

    try {
      let response
      
      // AUTH MODE: Use conversational auth endpoint
      if (authMode.value) {
        response = await authChatApi.chat({
          message: text || ' ',  // Send space if empty to trigger greeting
          session_id: authSessionId.value
        })
        
        // Update auth session ID (backend might have created a new one)
        if (response.session_id) {
          authSessionId.value = response.session_id
        }
        
        // Add VERA's auth response
        addMessage('assistant', response.message)
        
        // Update suggestions
        suggestions.value = response.suggestions || []
        
        // Check if authenticated
        if (response.authenticated && response.token) {
          // SUCCESS: User authenticated via chat
          const authStore = useAuthStore()
          
          // Store token and user info in auth store
          authStore.token = response.token
          authStore.user = response.user_info
          authStore.isAuthenticated = true
          localStorage.setItem('auth_token', response.token)
          
          // Exit auth mode
          authMode.value = false
          
          // Add welcome message
          const username = response.user_info?.username || 'du'
          addMessage('assistant', `Perfekt! Du bist jetzt angemeldet, ${username}! 🎉\n\nWas kann ich für dich tun?`)
          
          // Load normal chat suggestions
          await loadSuggestions()
        }
        
        return response
      }
      
      // NORMAL MODE: Use regular agent chat
      else {
        response = await agentApi.chat({
          message: text || ' ',  // Send space if empty to trigger greeting
          session_id: sessionId.value
        })

        // Add VERA's response
        addMessage('assistant', response.response)
        
        // Update suggestions
        suggestions.value = response.suggestions || []

        return response
      }
    } catch (error) {
      console.error('Chat error:', error)
      addMessage('assistant', 'Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function loadSuggestions() {
    try {
      const response = await agentApi.suggestions()
      proactiveSuggestions.value = response.suggestions || []
      return response
    } catch (error) {
      console.error('Suggestions error:', error)
      return { suggestions: [] }
    }
  }

  function clearChat() {
    messages.value = []
    suggestions.value = []
  }

  function generateSessionId() {
    sessionId.value = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
  
  function startAuthFlow() {
    /**
     * Start conversational authentication flow.
     * Called when user is not authenticated and wants to login via chat.
     */
    authMode.value = true
    authSessionId.value = `auth_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    clearChat()
    
    // Trigger initial greeting by sending empty message
    sendMessage('')
  }
  
  function exitAuthFlow() {
    /**
     * Exit auth flow (e.g. when user cancels or uses /login form instead)
     */
    authMode.value = false
    authSessionId.value = ''
    clearChat()
  }

  return {
    messages,
    loading,
    suggestions,
    proactiveSuggestions,
    sessionId,
    authMode,
    sendMessage,
    loadSuggestions,
    clearChat,
    generateSessionId,
    startAuthFlow,
    exitAuthFlow
  }
})
