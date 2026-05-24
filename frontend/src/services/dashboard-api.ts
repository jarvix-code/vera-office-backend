import api from './api'

export interface CriticalAlert {
  id: number
  title: string
  description: string
  icon: string
  route: string
}

export interface Warning {
  id: number
  title: string
  description: string
  icon: string
  route: string
}

export interface DashboardStats {
  new_documents: number
  unclassified: number
  storage_used: number
  storage_total: number
  storage_percent: number
  total_documents: number
}

export interface RecentActivity {
  id: number
  title: string
  description: string
  icon: string
  color: string
  time: string
}

export interface DashboardData {
  critical_alerts: CriticalAlert[]
  warnings: Warning[]
  stats: DashboardStats
  recent_activities: RecentActivity[]
}

export const dashboardApi = {
  async getData(): Promise<DashboardData> {
    const response = await api.get('/dashboard')
    return response.data
  }
}
