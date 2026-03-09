import { defineStore } from 'pinia'
import { ref } from 'vue'
import { qmApi } from '@/services/qm-api'
import type {
  QMDashboard,
  QMStats,
  QMDocument,
  QMDocumentCreate,
  QMDocumentUpdate,
  Audit,
  AuditCreate,
  AuditQuestionAnswer,
  HygieneProtocol,
  HygieneProtocolCreate,
  HygieneCheckUpdate,
  ComplianceCheck,
  ComplianceCheckCreate,
  ComplianceCheckUpdate,
  HandbookStructure
} from '@/types/qm'

export const useQmStore = defineStore('qm', () => {
  const loading = ref(false)
  const dashboard = ref<QMDashboard | null>(null)
  const stats = ref<QMStats | null>(null)
  const documents = ref<QMDocument[]>([])
  const currentDocument = ref<QMDocument | null>(null)
  const audits = ref<Audit[]>([])
  const currentAudit = ref<Audit | null>(null)
  const hygieneProtocols = ref<HygieneProtocol[]>([])
  const currentHygiene = ref<HygieneProtocol | null>(null)
  const complianceChecks = ref<ComplianceCheck[]>([])
  const handbook = ref<HandbookStructure | null>(null)

  async function fetchDashboard() {
    loading.value = true
    try {
      dashboard.value = await qmApi.getDashboard()
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    stats.value = await qmApi.getStats()
  }

  async function fetchHandbook() {
    handbook.value = await qmApi.getHandbook()
  }

  async function fetchDocuments(params?: { area?: string; status?: string }) {
    loading.value = true
    try {
      documents.value = await qmApi.listDocuments(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: number) {
    loading.value = true
    try {
      currentDocument.value = await qmApi.getDocument(id)
    } finally {
      loading.value = false
    }
  }

  async function createDocument(data: QMDocumentCreate): Promise<QMDocument> {
    const doc = await qmApi.createDocument(data)
    await fetchDocuments()
    return doc
  }

  async function updateDocument(id: number, data: QMDocumentUpdate): Promise<QMDocument> {
    const doc = await qmApi.updateDocument(id, data)
    currentDocument.value = doc
    return doc
  }

  async function deleteDocument(id: number) {
    await qmApi.deleteDocument(id)
    await fetchDocuments()
  }

  async function fetchAudits() {
    loading.value = true
    try {
      audits.value = await qmApi.listAudits()
    } finally {
      loading.value = false
    }
  }

  async function fetchAudit(id: number) {
    loading.value = true
    try {
      currentAudit.value = await qmApi.getAudit(id)
    } finally {
      loading.value = false
    }
  }

  async function createAudit(data: AuditCreate): Promise<Audit> {
    const audit = await qmApi.createAudit(data)
    await fetchAudits()
    return audit
  }

  async function answerQuestion(auditId: number, questionId: string, data: AuditQuestionAnswer): Promise<Audit> {
    const audit = await qmApi.answerQuestion(auditId, questionId, data)
    currentAudit.value = audit
    return audit
  }

  async function finalizeAudit(id: number): Promise<Audit> {
    const audit = await qmApi.finalizeAudit(id)
    currentAudit.value = audit
    return audit
  }

  async function deleteAudit(id: number) {
    await qmApi.deleteAudit(id)
    await fetchAudits()
  }

  async function fetchHygiene() {
    loading.value = true
    try {
      hygieneProtocols.value = await qmApi.listHygiene()
    } finally {
      loading.value = false
    }
  }

  async function fetchHygieneDetail(id: number) {
    loading.value = true
    try {
      currentHygiene.value = await qmApi.getHygiene(id)
    } finally {
      loading.value = false
    }
  }

  async function createHygiene(data: HygieneProtocolCreate): Promise<HygieneProtocol> {
    const protocol = await qmApi.createHygiene(data)
    await fetchHygiene()
    return protocol
  }

  async function checkHygieneItem(id: number, data: HygieneCheckUpdate): Promise<HygieneProtocol> {
    const protocol = await qmApi.checkHygieneItem(id, data)
    currentHygiene.value = protocol
    return protocol
  }

  async function deleteHygiene(id: number) {
    await qmApi.deleteHygiene(id)
    await fetchHygiene()
  }

  async function fetchCompliance(params?: { category?: string; fulfilled?: boolean }) {
    loading.value = true
    try {
      complianceChecks.value = await qmApi.listCompliance(params)
    } finally {
      loading.value = false
    }
  }

  async function createCompliance(data: ComplianceCheckCreate): Promise<ComplianceCheck> {
    const check = await qmApi.createCompliance(data)
    await fetchCompliance()
    return check
  }

  async function updateCompliance(id: number, data: ComplianceCheckUpdate): Promise<ComplianceCheck> {
    const check = await qmApi.updateCompliance(id, data)
    await fetchCompliance()
    return check
  }

  async function deleteCompliance(id: number) {
    await qmApi.deleteCompliance(id)
    await fetchCompliance()
  }

  return {
    loading, dashboard, stats, documents, currentDocument,
    audits, currentAudit, hygieneProtocols, currentHygiene,
    complianceChecks, handbook,
    fetchDashboard, fetchStats, fetchHandbook,
    fetchDocuments, fetchDocument, createDocument, updateDocument, deleteDocument,
    fetchAudits, fetchAudit, createAudit, answerQuestion, finalizeAudit, deleteAudit,
    fetchHygiene, fetchHygieneDetail, createHygiene, checkHygieneItem, deleteHygiene,
    fetchCompliance, createCompliance, updateCompliance, deleteCompliance
  }
})
