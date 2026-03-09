/**
 * Auth Store — JWT-basierte Authentifizierung
 * 
 * Verwaltet Login-Status, Token, User-Info
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const user = ref<any | null>(null)
  const loading = ref(false)
  const isAuthenticated = ref(!!token.value)

  /**
   * Login mit Username + Passwort
   */
  async function login(username: string, password: string) {
    loading.value = true
    
    try {
      const response = await api.post('/auth/login', { username, password })
      
      token.value = response.data.access_token
      user.value = response.data.user
      isAuthenticated.value = true
      
      // Token im localStorage speichern
      if (token.value) {
        localStorage.setItem('auth_token', token.value)
        console.log('[Auth] Token gespeichert:', token.value.substring(0, 20) + '...')
      } else {
        console.error('[Auth] Kein Token vom Server erhalten!')
      }
      
      // Token in Axios Default-Header setzen (redundant, aber zusätzliche Sicherheit)
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
      
      return { success: true }
    } catch (error: any) {
      console.error('Login failed:', error)
      return {
        success: false,
        message: error.response?.data?.detail || 'Login fehlgeschlagen'
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * Logout
   */
  async function logout() {
    try {
      // Server-seitiger Logout (optional - JWT ist stateless)
      if (token.value) {
        await api.post('/auth/logout')
      }
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      // Lokale Session löschen
      token.value = null
      user.value = null
      isAuthenticated.value = false
      
      localStorage.removeItem('auth_token')
      delete api.defaults.headers.common['Authorization']
    }
  }

  /**
   * Lade User-Info vom Server (beim App-Start)
   */
  async function fetchUser() {
    if (!token.value) {
      return
    }

    try {
      const response = await api.get('/auth/me')
      user.value = response.data
      isAuthenticated.value = true
    } catch (error) {
      console.error('Failed to fetch user:', error)
      // Token ungültig → Logout
      await logout()
    }
  }

  /**
   * Initialisiere Auth-Store (beim App-Start)
   * Setzt Token in Axios Header wenn vorhanden
   */
  function init() {
    if (token.value) {
      console.log('[Auth] Initialisiere mit gespeichertem Token:', token.value.substring(0, 20) + '...')
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
      fetchUser() // User-Info laden
    } else {
      console.log('[Auth] Kein gespeicherter Token gefunden - User nicht eingeloggt')
    }
  }

  return {
    // State
    token,
    user,
    loading,
    isAuthenticated,
    
    // Actions
    login,
    logout,
    fetchUser,
    init
  }
})
