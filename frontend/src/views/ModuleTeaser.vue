<template>
  <q-page class="teaser-page flex flex-center">
    <div class="teaser-container">

      <!-- Hero Section -->
      <div class="teaser-hero text-center q-mb-xl">
        <div class="teaser-icon-wrapper q-mb-lg">
          <q-icon :name="moduleIcon" size="72px" class="teaser-icon" />
        </div>
        <div class="text-h3 text-weight-bold text-dark q-mb-sm">{{ moduleName }}</div>
        <div class="text-subtitle1 text-grey-6 teaser-description">{{ description }}</div>
      </div>

      <!-- Feature Cards -->
      <div class="row q-col-gutter-md q-mb-xl justify-center">
        <div
          v-for="(feature, idx) in features"
          :key="idx"
          class="col-12 col-sm-6 col-md-4"
        >
          <q-card flat bordered class="feature-card full-height">
            <q-card-section class="row items-start no-wrap q-pa-md">
              <q-icon name="check_circle" color="positive" size="20px" class="q-mr-sm q-mt-xs flex-shrink-0" />
              <span class="text-body2 text-dark">{{ feature }}</span>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Call to Action -->
      <div class="text-center">
        <q-card flat class="cta-card q-pa-lg">
          <q-icon name="lock_open" size="32px" class="text-primary q-mb-md" />
          <div class="text-h6 text-dark q-mb-xs">Modul noch nicht freigeschaltet</div>
          <div class="text-body2 text-grey-6 q-mb-lg">
            Kontaktieren Sie uns, um dieses Modul für Ihre Praxis zu aktivieren.
          </div>
          <q-btn
            unelevated
            color="primary"
            size="lg"
            icon="rocket_launch"
            label="Jetzt aktivieren"
            class="cta-btn q-px-xl"
            @click="goToSettings"
          />
        </q-card>
      </div>

    </div>
  </q-page>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  moduleName: string
  moduleIcon: string
  description: string
  features: string[]
}>()

const router = useRouter()

function goToSettings() {
  router.push('/settings')
}
</script>

<style scoped>
.teaser-page {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  min-height: 100vh;
  padding: 48px 16px;
}

.teaser-container {
  width: 100%;
  max-width: 860px;
}

.teaser-icon-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  border-radius: 32px;
  background: linear-gradient(135deg, #e8f4fd 0%, #dbeafe 100%);
  box-shadow: 0 8px 32px rgba(25, 118, 210, 0.15);
}

.teaser-icon {
  color: #1976d2;
}

.teaser-description {
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.6;
  font-size: 1.05rem;
}

.feature-card {
  border-radius: 12px;
  border-color: #e2e8f0 !important;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.feature-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.flex-shrink-0 {
  flex-shrink: 0;
}

.cta-card {
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  display: inline-block;
  min-width: 340px;
}

.cta-btn {
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
</style>
