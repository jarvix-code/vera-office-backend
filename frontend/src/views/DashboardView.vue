<template>
  <q-page class="dashboard-page">
    <div class="dashboard-header">
      <h1 class="dashboard-title">Dashboard</h1>
      <p class="dashboard-subtitle">{{ greeting }}</p>
    </div>

    <!-- Alert Widgets (Kritisch) -->
    <div class="alerts-section" v-if="criticalAlerts.length > 0">
      <h2 class="section-title">🔴 Handlungsbedarf</h2>
      <div class="alerts-grid">
        <div v-for="alert in criticalAlerts" :key="alert.id" class="alert-card critical">
          <div class="alert-icon">
            <q-icon :name="alert.icon" size="32px" color="white" />
          </div>
          <div class="alert-content">
            <div class="alert-title">{{ alert.title }}</div>
            <div class="alert-description">{{ alert.description }}</div>
          </div>
          <q-btn flat round icon="arrow_forward" color="white" @click="handleAlertClick(alert)" />
        </div>
      </div>
    </div>

    <!-- Warning Widgets (Wichtig) -->
    <div class="warnings-section" v-if="warnings.length > 0">
      <h2 class="section-title">🟡 Bald fällig</h2>
      <div class="warnings-grid">
        <div v-for="warning in warnings" :key="warning.id" class="alert-card warning">
          <div class="alert-icon">
            <q-icon :name="warning.icon" size="28px" color="white" />
          </div>
          <div class="alert-content">
            <div class="alert-title">{{ warning.title }}</div>
            <div class="alert-description">{{ warning.description }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Info Widgets -->
    <div class="info-section">
      <h2 class="section-title">📊 Überblick</h2>
      <div class="info-grid">
        <!-- Neue Dokumente -->
        <div class="info-card">
          <div class="info-header">
            <div class="info-icon" style="background: #0EA5A0;">
              <q-icon name="insert_drive_file" size="24px" color="white" />
            </div>
            <div class="info-title">Neue Dokumente</div>
          </div>
          <div class="info-value">{{ stats.newDocuments }}</div>
          <div class="info-label">Letzte 7 Tage</div>
          <q-linear-progress :value="0.7" color="teal" class="q-mt-sm" />
        </div>

        <!-- Unklassifiziert -->
        <div class="info-card">
          <div class="info-header">
            <div class="info-icon" style="background: #F59E0B;">
              <q-icon name="help_outline" size="24px" color="white" />
            </div>
            <div class="info-title">Unklassifiziert</div>
          </div>
          <div class="info-value">{{ stats.unclassified }}</div>
          <div class="info-label">Warten auf Kategorisierung</div>
          <q-btn flat dense color="amber-8" label="Jetzt klassifizieren" class="q-mt-sm" @click="goToUnclassified" />
        </div>

        <!-- Speicherplatz -->
        <div class="info-card">
          <div class="info-header">
            <div class="info-icon" style="background: #6366F1;">
              <q-icon name="storage" size="24px" color="white" />
            </div>
            <div class="info-title">Speicherplatz</div>
          </div>
          <div class="info-value">{{ stats.storageUsed }} GB</div>
          <div class="info-label">von {{ stats.storageTotal }} GB</div>
          <q-linear-progress :value="stats.storagePercent / 100" :color="stats.storagePercent > 80 ? 'red' : 'indigo'" class="q-mt-sm" />
        </div>

        <!-- Gesamt Dokumente -->
        <div class="info-card">
          <div class="info-header">
            <div class="info-icon" style="background: #2E3B8E;">
              <q-icon name="folder" size="24px" color="white" />
            </div>
            <div class="info-title">Gesamt Dokumente</div>
          </div>
          <div class="info-value">{{ stats.totalDocuments }}</div>
          <div class="info-label">In allen Kategorien</div>
        </div>
      </div>
    </div>

    <!-- Letzte Aktivitäten -->
    <div class="activity-section">
      <h2 class="section-title">🕐 Letzte Aktivitäten</h2>
      <q-list bordered separator class="activity-list">
        <q-item v-for="activity in recentActivities" :key="activity.id" clickable @click="handleActivityClick(activity)">
          <q-item-section avatar>
            <q-avatar :color="activity.color" text-color="white">
              <q-icon :name="activity.icon" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ activity.title }}</q-item-label>
            <q-item-label caption>{{ activity.description }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-item-label caption>{{ activity.time }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/services/api'

const router = useRouter()

// Greeting based on time
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Guten Morgen! ☀️'
  if (hour < 18) return 'Guten Tag! 👋'
  return 'Guten Abend! 🌙'
})

// Data loaded from API
const criticalAlerts = ref([])
const warnings = ref([])
const stats = ref({
  newDocuments: 0,
  unclassified: 0,
  storageUsed: 0,
  storageTotal: 512,
  storagePercent: 0,
  totalDocuments: 0
})
const recentActivities = ref([])

function handleAlertClick(alert: any) {
  if (alert.route) router.push(alert.route)
}

function handleActivityClick(activity: any) {
  // TODO: Open document detail
  console.log('Activity clicked:', activity)
}

function goToUnclassified() {
  router.push('/documents?filter=unclassified')
}

onMounted(async () => {
  try {
    const data = await dashboardApi.getData()
    criticalAlerts.value = data.critical_alerts
    warnings.value = data.warnings
    stats.value = {
      newDocuments: data.stats.new_documents,
      unclassified: data.stats.unclassified,
      storageUsed: data.stats.storage_used,
      storageTotal: data.stats.storage_total,
      storagePercent: data.stats.storage_percent,
      totalDocuments: data.stats.total_documents
    }
    recentActivities.value = data.recent_activities
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})
</script>

<style scoped lang="scss">
$teal: #0EA5A0;
$navy: #2E3B8E;
$red: #EF4444;
$amber: #F59E0B;

.dashboard-page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
  background: #F4F6F8;
}

.dashboard-header {
  margin-bottom: 32px;
}

.dashboard-title {
  font-size: 32px;
  font-weight: 700;
  color: #1F2937;
  margin-bottom: 4px;
}

.dashboard-subtitle {
  font-size: 16px;
  color: #6B7280;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1F2937;
  margin-bottom: 16px;
}

.alerts-section, .warnings-section, .info-section, .activity-section {
  margin-bottom: 32px;
}

.alerts-grid, .warnings-grid {
  display: grid;
  gap: 16px;
}

.alert-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }

  &.critical {
    background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
    color: white;

    .alert-title { color: white; font-weight: 700; }
    .alert-description { color: rgba(255, 255, 255, 0.9); }
  }

  &.warning {
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    color: white;

    .alert-title { color: white; font-weight: 700; }
    .alert-description { color: rgba(255, 255, 255, 0.9); }
  }
}

.alert-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alert-description {
  font-size: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.info-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #6B7280;
}

.info-value {
  font-size: 32px;
  font-weight: 700;
  color: #1F2937;
  margin-bottom: 4px;
}

.info-label {
  font-size: 12px;
  color: #9CA3AF;
}

.activity-list {
  background: white;
  border-radius: 12px;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
