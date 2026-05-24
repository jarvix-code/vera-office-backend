<template>
  <q-btn
    v-if="questionId"
    flat
    dense
    no-caps
    color="primary"
    class="requirements-link touch-btn-sm"
    @click="showDialog = true"
  >
    <q-icon name="description" size="18px" class="q-mr-xs" />
    📄 BLZK-Dokument
  </q-btn>

  <q-dialog v-model="showDialog" position="bottom" full-width>
    <q-card style="max-height: 70vh">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">BLZK-Anforderungen</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup class="touch-btn-sm" />
      </q-card-section>

      <q-card-section v-if="loading" class="text-center q-pa-xl">
        <q-spinner-dots size="40px" color="primary" />
      </q-card-section>

      <q-card-section v-else-if="requirement" class="q-pt-sm">
        <q-badge color="blue-grey" class="q-mb-md">
          {{ requirement.section }}
        </q-badge>

        <div class="text-subtitle2 q-mt-md q-mb-sm">Anforderungen:</div>
        <q-list dense>
          <q-item v-for="(req, i) in requirement.requirements" :key="i">
            <q-item-section avatar>
              <q-icon name="check_circle" color="positive" size="20px" />
            </q-item-section>
            <q-item-section>{{ req }}</q-item-section>
          </q-item>
        </q-list>

        <div v-if="requirement.action_items?.length" class="q-mt-md">
          <div class="text-subtitle2 q-mb-sm">Was ist zu tun:</div>
          <q-list dense>
            <q-item v-for="(item, i) in requirement.action_items" :key="i">
              <q-item-section avatar>
                <q-icon name="arrow_forward" color="orange" size="20px" />
              </q-item-section>
              <q-item-section>{{ item }}</q-item-section>
            </q-item>
          </q-list>
        </div>

        <div class="text-caption text-grey-7 q-mt-md">
          Quelle: {{ requirement.pdf }}, Seite {{ requirement.page }}
          <span v-if="requirement.blzk_code"> · Code: {{ requirement.blzk_code }}</span>
        </div>
      </q-card-section>

      <q-card-section v-else class="text-center text-grey-5">
        Keine Anforderungen für diese Frage gefunden.
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { qmApi } from '@/services/qm-api'

const props = defineProps<{
  questionId: string
}>()

const showDialog = ref(false)
const loading = ref(false)
const requirement = ref<any>(null)

watch(showDialog, async (val) => {
  if (val && !requirement.value) {
    loading.value = true
    try {
      requirement.value = await qmApi.getBLZKRequirement(props.questionId)
    } catch {
      requirement.value = null
    } finally {
      loading.value = false
    }
  }
})
</script>

<style scoped>
.requirements-link {
  font-size: 14px;
}

.touch-btn-sm {
  min-height: 40px;
  min-width: 40px;
}
</style>
