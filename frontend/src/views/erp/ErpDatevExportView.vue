<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg">📤 DATEV-Export</div>

    <q-card flat bordered class="q-mb-lg">
      <q-card-section>
        <div class="text-h6 q-mb-md">Export-Parameter</div>

        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <q-input v-model="start" label="Von" outlined type="date" />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model="end" label="Bis" outlined type="date" />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model.number="beraterNr" label="Berater-Nr." outlined type="number" />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model.number="mandantenNr" label="Mandanten-Nr." outlined type="number" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-6">
        <q-card flat bordered class="cursor-pointer hover-card" @click="exportDATEV">
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="account_balance" size="64px" color="primary" />
            <div class="text-h5 q-mt-md">DATEV Buchungsstapel</div>
            <div class="text-caption text-grey-7">Format: EXTF v700, SKR03, cp1252</div>
            <q-btn unelevated color="primary" label="Exportieren" class="q-mt-md" icon="download"
              :loading="exporting === 'datev'" :disable="!beraterNr || !mandantenNr" />
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card flat bordered class="cursor-pointer hover-card" @click="exportCSV">
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="table_chart" size="64px" color="green" />
            <div class="text-h5 q-mt-md">CSV-Export</div>
            <div class="text-caption text-grey-7">Semikolon-getrennt, UTF-8</div>
            <q-btn unelevated color="green" label="Exportieren" class="q-mt-md" icon="download"
              :loading="exporting === 'csv'" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Hinweise</div>
        <q-list dense>
          <q-item>
            <q-item-section avatar><q-icon name="info" color="blue" /></q-item-section>
            <q-item-section>DATEV-Export nutzt SKR03 Kontenrahmen</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar><q-icon name="info" color="blue" /></q-item-section>
            <q-item-section>Berater- und Mandanten-Nr. erhalten Sie von Ihrem Steuerberater</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar><q-icon name="warning" color="amber" /></q-item-section>
            <q-item-section>Bitte prüfen Sie den Export vor dem Import in DATEV</q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { erpApi } from '@/services/erp-api'
import { Notify } from 'quasar'

const now = new Date()
const start = ref(`${now.getFullYear()}-01-01`)
const end = ref(now.toISOString().slice(0, 10))
const beraterNr = ref<number | null>(null)
const mandantenNr = ref<number | null>(null)
const exporting = ref<string | null>(null)

async function exportDATEV() {
  if (!beraterNr.value || !mandantenNr.value) return
  exporting.value = 'datev'
  try {
    await erpApi.downloadDATEV(start.value, end.value, beraterNr.value, mandantenNr.value)
    Notify.create({ type: 'positive', message: 'DATEV-Export heruntergeladen' })
  } catch {
    Notify.create({ type: 'negative', message: 'Export fehlgeschlagen' })
  } finally {
    exporting.value = null
  }
}

async function exportCSV() {
  exporting.value = 'csv'
  try {
    await erpApi.downloadCSV(start.value, end.value)
    Notify.create({ type: 'positive', message: 'CSV-Export heruntergeladen' })
  } catch {
    Notify.create({ type: 'negative', message: 'Export fehlgeschlagen' })
  } finally {
    exporting.value = null
  }
}
</script>

<style scoped>
.hover-card { transition: box-shadow 0.2s, transform 0.2s; }
.hover-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.12); transform: translateY(-2px); }
</style>
