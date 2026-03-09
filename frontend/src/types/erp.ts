/**
 * TypeScript types for ERP module.
 * Based on backend/modules/erp/schemas.py
 */

// ======= Enums =======

export type Direction = 'incoming' | 'outgoing'

export type PaymentStatus = 'open' | 'paid' | 'overdue'

// ======= CRUD =======

export interface FinancialRecord {
  id: number
  document_id: string | null
  direction: Direction
  invoice_number: string | null
  invoice_date: string
  due_date: string | null
  net_amount: number
  vat_rate: number
  vat_amount: number
  gross_amount: number
  counterparty: string | null
  category: string | null
  payment_status: PaymentStatus
  payment_date: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface FinancialRecordCreate {
  direction: Direction
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
}

export interface FinancialRecordUpdate {
  invoice_number?: string
  invoice_date?: string
  due_date?: string
  net_amount?: number
  vat_rate?: number
  gross_amount?: number
  counterparty?: string
  category?: string
  payment_status?: PaymentStatus
  payment_date?: string
  notes?: string
}

// ======= Dashboard =======

export interface MonthlyStats {
  month: string
  revenue: number
  expenses: number
  profit: number
}

export interface CategoryBreakdown {
  category: string
  amount: number
}

export interface TopCounterparty {
  name: string
  amount: number
}

export interface PeriodComparison {
  current: number
  previous: number
  delta: number
  delta_pct: number
}

export interface ErpDashboard {
  total_revenue: number
  total_expenses: number
  total_profit: number
  monthly: MonthlyStats[]
  categories: CategoryBreakdown[]
  top_suppliers: TopCounterparty[]
  top_customers: TopCounterparty[]
  comparison: PeriodComparison | null
}

// ======= BWA =======

export interface BWARow {
  label: string
  current: number
  previous: number | null
  delta: number | null
  delta_pct: number | null
}

export interface BWAReport {
  period_start: string
  period_end: string
  rows: BWARow[]
}

// ======= USt =======

export interface UStByRate {
  rate: number
  output_vat: number
  input_vat: number
  balance: number
}

export interface UStReport {
  period_start: string
  period_end: string
  total_output_vat: number
  total_input_vat: number
  total_balance: number
  by_rate: UStByRate[]
}

// ======= Open Items =======

export interface OpenItem {
  id: number
  direction: Direction
  invoice_number: string | null
  invoice_date: string
  due_date: string | null
  gross_amount: number
  counterparty: string | null
  days_until_due: number | null
  status_color: 'green' | 'yellow' | 'red'
}

// ======= Stats =======

export interface ErpStats {
  total: number
  open: number
  overdue: number
}
