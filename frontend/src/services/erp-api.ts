import api from './api'

export const erpApi = {
  // CRUD
  async listItems(params?: {
    direction?: string
    status?: string
    counterparty?: string
    start?: string
    end?: string
    limit?: number
    offset?: number
  }) {
    const response = await api.get('/modules/erp/items', { params })
    return response.data
  },

  async getItem(id: number) {
    const response = await api.get(`/modules/erp/items/${id}`)
    return response.data
  },

  async createItem(data: {
    direction: string
    invoice_number?: string
    invoice_date: string
    due_date?: string
    net_amount?: number
    vat_rate?: number
    gross_amount?: number
    counterparty?: string
    category?: string
    document_id?: string
    notes?: string
  }) {
    const response = await api.post('/modules/erp/items', data)
    return response.data
  },

  async updateItem(id: number, data: {
    invoice_number?: string
    invoice_date?: string
    due_date?: string
    net_amount?: number
    vat_rate?: number
    gross_amount?: number
    counterparty?: string
    category?: string
    payment_status?: string
    payment_date?: string
    notes?: string
  }) {
    const response = await api.patch(`/modules/erp/items/${id}`, data)
    return response.data
  },

  async deleteItem(id: number) {
    await api.delete(`/modules/erp/items/${id}`)
  },

  // Dashboard
  async getDashboard(start: string, end: string) {
    const response = await api.get('/modules/erp/dashboard', { params: { start, end } })
    return response.data
  },

  // Reports
  async getBWA(start: string, end: string) {
    const response = await api.get('/modules/erp/reports/bwa', { params: { start, end } })
    return response.data
  },

  async getUSt(start: string, end: string) {
    const response = await api.get('/modules/erp/reports/ust', { params: { start, end } })
    return response.data
  },

  async downloadCSV(start: string, end: string) {
    const response = await api.get('/modules/erp/reports/csv', {
      params: { start, end },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `vera_erp_${start}_${end}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  async downloadDATEV(start: string, end: string, beraterNr: number, mandantenNr: number) {
    const response = await api.get('/modules/erp/reports/datev', {
      params: { start, end, berater_nr: beraterNr, mandanten_nr: mandantenNr },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `EXTF_${start.replace(/-/g, '')}_${end.replace(/-/g, '')}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  // Open Items
  async getOpenItems(direction?: string) {
    const response = await api.get('/modules/erp/open-items', { params: direction ? { direction } : {} })
    return response.data
  },

  // Stats
  async getStats() {
    const response = await api.get('/modules/erp/stats')
    return response.data
  }
}
