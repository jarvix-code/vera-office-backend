/**
 * Auth Store — Boris Auth v2
 * Kein Login-Zwang. PIN/Master nur für geschützte Module.
 * Tokens werden in sessionStorage gespeichert (weg bei Browser-Schließen).
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

const SESSION_KEY_MODULE = 'vera_module_token'
const SESSION_KEY_MASTER = 'vera_master_token'
// Key used by moduleAuth store -- must be cleared on logout (Bug #679)
const SESSION_KEY_MODULE_SESSION = 'vera_module_session'

export const useAuthStore = defineStore('auth', () => {
  // Legacy JWT (fuer Rueckwaertskompatibilitaet -- onboarding admin creation)
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const user = ref<any | null>(null)
  const loading = ref(false)

  // Boris Auth v2 -- Module PIN tokens (in sessionStorage)
  const moduleToken = ref<string | null>(sessionStorage.getItem(SESSION_KEY_MODULE))
  const masterToken = ref<string | null>(sessionStorage.getItem(SESSION_KEY_MASTER))
  const unlockedModules = ref<string[]>(_parseModulesFromToken(moduleToken.value))

  // Bug #675 fix: isAuthenticated is true only when a valid auth_token exists in localStorage
  const isAuthenticated = ref<boolean>(!!localStorage.getItem('auth_token'))

  // Modul-Auth Dialog state -- wird vom Router Guard gesetzt
  const pendingModuleAccess = ref<string | null>(null)
  const pendingRedirectPath = ref<string | null>(null)

  async function verifyPin(pin: string): Promise<{ success: boolean; message?: string; modules?: string[] }> {
    loading.value = true
    try {
      const response = await api.post('/auth/verify-pin', { pin })
      const { access_token, modules } = response.data
      moduleToken.value = access_token
      unlockedModules.value = modules || []
      sessionStorage.setItem(SESSION_KEY_MODULE, access_token)
      api.defaults.headers.common['Authorization'] = 'Bearer ' + access_token
      return { success: true, modules }
    } catch (error: any) {
      return { success: false, message: error.response?.data?.detail || 'Falsche PIN' }
    } finally {
      loading.value = false
    }
  }

  async function verifyMaster(masterPw: string): Promise<{ success: boolean; message?: string }> {
    loading.value = true
    try {
      const response = await api.post('/auth/verify-master', { master_pw: masterPw })
      const { access_token } = response.data
      masterToken.value = access_token
      sessionStorage.setItem(SESSION_KEY_MASTER, access_token)
      api.defaults.headers.common['Authorization'] = 'Bearer ' + access_token
      return { success: true }
    } catch (error: any) {
      return { success: false, message: error.response?.data?.detail || 'Falsches Master-Passwort' }
    } finally {
      loading.value = false
    }
  }

  async function unlockModule(promoCode: string): Promise<{ success: boolean; message?: string; modules?: string[] }> {
    try {
      const response = await api.post('/modules/unlock', { promo_code: promoCode })
      if (response.data.success) {
        const statusResp = await api.get('/modules/status')
        _updateUnlockedFromStatus(statusResp.data.modules)
        return { success: true, modules: response.data.modules_unlocked }
      }
      return { success: false }
    } catch (error: any) {
      return { success: false, message: error.response?.data?.detail || 'Fehler beim Freischalten' }
    }
  }

  function hasModuleAccess(module: string): boolean {
    if (masterToken.value && _isTokenValid(masterToken.value)) return true
    if (!moduleToken.value || !_isTokenValid(moduleToken.value)) return false
    return unlockedModules.value.includes(module)
  }

  function isModuleUnlocked(module: string): boolean {
    return unlockedModules.value.includes(module)
  }

  async function fetchModuleStatus() {
    try {
      const response = await api.get('/modules/status')
      _updateUnlockedFromStatus(response.data.modules)
    } catch {
      // ignore -- offline mode
    }
  }

  function clearModuleSession() {
    moduleToken.value = null
    masterToken.value = null
    unlockedModules.value = []
    sessionStorage.removeItem(SESSION_KEY_MODULE)
    sessionStorage.removeItem(SESSION_KEY_MASTER)
    // Bug #679 fix: also clear moduleAuth localStorage session so modules dont persist after logout
    localStorage.removeItem(SESSION_KEY_MODULE_SESSION)
    delete api.defaults.headers.common['Authorization']
    if (token.value) {
      api.defaults.headers.common['Authorization'] = 'Bearer ' + token.value
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const response = await api.post('/auth/login', { username, password })
      token.value = response.data.access_token
      user.value = response.data.user
      if (token.value) {
        localStorage.setItem('auth_token', token.value)
        api.defaults.headers.common['Authorization'] = 'Bearer ' + token.value
        // Bug #675 fix: set isAuthenticated on successful login
        isAuthenticated.value = true
      }
      return { success: true }
    } catch (error: any) {
      return { success: false, message: error.response?.data?.detail || 'Login fehlgeschlagen' }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    token.value = null
    user.value = null
    // Bug #676 fix: set isAuthenticated to false on logout so router guard blocks access
    isAuthenticated.value = false
    localStorage.removeItem('auth_token')
    // clearModuleSession also removes vera_module_session from localStorage (Bug #679)
    clearModuleSession()
  }

  function init() {
    const savedModuleToken = sessionStorage.getItem(SESSION_KEY_MODULE)
    if (savedModuleToken && _isTokenValid(savedModuleToken)) {
      moduleToken.value = savedModuleToken
      unlockedModules.value = _parseModulesFromToken(savedModuleToken)
      api.defaults.headers.common['Authorization'] = 'Bearer ' + savedModuleToken
    } else if (token.value) {
      api.defaults.headers.common['Authorization'] = 'Bearer ' + token.value
    }
  }

  function _isTokenValid(token: string): boolean {
    try {
      const parts = token.split('.')
      if (parts.length !== 3) return false
      const payload = JSON.parse(atob(parts[1]))
      return payload.exp * 1000 > Date.now()
    } catch {
      return false
    }
  }

  function _parseModulesFromToken(token: string | null): string[] {
    if (!token) return []
    try {
      const parts = token.split('.')
      const payload = JSON.parse(atob(parts[1]))
      return payload.modules || []
    } catch {
      return []
    }
  }

  function _updateUnlockedFromStatus(modules: Record<string, { unlocked: boolean }>) {
    unlockedModules.value = Object.entries(modules)
      .filter(([, v]) => v.unlocked)
      .map(([k]) => k)
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    moduleToken,
    masterToken,
    unlockedModules,
    pendingModuleAccess,
    pendingRedirectPath,
    verifyPin,
    verifyMaster,
    unlockModule,
    hasModuleAccess,
    isModuleUnlocked,
    fetchModuleStatus,
    clearModuleSession,
    login,
    logout,
    init,
    fetchUser: async () => {},
  }
})
