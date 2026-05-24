<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">📊 Finanzen Dashboard</div>

    <!-- Period Selector -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-3">
        <q-input v-model="periodStart" label="Von" outlined dense type="date" @change="loadData" />
      </div>
      <div class="col-12 col-md-3">
        <q-input v-model="periodEnd" label="Bis" outlined dense type="date" @change="loadData" />
      </div>
      <div class="col-auto">
        <q-btn unelevated color="primary" label="Aktualisieren" @click="loadData" />
      </div>
    </div>

    <div v-if="store.loading">
      <div class="row q-col-gutter-md">
        <div v-for="i in 3" :key="i" class="col-12 col-md-4">
          <q-card flat bordered><q-card-section><q-skeleton type="rect" height="80px" /></q-card-section></q-card>
        </div>
      </div>
    </div>

    <template v-else-if="store.dashboard">
      <!-- KPI Cards -->
      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Umsatz</div>
              <div class="text-h3 text-positive">{{ formatCurrency(store.dashboard.total_revenue) }}</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Ausgaben</div>
              <div class="text-h3 text-negative">{{ formatCurrency(store.dashboard.total_expenses) }}</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Gewinn</div>
              <div class="text-h3" :class="store.dashboard.total_profit >= 0 ? 'text-positive' : 'text-negative'">
                {{ formatCurrency(store.dashboard.total_profit) }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Periodenvergleich -->
      <q-card v-if="store.dashboard.comparison" flat bordered class="q-mb-lg">
        <q-card-section>
          <div class="text-h6 q-mb-md">Periodenvergleich</div>
          <div class="row q-col-gutter-md items-center">
            <div class="col">
              <div class="text-caption">Vorperiode</div>
              <div class="text-h5">{{ formatCurrency(store.dashboard.comparison.previous) }}</div>
            </div>
            <div class="col-auto">
              <q-icon :name="store.dashboard.comparison.delta >= 0 ? 'trending_up' : 'trending_down'"
                :color="store.dashboard.comparison.delta >= 0 ? 'green' : 'red'" size="48px" />
            </div>
            <div class="col">
              <div class="text-caption">Aktuelle Periode</div>
              <div class="text-h5">{{ formatCurrency(store.dashboard.comparison.current) }}</div>
            </div>
            <div class="col">
              <div class="text-caption">Veränderung</div>
              <div class="text-h5" :class="store.dashboard.comparison.delta >= 0 ? 'text-positive' : 'text-negative'">
                {{ store.dashboard.comparison.delta >= 0 ? '+' : '' }}{{ store.dashboard.comparison.delta_pct.toFixed(1) }}%
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Monthly Chart (Bar-style with Quasar) -->
      <q-card flat bordered class="q-mb-lg">
        <q-card-section>
          <div class="text-h6 q-mb-md">Monatliche Übersicht</div>
          <div v-for="month in store.dashboard.monthly" :key="month.month" class="q-mb-sm">
            <div class="row items-center">
              <div class="col-2 text-caption">{{ month.month }}</div>
              <div class="col">
                <div class="row q-col-gutter-xs">
                  <div class="col-6">
                    <q-linear-progress :value="month.revenue / maxMonthly" color="green" size="24px">
                      <div class="absolute-full flex flex-center text-caption text-white">{{ formatCurrency(month.revenue) }}</div>
                    </q-linear-progress>
                  </div>
                  <div class="col-6">
                    <q-linear-progress :value="month.expenses / maxMonthly" color="red" size="24px">
                      <div class="absolute-full flex flex-center text-caption text-white">{{ formatCurrency(month.expenses) }}</div>
                    </q-linear-progress>
                  </div>
                </div>
              </div>
              <div class="col-2 text-right" :class="month.profit >= 0 ? 'text-positive' : 'text-negative'">
                {{ formatCurrency(month.profit) }}
              </div>
            </div>
          </div>
          <div class="row q-mt-sm">
            <div class="col-2"></div>
            <div class="col">
              <div class="row q-col-gutter-xs text-center text-caption text-grey-6">
                <div class="col-6">🟢 Umsatz</div>
                <div class="col-6">🔴 Ausgaben</div>
              </div>
            </div>
            <div class="col-2 text-right text-caption text-grey-6">Gewinn</div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Categories & Top Partners -->
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-h6 q-mb-md">Kategorien</div>
              <q-list dense>
                <q-item v-for="cat in store.dashboard.categories" :key="cat.category">
                  <q-item-section>{{ cat.category || 'Ohne Kategorie' }}</q-item-section>
                  <q-item-section side>{{ formatCurrency(cat.amount) }}</q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-h6 q-mb-md">Top Lieferanten</div>
              <q-list dense>
                <q-item v-for="s in store.dashboard.top_suppliers" :key="s.name">
                  <q-item-section>{{ s.name }}</q-item-section>
                  <q-item-section side>{{ formatCurrency(s.amount) }}</q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-h6 q-mb-md">Top Kunden</div>
              <q-list dense>
                <q-item v-for="c in store.dashboard.top_customers" :key="c.name">
                  <q-item-section>{{ c.name }}</q-item-section>
                  <q-item-section side>{{ formatCurrency(c.amount) }}</q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useErpStore } from '@/stores/erp'

const store = useErpStore()

const now = new Date()
const periodStart = ref(`${now.getFullYear()}-01-01`)
const periodEnd = ref(now.toISOString().slice(0, 10))

const maxMonthly = computed(() => {
  if (!store.dashboard?.monthly) return 1
  return Math.max(...store.dashboard.monthly.flatMap((m: any) => [m.revenue, m.expenses]), 1)
})

onMounted(() => loadData())

function loadData() {
  store.fetchDashboard(periodStart.value, periodEnd.value)
}

function formatCurrency(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}
</script>
