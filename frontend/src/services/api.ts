import axios from 'axios'
import { Notify } from 'quasar'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor â€" Bearer Token hinzufÃ¼gen
api.interceptors.request.use(
  (config) => {
    // Token aus localStorage holen
    const token = localStorage.getItem('auth_token')
    
    if (token) {
      // Setze Authorization-Header (Ã¼berschreibt falls bereits vorhanden)
      config.headers.Authorization = `Bearer ${token}`
      console.debug('[API] Request mit Auth Token:', config.method?.toUpperCase(), config.url)
    } else {
      console.warn('[API] Kein Auth Token gefunden fÃ¼r:', config.method?.toUpperCase(), config.url)
      // Entferne Authorization-Header falls vorhanden (sollte nicht passieren)
      delete config.headers.Authorization
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor â€" 401 = Token ungÃ¼ltig â†' Redirect zu Login
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Ein Fehler ist aufgetreten'

    // 401 Unauthorized â†' Token ungÃ¼ltig â†' Logout + Redirect
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')

      // Nur redirecten wenn nicht bereits auf Login-Seite
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname)
      }

      return Promise.reject(error)
    }

    Notify.create({
      type: 'negative',
      message: message,
      position: 'bottom'
    })
    return Promise.reject(error)
  }
)

// Document API
export const documentsApi = {
  async upload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  async list(params?: { skip?: number; limit?: number; search?: string }) {
    const response = await api.get('/documents/list', { params })
    return response.data
  },

  async get(id: string) {
    const response = await api.get(`/documents/${id}`)
    return response.data
  },

  async download(id: string) {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob'
    })
    return response.data
  },

  async delete(id: string) {
    const response = await api.delete(`/documents/${id}`)
    return response.data
  },

  async search(query: string) {
    const response = await api.get('/documents/search/query', { params: { q: query } })
    return response.data
  }
}

// Onboarding API
export const onboardingApi = {
  async getStatus() {
    const response = await api.get('/onboarding/status')
    return response.data
  },

  async submitStep1(data: {
    company_name: string
    company_type: string
    industry: string
    employee_range: string
  }) {
    const response = await api.post('/onboarding/step1', {
      profile: {
        company_type: data.company_type,
        industry: data.industry,
        employee_range: data.employee_range
      }
    })
    return response.data
  },

  async getSuggestions() {
    const response = await api.get('/onboarding/step2/suggestions')
    return response.data
  },

  async submitStep2(categories: string[]) {
    const document_types = categories.map(name => ({
      name: name.toLowerCase().replace(/\s+/g, '_').replace(/Ã¤/g, 'ae').replace(/Ã¶/g, 'oe').replace(/Ã¼/g, 'ue'),
      display_name: name,
      storage_path: name.toLowerCase().replace(/\s+/g, '_').replace(/Ã¤/g, 'ae').replace(/Ã¶/g, 'oe').replace(/Ã¼/g, 'ue')
    }))
    const response = await api.post('/onboarding/step2', { document_types })
    return response.data
  },

  async submitStep3(data: {
    internet_access: boolean
    email_enabled: boolean
    auto_email: boolean
    network_shares: string[]
  }) {
    const response = await api.post('/onboarding/step3', {
      network: {
        internet_enabled: data.internet_access,
        email_enabled: data.email_enabled,
        network_shares: data.network_shares
      }
    })
    return response.data
  },

  async complete() {
    const response = await api.post('/onboarding/complete')
    return response.data
  }
}

// Onboarding Admin API
export const onboardingAdminApi = {
  async checkExists() {
    const response = await api.get('/onboarding/admin/exists')
    return response.data
  },

  async createAdmin(data: {
    username: string
    password: string
    password_confirm: string
    full_name?: string
    email?: string
  }) {
    const response = await api.post('/onboarding/admin/create', data)
    return response.data
  }
}

// System API
export const systemApi = {
  async getStatus() {
    const response = await api.get('/system/status')
    return response.data
  },

  async getStats() {
    const response = await api.get('/system/stats')
    return response.data
  },

  async getDiscovery() {
    const response = await api.get('/system/discovery')
    return response.data
  }
}

// Update API
export const updateApi = {
  async getStatus() {
    const response = await api.get('/system/update-status')
    return response.data
  },

  async checkForUpdate() {
    const response = await api.post('/system/check-update')
    return response.data
  },

  async downloadAndApply(version: string) {
    const response = await api.post('/system/apply-update', { version }, { timeout: 300000 })
    return response.data
  },

  async getVersion() {
    const response = await api.get('/system/version')
    return response.data
  }
}

// Scanner API
export const scannerApi = {
  async discover() {
    const response = await api.get('/scanner/discover')
    return response.data
  },

  async scan(scannerId: string, settings?: {
    resolution?: number
    color_mode?: string
    format?: string
  }) {
    const response = await api.post('/scanner/scan', {
      scanner_id: scannerId,
      resolution: settings?.resolution || 300,
      color_mode: settings?.color_mode || 'RGB24',
      format: settings?.format || 'image/jpeg'
    })
    return response.data
  },

  async health() {
    const response = await api.get('/scanner/health')
    return response.data
  }
}

// Agent API (VERA Chat)
export const agentApi = {
  async chat(data: { message: string; session_id?: string }) {
    const response = await api.post('/agent/chat', data)
    return response.data
  },

  async suggestions() {
    const response = await api.get('/agent/suggestions')
    return response.data
  },

  async voice(audioData: Blob) {
    const formData = new FormData()
    formData.append('audio', audioData)
    const response = await api.post('/agent/voice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
}

// Conversational Auth API
export const authChatApi = {
  async chat(data: { message: string; session_id?: string }) {
    const response = await api.post('/auth/chat', data)
    return response.data
  }
}

export default api

