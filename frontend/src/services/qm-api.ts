import api from './api'

export const qmApi = {
  // Dashboard
  async getDashboard() {
    const response = await api.get('/modules/qm/dashboard')
    return response.data
  },

  async getStats() {
    const response = await api.get('/modules/qm/stats')
    return response.data
  },

  // Handbuch
  async getHandbook() {
    const response = await api.get('/modules/qm/handbook')
    return response.data
  },

  async getHandbookChapter(chapterId: string) {
    const response = await api.get(`/modules/qm/handbook/${chapterId}`)
    return response.data
  },

  // Dokumente
  async listDocuments(params?: { area?: string; status?: string; limit?: number; offset?: number }) {
    const response = await api.get('/modules/qm/documents', { params })
    return response.data
  },

  async getDocument(id: number) {
    const response = await api.get(`/modules/qm/documents/${id}`)
    return response.data
  },

  async createDocument(data: {
    title: string
    main_area: string
    content?: string
    grundelemente?: string[]
    tags?: string[]
  }) {
    const response = await api.post('/modules/qm/documents', data)
    return response.data
  },

  async updateDocument(id: number, data: {
    title?: string
    content?: string
    status?: string
    grundelemente?: string[]
    tags?: string[]
    approved_by?: string
  }) {
    const response = await api.patch(`/modules/qm/documents/${id}`, data)
    return response.data
  },

  async deleteDocument(id: number) {
    const response = await api.delete(`/modules/qm/documents/${id}`)
    return response.data
  },

  // Audits
  async listAudits() {
    const response = await api.get('/modules/qm/audits')
    return response.data
  },

  async getAudit(id: number) {
    const response = await api.get(`/modules/qm/audits/${id}`)
    return response.data
  },

  async createAudit(data: { title: string; auditor: string }) {
    const response = await api.post('/modules/qm/audits', data)
    return response.data
  },

  async answerQuestion(auditId: number, questionId: string, data: { answer: string; notes?: string }) {
    const response = await api.put(`/modules/qm/audits/${auditId}/answer/${questionId}`, data)
    return response.data
  },

  async finalizeAudit(id: number) {
    const response = await api.post(`/modules/qm/audits/${id}/finalize`)
    return response.data
  },

  async getAuditReport(id: number) {
    const response = await api.get(`/modules/qm/audits/${id}/report`)
    return response.data
  },

  async deleteAudit(id: number) {
    const response = await api.delete(`/modules/qm/audits/${id}`)
    return response.data
  },

  // Hygiene
  async listHygiene() {
    const response = await api.get('/modules/qm/hygiene')
    return response.data
  },

  async getHygiene(id: number) {
    const response = await api.get(`/modules/qm/hygiene/${id}`)
    return response.data
  },

  async createHygiene(data: { title: string; area?: string }) {
    const response = await api.post('/modules/qm/hygiene', data)
    return response.data
  },

  async checkHygieneItem(id: number, data: { item: string; checked: boolean; notes?: string }) {
    const response = await api.put(`/modules/qm/hygiene/${id}/check`, data)
    return response.data
  },

  async deleteHygiene(id: number) {
    const response = await api.delete(`/modules/qm/hygiene/${id}`)
    return response.data
  },

  // Compliance
  async listCompliance(params?: { category?: string; fulfilled?: boolean }) {
    const response = await api.get('/modules/qm/compliance', { params })
    return response.data
  },

  async createCompliance(data: {
    title: string
    category: string
    requirement: string
    due_date?: string
  }) {
    const response = await api.post('/modules/qm/compliance', data)
    return response.data
  },

  async updateCompliance(id: number, data: {
    title?: string
    fulfilled?: boolean
    evidence?: string
    due_date?: string
  }) {
    const response = await api.patch(`/modules/qm/compliance/${id}`, data)
    return response.data
  },

  async deleteCompliance(id: number) {
    const response = await api.delete(`/modules/qm/compliance/${id}`)
    return response.data
  },

  // BLZK Portal Integration
  async getBLZKCredentials() {
    const response = await api.get('/modules/qm/blzk/credentials')
    return response.data
  },

  async saveBLZKCredentials(data: { username: string; password: string }) {
    const response = await api.post('/modules/qm/blzk/credentials', data)
    return response.data
  },

  async deleteBLZKCredentials() {
    const response = await api.delete('/modules/qm/blzk/credentials')
    return response.data
  },

  async testBLZKLogin(data?: { username: string; password: string }) {
    const response = await api.post('/modules/qm/blzk/login', data || {})
    return response.data
  },

  async getBLZKPortalDocuments(area?: string) {
    const response = await api.get('/modules/qm/blzk/documents', { params: area ? { area } : {} })
    return response.data
  },

  async downloadBLZKDocuments(data: { doc_ids: string[]; filename?: string }) {
    const response = await api.post('/modules/qm/blzk/download', data)
    return response.data
  },

  // BLZK Katalog + Requirements
  async getBLZKKatalog() {
    const response = await api.get('/modules/qm/blzk/katalog')
    return response.data
  },

  async getBLZKFristen() {
    const response = await api.get('/modules/qm/blzk/fristen')
    return response.data
  },

  async getBLZKRequirements(keyword?: string) {
    const response = await api.get('/modules/qm/blzk/requirements', { params: keyword ? { keyword } : {} })
    return response.data
  },

  async getBLZKRequirement(questionId: string) {
    const response = await api.get(`/modules/qm/blzk/requirements/${questionId}`)
    return response.data
  }
}
