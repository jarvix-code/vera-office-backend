<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">🧾 USt-Voranmeldung</div>

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

    <template v-if="store.ust">
      <!-- Summary -->
      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Umsatzsteuer (Ausgang)</div>
              <div class="text-h4 text-negative">{{ formatCurrency(store.ust.total_output_vat) }}</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-caption text-grey-7">Vorsteuer (Eingang)</div>
              <div class="text-h4 text-positive">{{ formatCurrency(store.ust.total_input_vat) }}</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-md-4">
          <q-card flat bordered class="bg-primary text-white">
            <q-card-section>
              <div class="text-caption" style="opacity: 0.8">Zahllast / Erstattung</div>
              <div class="text-h4">{{ formatCurrency(store.ust.total_balance) }}</div>
              <div class="text-caption">
                {{ store.ust.total_balance > 0 ? '→ Ans Finanzamt zu zahlen' : '→ Erstattung vom Finanzamt' }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- By Rate -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-md">Aufschlüsselung nach Steuersatz</div>
        </q-card-section>
        <q-table
          :rows="store.ust.by_rate"
          :columns="rateColumns"
          row-key="rate"
          flat
          hide-pagination
          :rows-per-page-options="[0]"
        >
          <template v-slot:body-cell-rate="props">
            <q-td :props="props">
              <q-badge color="primary">{{ props.row.rate }}%</q-badge>
            </q-td>
          </template>
          <template v-slot:body-cell-balance="props">
            <q-td :props="props" :class="props.row.balance > 0 ? 'text-negative' : 'text-positive'">
              {{ formatCurrency(props.row.balance) }}
            </q-td>
          </template>
        </q-table>
      </q-card>

      <div class="text-caption text-grey-7 q-mt-md">
        Zeitraum: {{ store.ust.period_start }} bis {{ store.ust.period_end }}
      </div>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useErpStore } from '@/stores/erp'

const store = useErpStore()

const now = new Date()
const q = Math.floor(now.getMonth() / 3)
const qStart = new Date(now.getFullYear(), q * 3, 1)
const start = ref(qStart.toISOString().slice(0, 10))
const end = ref(now.toISOString().slice(0, 10))

const rateColumns = [
  { name: 'rate', label: 'Steuersatz', field: 'rate', align: 'center' as const },
  { name: 'output_vat', label: 'Umsatzsteuer', field: (r: any) => formatCurrency(r.output_vat), align: 'right' as const },
  { name: 'input_vat', label: 'Vorsteuer', field: (r: any) => formatCurrency(r.input_vat), align: 'right' as const },
  { name: 'balance', label: 'Saldo', field: 'balance', align: 'right' as const }
]

onMounted(() => loadData())

function loadData() {
  store.fetchUSt(start.value, end.value)
}

function formatCurrency(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}
</script>
