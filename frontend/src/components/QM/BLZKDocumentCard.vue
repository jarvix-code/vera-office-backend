<template>
  <q-card flat bordered class="blzk-doc-card">
    <q-card-section>
      <div class="row items-center q-mb-sm">
        <q-badge :color="typColor" class="q-mr-sm">Typ {{ doc.typ }}</q-badge>
        <span class="text-caption text-grey-7">{{ doc.code }}</span>
        <q-space />
        <q-icon
          v-if="doc.turnus?.includes('täglich')"
          name="today"
          color="red"
          size="20px"
        >
          <q-tooltip>Tägliche Aufgabe</q-tooltip>
        </q-icon>
      </div>

      <div class="text-subtitle1 text-weight-medium doc-title">
        {{ doc.name }}
      </div>

      <div class="text-caption text-grey-7 q-mt-xs">
        <q-icon name="schedule" size="14px" class="q-mr-xs" />
        {{ doc.turnus }}
      </div>

      <div v-if="doc.beschreibung" class="text-caption q-mt-sm">
        {{ doc.beschreibung }}
      </div>
    </q-card-section>

    <q-separator />

    <q-card-actions class="q-pa-sm">
      <q-chip
        v-for="sd in (doc.stammdaten || [])"
        :key="sd"
        size="sm"
        :icon="stammdatenIcon(sd)"
        :label="sd"
        dense
      />
      <q-space />
      <q-btn
        v-if="showDownload"
        flat
        dense
        icon="download"
        color="primary"
        class="touch-btn-sm"
        @click="$emit('download', doc)"
      >
        <q-tooltip>PDF herunterladen</q-tooltip>
      </q-btn>
      <q-btn
        flat
        dense
        icon="info"
        color="grey-7"
        class="touch-btn-sm"
        @click="$emit('details', doc)"
      >
        <q-tooltip>Details anzeigen</q-tooltip>
      </q-btn>
    </q-card-actions>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface BLZKDoc {
  code: string
  kapitel: string
  kapitel_name: string
  name: string
  typ: string
  turnus: string
  stammdaten: string[]
  beschreibung?: string
}

const props = defineProps<{
  doc: BLZKDoc
  showDownload?: boolean
}>()

defineEmits<{
  (e: 'download', doc: BLZKDoc): void
  (e: 'details', doc: BLZKDoc): void
}>()

const typColor = computed(() => {
  return props.doc.typ === 'A' ? 'blue' : props.doc.typ === 'B' ? 'orange' : 'green'
})

function stammdatenIcon(sd: string): string {
  const map: Record<string, string> = {
    praxis: 'business',
    personal: 'people',
    geraete: 'precision_manufacturing',
  }
  return map[sd] || 'description'
}
</script>

<style scoped>
.blzk-doc-card {
  transition: box-shadow 0.2s;
}

.blzk-doc-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.doc-title {
  line-height: 1.3;
}

.touch-btn-sm {
  min-height: 40px;
  min-width: 40px;
}
</style>
