<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <div class="text-h4">🧼 Hygiene-Checklisten</div>
      <q-space />
      <q-btn unelevated color="primary" icon="add" label="Neues Protokoll" @click="showCreate = true" />
    </div>

    <!-- Liste -->
    <q-table
      :rows="store.hygieneProtocols"
      :columns="columns"
      row-key="id"
      :loading="store.loading"
      flat bordered
      @row-click="(_evt: Event, row: any) => openProtocol(row.id)"
      class="cursor-pointer"
    >
      <template v-slot:body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="props.row.status === 'abgeschlossen' ? 'green' : 'orange'">
            {{ props.row.status === 'abgeschlossen' ? 'Abgeschlossen' : 'Offen' }}
          </q-badge>
        </q-td>
      </template>
      <template v-slot:body-cell-progress="props">
        <q-td :props="props">
          <q-linear-progress
            :value="checkedCount(props.row) / props.row.checklist.length"
            size="20px"
            :color="checkedCount(props.row) === props.row.checklist.length ? 'green' : 'blue'"
          >
            <div class="absolute-full flex flex-center">
              <span class="text-caption text-white">{{ checkedCount(props.row) }}/{{ props.row.checklist.length }}</span>
            </div>
          </q-linear-progress>
        </q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat round dense icon="delete" color="negative" @click.stop="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Detail Dialog -->
    <q-dialog v-model="showDetail" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card v-if="store.currentHygiene">
        <q-bar class="bg-blue text-white">
          <div class="text-weight-bold">{{ store.currentHygiene.title }}</div>
          <q-space />
          <q-badge color="white" :text-color="store.currentHygiene.status === 'abgeschlossen' ? 'green' : 'orange'">
            {{ store.currentHygiene.status === 'abgeschlossen' ? '✅ Abgeschlossen' : '⏳ Offen' }}
          </q-badge>
          <q-btn dense flat icon="close" v-close-popup class="q-ml-sm" />
        </q-bar>

        <q-card-section class="q-pa-lg">
          <div v-if="store.currentHygiene.area" class="text-subtitle1 text-grey-7 q-mb-md">
            📍 Bereich: {{ store.currentHygiene.area }}
          </div>

          <q-list bordered separator>
            <q-item v-for="(item, idx) in store.currentHygiene.checklist" :key="idx" :class="item.checked ? 'bg-green-1' : ''">
              <q-item-section side>
                <q-checkbox
                  :model-value="item.checked"
                  @update:model-value="(val: boolean) => toggleItem(item, val)"
                  :disable="store.currentHygiene.status === 'abgeschlossen'"
                  color="green"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label :class="item.checked ? 'text-strike text-grey-6' : ''">
                  {{ item.item }}
                </q-item-label>
                <q-item-label v-if="item.timestamp" caption>
                  ✅ {{ new Date(item.timestamp).toLocaleString('de-DE') }}
                </q-item-label>
                <q-item-label v-if="item.notes" caption class="text-italic">📝 {{ item.notes }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <div v-if="store.currentHygiene.closed_at" class="q-mt-lg text-center text-positive">
            <q-icon name="check_circle" size="48px" />
            <div class="text-h6">Abgeschlossen am {{ new Date(store.currentHygiene.closed_at).toLocaleString('de-DE') }}</div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Create Dialog -->
    <q-dialog v-model="showCreate">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Neues Hygiene-Protokoll</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="newProtocol.title" label="Titel" outlined class="q-mb-md" />
          <q-input v-model="newProtocol.area" label="Bereich (optional)" outlined placeholder="z.B. Behandlungsraum 1" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Abbrechen" v-close-popup />
          <q-btn unelevated color="primary" label="Erstellen" @click="create" :loading="creating" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQmStore } from '@/stores/qm'
import { Notify, useQuasar } from 'quasar'

const store = useQmStore()
const $q = useQuasar()

const showCreate = ref(false)
const showDetail = ref(false)
const creating = ref(false)
const newProtocol = ref({ title: '', area: '' })

const columns = [
  { name: 'title', label: 'Titel', field: 'title', align: 'left' as const, sortable: true },
  { name: 'area', label: 'Bereich', field: 'area', align: 'left' as const },
  { name: 'status', label: 'Status', field: 'status', align: 'center' as const },
  { name: 'progress', label: 'Fortschritt', field: 'id', align: 'center' as const },
  { name: 'created_at', label: 'Erstellt', field: (row: any) => new Date(row.created_at).toLocaleDateString('de-DE'), align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const }
]

onMounted(() => store.fetchHygiene())

function checkedCount(row: any): number {
  return row.checklist.filter((i: any) => i.checked).length
}

async function openProtocol(id: number) {
  await store.fetchHygieneDetail(id)
  showDetail.value = true
}

async function toggleItem(item: any, checked: boolean) {
  if (!store.currentHygiene) return
  await store.checkHygieneItem(store.currentHygiene.id, { item: item.item, checked })
}

async function create() {
  if (!newProtocol.value.title) return
  creating.value = true
  try {
    await store.createHygiene(newProtocol.value)
    showCreate.value = false
    newProtocol.value = { title: '', area: '' }
    Notify.create({ type: 'positive', message: 'Hygiene-Protokoll erstellt' })
  } finally {
    creating.value = false
  }
}

function confirmDelete(protocol: any) {
  $q.dialog({
    title: 'Protokoll löschen',
    message: `"${protocol.title}" wirklich löschen?`,
    cancel: true, persistent: true
  }).onOk(async () => {
    await store.deleteHygiene(protocol.id)
    Notify.create({ type: 'info', message: 'Protokoll gelöscht' })
  })
}
</script>
