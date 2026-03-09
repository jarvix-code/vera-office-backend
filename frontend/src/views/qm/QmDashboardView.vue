<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">📋 QM Dashboard</div>

    <div v-if="store.loading" class="row q-col-gutter-md">
      <div v-for="i in 4" :key="i" class="col-12 col-md-3">
        <q-card flat bordered><q-card-section><q-skeleton type="rect" height="80px" /></q-card-section></q-card>
      </div>
    </div>

    <template v-else-if="store.dashboard">
      <!-- KPI Cards -->
      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md-3">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Dokumente</div>
              <div class="text-h3 text-primary">{{ store.dashboard.total_documents }}</div>
              <div class="q-mt-sm">
                <q-badge v-for="(count, status) in store.dashboard.documents_by_status" :key="status"
                  :color="statusColor(status as string)" class="q-mr-xs">
                  {{ status }}: {{ count }}
                </q-badge>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Offene Audits</div>
              <div class="text-h3 text-orange">{{ store.dashboard.open_audits }}</div>
              <div class="text-caption">von {{ store.dashboard.total_audits }} gesamt</div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Offene Hygiene</div>
              <div class="text-h3 text-blue">{{ store.dashboard.open_hygiene }}</div>
              <div class="text-caption">von {{ store.dashboard.total_hygiene }} gesamt</div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Compliance-Rate</div>
              <div class="text-h3" :class="complianceColor">
                {{ store.dashboard.compliance_rate.toFixed(0) }}%
              </div>
              <q-badge :color="complianceBadgeColor" class="q-mt-sm">
                {{ complianceLabel }}
              </q-badge>
              <div v-if="store.dashboard.unfulfilled_compliance > 0" class="text-caption text-negative q-mt-xs">
                {{ store.dashboard.unfulfilled_compliance }} nicht erfüllt
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Compliance Ampel -->
      <q-card flat bordered class="q-mb-lg">
        <q-card-section>
          <div class="text-h6 q-mb-md">Compliance-Ampel</div>
          <div class="row items-center justify-center q-gutter-lg">
            <div class="text-center">
              <q-icon
                name="circle"
                size="80px"
                :color="store.dashboard.compliance_rate >= 80 ? 'green' : 'grey-4'"
              />
              <div class="text-caption q-mt-sm">≥ 80% Erfüllt</div>
            </div>
            <div class="text-center">
              <q-icon
                name="circle"
                size="80px"
                :color="store.dashboard.compliance_rate >= 50 && store.dashboard.compliance_rate < 80 ? 'amber' : 'grey-4'"
              />
              <div class="text-caption q-mt-sm">50–79%</div>
            </div>
            <div class="text-center">
              <q-icon
                name="circle"
                size="80px"
                :color="store.dashboard.compliance_rate < 50 ? 'red' : 'grey-4'"
              />
              <div class="text-caption q-mt-sm">&lt; 50%</div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Quick Links -->
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-4">
          <q-btn unelevated color="primary" class="full-width" size="lg" icon="menu_book" label="QM Handbuch" to="/qm/handbook" />
        </div>
        <div class="col-12 col-md-4">
          <q-btn unelevated color="orange" class="full-width" size="lg" icon="fact_check" label="Audits" to="/qm/audits" />
        </div>
        <div class="col-12 col-md-4">
          <q-btn unelevated color="blue" class="full-width" size="lg" icon="cleaning_services" label="Hygiene" to="/qm/hygiene" />
        </div>
      </div>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useQmStore } from '@/stores/qm'

const store = useQmStore()

onMounted(() => {
  store.fetchDashboard()
})

const complianceColor = computed(() => {
  if (!store.dashboard) return 'text-grey'
  const rate = store.dashboard.compliance_rate
  if (rate >= 80) return 'text-positive'
  if (rate >= 50) return 'text-warning'
  return 'text-negative'
})

const complianceBadgeColor = computed(() => {
  if (!store.dashboard) return 'grey'
  const rate = store.dashboard.compliance_rate
  if (rate >= 80) return 'green'
  if (rate >= 50) return 'amber'
  return 'red'
})

const complianceLabel = computed(() => {
  if (!store.dashboard) return ''
  const rate = store.dashboard.compliance_rate
  if (rate >= 80) return '✅ Konform'
  if (rate >= 50) return '⚠️ Teilweise'
  return '🔴 Kritisch'
})

function statusColor(status: string): string {
  const map: Record<string, string> = {
    'Entwurf': 'grey',
    'In Prüfung': 'orange',
    'Freigegeben': 'green',
    'Veraltet': 'amber',
    'Archiviert': 'blue-grey'
  }
  return map[status] || 'grey'
}
</script>
