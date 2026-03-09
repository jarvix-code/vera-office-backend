<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">📄 Betriebswirtschaftliche Auswertung</div>

    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-3">
        <q-input v-model="start" label="Von" outlined dense type="date" />
      </div>
      <div class="col-12 col-md-3">
        <q-input v-model="end" label="Bis" outlined dense type="date" />
      </div>
      <div class="col-auto">
        <q-btn unelevated color="primary" label="Berechnen" @click="loadData" />
      </div>
    </div>

    <q-table
      v-if="store.bwa"
      :rows="store.bwa.rows"
      :columns="columns"
      row-key="label"
      flat bordered
      hide-pagination
      :rows-per-page-options="[0]"
      :loading="store.loading"
    >
      <template v-slot:body-cell-current="props">
        <q-td :props="props" :class="props.row.current < 0 ? 'text-negative' : ''">
          {{ formatCurrency(props.row.current) }}
        </q-td>
      </template>
      <template v-slot:body-cell-previous="props">
        <q-td :props="props" :class="(props.row.previous || 0) < 0 ? 'text-negative' : 'text-grey-7'">
          {{ props.row.previous != null ? formatCurrency(props.row.previous) : '—' }}
        </q-td>
      </template>
      <template v-slot:body-cell-delta="props">
        <q-td :props="props">
          <template v-if="props.row.delta != null">
            <span :class="props.row.delta >= 0 ? 'text-positive' : 'text-negative'">
              {{ props.row.delta >= 0 ? '+' : '' }}{{ formatCurrency(props.row.delta) }}
            </span>
            <span v-if="props.row.delta_pct != null" class="text-caption q-ml-xs">
              ({{ props.row.delta_pct >= 0 ? '+' : '' }}{{ props.row.delta_pct.toFixed(1) }}%)
            </span>
          </template>
          <span v-else>—</span>
        </q-td>
      </template>
    </q-table>

    <div v-if="store.bwa" class="text-caption text-grey-7 q-mt-md">
      Periode: {{ store.bwa.period_start }} bis {{ store.bwa.period_end }}
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useErpStore } from '@/stores/erp'

const store = useErpStore()

const now = new Date()
const start = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`)
const end = ref(now.toISOString().slice(0, 10))

const columns = [
  { name: 'label', label: 'Position', field: 'label', align: 'left' as const, style: 'font-weight: 600;' },
  { name: 'current', label: 'Aktuelle Periode', field: 'current', align: 'right' as const },
  { name: 'previous', label: 'Vorperiode', field: 'previous', align: 'right' as const },
  { name: 'delta', label: 'Veränderung', field: 'delta', align: 'right' as const }
]

onMounted(() => loadData())

function loadData() {
  store.fetchBWA(start.value, end.value)
}

function formatCurrency(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}
</script>
