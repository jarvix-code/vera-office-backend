<template>
  <q-page class="flex flex-center">
    <div class="text-center q-pa-xl">
      <q-icon name="construction" size="80px" color="grey-5" class="q-mb-lg" />
      <div class="text-h5 text-grey-7 q-mb-sm">{{ title }}</div>
      <div class="text-body1 text-grey-5">Dieser Bereich ist in Entwicklung.</div>
      <q-btn
        flat
        color="primary"
        label="Zurück"
        icon="arrow_back"
        class="q-mt-xl"
        @click="$router.back()"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || 'Coming Soon')
</script>
