import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentsApi } from '@/services/api'

export interface Document {
  id: number
  filename: string
  original_filename?: string
  file_size: number
  category_id?: number
  category_name?: string
  classification_confidence?: number
  ocr_text?: string
  document_date?: string
  sender?: string
  reference_number?: string
  amount?: number
  page_count: number
  processed: boolean
  created_at: string
  // Computed aliases for frontend convenience
  title?: string
  document_type?: string
  upload_date?: string
}

export const useDocumentsStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const total = ref(0)

  function mapDocument(doc: any): Document {
    return {
      ...doc,
      title: doc.original_filename || doc.filename,
      document_type: doc.category_name || 'Unbekannt',
      upload_date: doc.created_at
    }
  }

  async function fetchDocuments(params?: { skip?: number; limit?: number; search?: string }) {
    loading.value = true
    try {
      const result = await documentsApi.list(params)
      const items = result.items || result.documents || result
      documents.value = (Array.isArray(items) ? items : []).map(mapDocument)
      total.value = result.total || documents.value.length
      return result
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: string) {
    loading.value = true
    try {
      const doc = await documentsApi.get(id)
      currentDocument.value = mapDocument(doc)
      return currentDocument.value
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File) {
    loading.value = true
    try {
      const result = await documentsApi.upload(file)
      await fetchDocuments()
      return result
    } finally {
      loading.value = false
    }
  }

  async function deleteDocument(id: string) {
    loading.value = true
    try {
      await documentsApi.delete(id)
      await fetchDocuments()
    } finally {
      loading.value = false
    }
  }

  async function searchDocuments(query: string) {
    loading.value = true
    try {
      const response = await documentsApi.search(query)
      const items = response.results || response.documents || response
      documents.value = (Array.isArray(items) ? items : []).map(mapDocument)
      return { documents: documents.value, total: response.total || documents.value.length }
    } finally {
      loading.value = false
    }
  }

  return {
    documents,
    currentDocument,
    loading,
    total,
    fetchDocuments,
    fetchDocument,
    uploadDocument,
    deleteDocument,
    searchDocuments
  }
})
