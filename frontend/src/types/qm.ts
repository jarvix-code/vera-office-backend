/**
 * TypeScript types for QM module.
 * Based on backend/modules/qm/schemas.py + models.py enums.
 */

// ======= Enums =======

export type QMMainArea = 'Arbeitssicherheit' | 'Qualitätsmanagement' | 'Handbuch'

export type DocumentStatus = 'Entwurf' | 'In Prüfung' | 'Freigegeben' | 'Veraltet' | 'Archiviert'

export type QMGrundelement =
  | 'Patientenorientierung'
  | 'Mitarbeiterorientierung'
  | 'Prozessorientierung'
  | 'Führung und Verantwortung'
  | 'Fehlerkultur'
  | 'Kommunikation'

export type QuestionOption = 'Ja' | 'Nein' | 'Übersprungen'

export type AuditStatus = 'In Bearbeitung' | 'Abgeschlossen'

export type ProtocolStatus = 'Offen' | 'Abgeschlossen'

// ======= Documents =======

export interface QMDocumentRevision {
  id: number
  version: string
  content: string
  changelog: string | null
  created_by: string | null
  created_at: string
}

export interface QMDocument {
  id: number
  title: string
  main_area: QMMainArea
  content: string | null
  current_version: string
  status: DocumentStatus
  approved_by: string | null
  approved_at: string | null
  grundelemente: QMGrundelement[]
  tags: string[]
  created_at: string
  updated_at: string
  revisions: QMDocumentRevision[]
}

export interface QMDocumentCreate {
  title: string
  main_area: QMMainArea
  content?: string
  grundelemente?: QMGrundelement[]
  tags?: string[]
}

export interface QMDocumentUpdate {
  title?: string
  content?: string
  status?: DocumentStatus
  grundelemente?: QMGrundelement[]
  tags?: string[]
  approved_by?: string
}

// ======= Audits =======

export interface AuditQuestion {
  id: number
  question_id: string
  question_text: string
  category: QMGrundelement
  answer: QuestionOption | null
  notes: string | null
}

export interface AuditFinding {
  question_id: string
  finding: string
  notes: string | null
}

export interface AuditAction {
  action: string
  deadline: string | null
}

export interface Audit {
  id: number
  title: string
  auditor: string
  status: AuditStatus
  completion_percentage: number
  findings: AuditFinding[]
  actions: AuditAction[]
  created_at: string
  finalized_at: string | null
  questions: AuditQuestion[]
}

export interface AuditCreate {
  title: string
  auditor: string
}

export interface AuditQuestionAnswer {
  answer: QuestionOption
  notes?: string
}

export interface AuditReportCategory {
  answered: number
  total: number
  questions: Array<{
    id: string
    text: string
    answer: QuestionOption | null
    notes: string | null
  }>
}

export interface AuditReport {
  audit_id: number
  title: string
  auditor: string
  finalized_at: string | null
  categories: Record<string, AuditReportCategory>
  findings: AuditFinding[]
  actions: AuditAction[]
}

// ======= Hygiene =======

export interface ChecklistItem {
  item: string
  checked: boolean
  timestamp: string | null
  notes: string | null
}

export interface HygieneProtocol {
  id: number
  title: string
  area: string | null
  checklist: ChecklistItem[]
  status: ProtocolStatus
  created_at: string
  closed_at: string | null
}

export interface HygieneProtocolCreate {
  title: string
  area?: string
}

export interface HygieneCheckUpdate {
  item: string
  checked: boolean
  notes?: string
}

// ======= Compliance =======

export interface ComplianceCheck {
  id: number
  title: string
  category: QMGrundelement
  requirement: string
  fulfilled: boolean
  evidence: string | null
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface ComplianceCheckCreate {
  title: string
  category: QMGrundelement
  requirement: string
  due_date?: string
}

export interface ComplianceCheckUpdate {
  title?: string
  fulfilled?: boolean
  evidence?: string
  due_date?: string
}

// ======= Dashboard =======

export interface QMDashboard {
  total_documents: number
  documents_by_status: Record<string, number>
  open_audits: number
  total_audits: number
  open_hygiene: number
  total_hygiene: number
  compliance_rate: number
  unfulfilled_compliance: number
}

export interface QMStats {
  documents: number
  open_audits: number
  open_hygiene: number
  unfulfilled_compliance: number
}

// ======= Handbook =======

export interface HandbookChapter {
  id: string
  area: string
  title: string
  order: number
}

export type HandbookStructure = Record<string, HandbookChapter[]>

export interface HandbookChapterDetail {
  chapter: HandbookChapter
  documents: QMDocument[]
}
