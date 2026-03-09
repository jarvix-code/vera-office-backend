import { defineStore } from 'pinia'
import { ref } from 'vue'
import { erpApi } from '@/services/erp-api'
import type {
  FinancialRecord,
  FinancialRecordCreate,
  FinancialRecordUpdate,
  ErpDashboard,
  BWAReport,
  UStReport,
  OpenItem,
  ErpStats
} from '@/types/erp'

export const useErpStore = defineStore('erp', () => {
  const loading = ref(false)
  const items = ref<FinancialRecord[]>([])
  const currentItem = ref<FinancialRecord | null>(null)
  const dashboard = ref<ErpDashboard | null>(null)
  const bwa = ref<BWAReport | null>(null)
  const ust = ref<UStReport | null>(null)
  const openItems = ref<OpenItem[]>([])
  const stats = ref<ErpStats | null>(null)

  async function fetchItems(params?: {
    direction?: string
    status?: string
    counterparty?: string
    start?: string
    end?: string
    limit?: number
    offset?: number
  }) {
    loading.value = true
    try {
      items.value = await erpApi.listItems(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchItem(id: number) {
    loading.value = true
    try {
      currentItem.value = await erpApi.getItem(id)
    } finally {
      loading.value = false
    }
  }

  async function createItem(data: FinancialRecordCreate): Promise<FinancialRecord> {
    const item = await erpApi.createItem(data)
    await fetchItems()
    return item
  }

  async function updateItem(id: number, data: FinancialRecordUpdate): Promise<FinancialRecord> {
    const item = await erpApi.updateItem(id, data)
    currentItem.value = item
    return item
  }

  async function deleteItem(id: number) {
    await erpApi.deleteItem(id)
    await fetchItems()
  }

  async function fetchDashboard(start: string, end: string) {
    loading.value = true
    try {
      dashboard.value = await erpApi.getDashboard(start, end)
    } finally {
      loading.value = false
    }
  }

  async function fetchBWA(start: string, end: string) {
    loading.value = true
    try {
      bwa.value = await erpApi.getBWA(start, end)
    } finally {
      loading.value = false
    }
  }

  async function fetchUSt(start: string, end: string) {
    loading.value = true
    try {
      ust.value = await erpApi.getUSt(start, end)
    } finally {
      loading.value = false
    }
  }

  async function fetchOpenItems(direction?: string) {
    loading.value = true
    try {
      openItems.value = await erpApi.getOpenItems(direction)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    stats.value = await erpApi.getStats()
  }

  return {
    loading, items, currentItem, dashboard, bwa, ust, openItems, stats,
    fetchItems, fetchItem, createItem, updateItem, deleteItem,
    fetchDashboard, fetchBWA, fetchUSt, fetchOpenItems, fetchStats
  }
})
