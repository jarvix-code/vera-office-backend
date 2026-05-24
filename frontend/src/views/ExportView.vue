<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Export</div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">Dokumente exportieren</div>
            
            <q-select
              outlined
              label="Export-Format"
              :options="['PDF', 'ZIP-Archiv', 'CSV-Liste']"
              class="q-mb-md"
            />

            <q-select
              outlined
              label="Zeitraum"
              :options="['Letzte 7 Tage', 'Letzter Monat', 'Letztes Jahr', 'Alle']"
              class="q-mb-md"
            />

            <q-btn
              unelevated
              color="primary"
              icon="download"
              label="Export starten"
              class="full-width"
              @click="startExport"
            />
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-md">Automatische Backups</div>
            
            <q-toggle
              label="Tägliches Backup aktivieren"
              class="q-mb-md"
            />

            <q-input
              outlined
              label="Backup-Pfad"
              placeholder="Z.B. \\server\backups"
              class="q-mb-md"
            />

            <q-btn
              unelevated
              color="secondary"
              icon="save"
              label="Einstellungen speichern"
              class="full-width"
            />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="text-caption text-grey-5 text-center q-mt-xl">
      (Vollständige Export-Funktionen in Entwicklung)
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { Notify } from 'quasar'

function startExport() {
  Notify.create({
    type: 'info',
    message: 'Export-Funktion wird vorbereitet...'
  })
}
</script>
