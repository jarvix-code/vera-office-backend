import axios from 'axios'
import { Notify } from 'quasar'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor — Bearer Token hinzufügen
api.interceptors.request.use(
  (config) => {
    // Token aus localStorage holen
    const token = localStorage.getItem('auth_token')

    if (token) {
      // Setze Authorization-Header (überschreibt falls bereits vorhanden)
      config.headers.Authorization = `Bearer ${token}`
      console.debug('[API] Request mit Auth Token:', config.method?.toUpperCase(), config.url)
    } else {
      console.warn('[API] Kein Auth Token gefunden für:', config.method?.toUpperCase(), config.url)
      // Entferne Authorization-Header falls vorhanden (sollte nicht passieren)
      delete config.headers.Authorization
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor — 401 = Token ungültig → Redirect zu Login
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 401 Unauthorized → Token löschen, KEIN Redirect (Boris Auth v2: kein Zwangs-Login)
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      return Promise.reject(error)
    }

    // Hintergrundcalls mit { params: { _silent: true } } oder Header 'x-silent' unterdrücken Notification
    const isSilent = error.config?.params?._silent || error.config?.headers?.['x-silent']
    if (!isSilent) {
      const message = error.response?.data?.detail || error.message || 'Ein Fehler ist aufgetreten'
      Notify.create({
        type: 'negative',
        message: message,
        position: 'bottom'
      })
    }
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
      name: name.toLowerCase().replace(/\s+/g, '_').replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss'),
      display_name: name,
      storage_path: name.toLowerCase().replace(/\s+/g, '_').replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
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

// Dashboard API
export const dashboardApi = {
  async getData() {
    const response = await api.get('/dashboard')
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
    // Silent: Fehler beim Start sollen keine rote Notification zeigen
    const response = await api.get('/agent/suggestions', { params: { _silent: true } })
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
// TODO: Backend-Endpoint /api/auth/chat existiert noch nicht → gibt 404 zurück.
//       Entweder in backend/api/auth.py implementieren oder diesen API-Call entfernen.
//       Wird derzeit nicht aktiv aufgerufen — nur als Stub definiert.
export const authChatApi = {
  async chat(data: { message: string; session_id?: string }) {
    // TODO: /api/auth/chat implementieren (Bug #17)
    const response = await api.post('/auth/chat', data)
    return response.data
  }
}

// USB Import API
export const usbApi = {
  async scan() {
    const response = await api.get('/import-usb/scan')
    return response.data
  },

  async import(folders: string[]) {
    const response = await api.post('/import-usb', { folders })
    return response.data
  },

  async progress(jobId: string) {
    const response = await api.get(`/import-usb/progress/${jobId}`, {
      params: { _silent: true } // Kein Error-Toast bei Polling
    })
    return response.data
  }
}

// QM RAG API
export const qmApi = {
  async search(query: string, topK: number = 5, categoryFilter?: string) {
    const response = await api.post('/qm/search', {
      query,
      top_k: topK,
      category_filter: categoryFilter
    })
    return response.data
  },

  async index(force: boolean = false) {
    const response = await api.post('/qm/index', { force })
    return response.data
  },

  async getStats() {
    const response = await api.get('/qm/stats')
    return response.data
  },

  async getDocument(docId: number) {
    const response = await api.get(`/qm/document/${docId}`)
    return response.data
  }
}

export default api

