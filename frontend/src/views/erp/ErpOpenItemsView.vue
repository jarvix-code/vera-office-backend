<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">💰 Offene Posten</div>

    <!-- Filter -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-4">
        <q-select v-model="filterDirection" label="Richtung" outlined dense clearable
          :options="[{ label: 'Eingangsrechnungen', value: 'incoming' }, { label: 'Ausgangsrechnungen', value: 'outgoing' }]"
          emit-value map-options @update:model-value="loadData" />
      </div>
    </div>

    <!-- Summary -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption">Gesamt offen</div>
            <div class="text-h4">{{ formatCurrency(totalOpen) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered class="bg-red-1">
          <q-card-section>
            <div class="text-caption text-negative">Überfällig</div>
            <div class="text-h4 text-negative">{{ formatCurrency(totalOverdue) }}</div>
            <div class="text-caption">{{ overdueCount }} Posten</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered class="bg-amber-1">
          <q-card-section>
            <div class="text-caption text-warning">Bald fällig (≤7 Tage)</div>
            <div class="text-h4 text-warning">{{ formatCurrency(totalSoonDue) }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Table -->
    <q-table
      :rows="store.openItems"
      :columns="columns"
      row-key="id"
      :loading="store.loading"
      flat bordered
    >
      <template v-slot:body-cell-status_color="props">
        <q-td :props="props">
          <q-badge :color="props.row.status_color === 'red' ? 'red' : props.row.status_color === 'yellow' ? 'amber' : 'green'">
            {{ props.row.status_color === 'red' ? '🔴 Überfällig' : props.row.status_color === 'yellow' ? '🟡 Bald fällig' : '🟢 OK' }}
          </q-badge>
        </q-td>
      </template>
      <template v-slot:body-cell-direction="props">
        <q-td :props="props">
          <q-chip dense :color="props.row.direction === 'incoming' ? 'orange' : 'blue'" text-color="white" size="sm">
            {{ props.row.direction === 'incoming' ? '📥 Eingang' : '📤 Ausgang' }}
          </q-chip>
        </q-td>
      </template>
      <template v-slot:body-cell-gross_amount="props">
        <q-td :props="props" class="text-weight-bold">
          {{ formatCurrency(props.row.gross_amount) }}
        </q-td>
      </template>
      <template v-slot:body-cell-days_until_due="props">
        <q-td :props="props" :class="(props.row.days_until_due ?? 0) < 0 ? 'text-negative text-weight-bold' : ''">
          {{ props.row.days_until_due != null ? `${props.row.days_until_due} Tage` : '—' }}
        </q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat dense round icon="check_circle" color="green"
            @click="markPaid(props.row)" />
        </q-td>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useErpStore } from '@/stores/erp'
import { Notify } from 'quasar'

const store = useErpStore()
const filterDirection = ref<string | null>(null)

const columns = [
  { name: 'status_color', label: 'Ampel', field: 'status_color', align: 'center' as const },
  { name: 'direction', label: 'Richtung', field: 'direction', align: 'center' as const },
  { name: 'invoice_number', label: 'Rechnungsnr.', field: (r: any) => r.invoice_number || '—', align: 'left' as const },
  { name: 'counterparty', label: 'Geschäftspartner', field: (r: any) => r.counterparty || '—', align: 'left' as const },
  { name: 'invoice_date', label: 'Rechnungsdatum', field: 'invoice_date', align: 'left' as const, sortable: true },
  { name: 'due_date', label: 'Fällig am', field: (r: any) => r.due_date || '—', align: 'left' as const, sortable: true },
  { name: 'gross_amount', label: 'Betrag', field: 'gross_amount', align: 'right' as const, sortable: true },
  { name: 'days_until_due', label: 'Tage', field: 'days_until_due', align: 'right' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const }
]

const totalOpen = computed(() => store.openItems.reduce((s: number, i: any) => s + i.gross_amount, 0))
const totalOverdue = computed(() => store.openItems.filter((i: any) => i.status_color === 'red').reduce((s: number, i: any) => s + i.gross_amount, 0))
const overdueCount = computed(() => store.openItems.filter((i: any) => i.status_color === 'red').length)
const totalSoonDue = computed(() => store.openItems.filter((i: any) => i.status_color === 'yellow').reduce((s: number, i: any) => s + i.gross_amount, 0))

onMounted(() => loadData())

function loadData() {
  store.fetchOpenItems(filterDirection.value || undefined)
}

async function markPaid(item: any) {
  await store.updateItem(item.id, {
    payment_status: 'paid',
    payment_date: new Date().toISOString().slice(0, 10)
  })
  Notify.create({ type: 'positive', message: 'Als bezahlt markiert' })
  loadData()
}

function formatCurrency(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}
</script>
