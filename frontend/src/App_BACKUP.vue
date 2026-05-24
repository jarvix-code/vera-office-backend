<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="vera-header">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          aria-label="Menu"
          @click="drawer = !drawer"
        />
        <q-toolbar-title class="text-weight-bold" style="font-size: 1.1rem;">
          <span style="color: #7C3AED;">●</span> VERA Office
        </q-toolbar-title>
        <q-space />
        <q-btn flat round dense icon="dark_mode" @click="toggleDark" />
        <q-btn flat round dense icon="notifications" />
        <q-btn flat round dense icon="account_circle" />
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawer"
      show-if-above
      :width="280"
      :breakpoint="500"
      class="vera-sidebar"
    >
      <div class="q-pa-md q-mb-sm" style="border-bottom: 1px solid rgba(255,255,255,0.08);">
        <div class="text-h6 text-white text-weight-bold">
          <q-icon name="auto_awesome" color="purple-4" class="q-mr-sm" />
          VERA
        </div>
        <div class="text-caption" style="color: #64748B;">Intelligent Office Assistant</div>
      </div>

      <q-scroll-area class="fit" style="margin-top: -8px;">
        <q-list padding>
          <q-item
            v-for="item in coreMenuItems"
            :key="item.to"
            clickable v-ripple :to="item.to"
            active-class="q-router-link--active"
          >
            <q-item-section avatar><q-icon :name="item.icon" size="sm" /></q-item-section>
            <q-item-section><q-item-label>{{ item.label }}</q-item-label></q-item-section>
          </q-item>

          <template v-if="qmEnabled">
            <q-separator class="q-my-sm" />
            <q-item-label header class="text-caption" style="color: #64748B;">📋 Qualitätsmanagement</q-item-label>
            <q-item v-for="item in qmMenuItems" :key="item.to" clickable v-ripple :to="item.to" active-class="q-router-link--active">
              <q-item-section avatar><q-icon :name="item.icon" size="sm" /></q-item-section>
              <q-item-section><q-item-label>{{ item.label }}</q-item-label></q-item-section>
            </q-item>
          </template>

          <template v-if="erpEnabled">
            <q-separator class="q-my-sm" />
            <q-item-label header class="text-caption" style="color: #64748B;">📊 Finanzen</q-item-label>
            <q-item v-for="item in erpMenuItems" :key="item.to" clickable v-ripple :to="item.to" active-class="q-router-link--active">
              <q-item-section avatar><q-icon :name="item.icon" size="sm" /></q-item-section>
              <q-item-section><q-item-label>{{ item.label }}</q-item-label></q-item-section>
            </q-item>
          </template>

          <q-separator class="q-my-sm" />
          <q-item v-for="item in settingsMenuItems" :key="item.to" clickable v-ripple :to="item.to" active-class="q-router-link--active">
            <q-item-section avatar><q-icon :name="item.icon" size="sm" /></q-item-section>
            <q-item-section><q-item-label>{{ item.label }}</q-item-label></q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const drawer = ref(true)

const coreMenuItems = [
  { label: 'VERA Chat', icon: 'chat', to: '/' },
  { label: 'Dashboard', icon: 'dashboard', to: '/dashboard' },
  { label: 'Dokumente', icon: 'folder', to: '/documents' },
  { label: 'Erfassung', icon: 'camera_alt', to: '/capture' },
  { label: 'Suche', icon: 'search', to: '/search' },
  { label: 'Aufgaben', icon: 'assignment', to: '/tasks' },
]

const qmMenuItems = [
  { label: 'QM Dashboard', icon: 'checklist', to: '/qm' },
  { label: 'QM Handbuch', icon: 'menu_book', to: '/qm/handbook' },
  { label: 'Audits', icon: 'fact_check', to: '/qm/audits' },
  { label: 'Hygiene', icon: 'cleaning_services', to: '/qm/hygiene' },
  { label: 'Compliance', icon: 'verified', to: '/qm/compliance' },
]

const erpMenuItems = [
  { label: 'Finanzen', icon: 'account_balance', to: '/finanzen' },
  { label: 'BWA', icon: 'assessment', to: '/finanzen/bwa' },
  { label: 'USt-Voranmeldung', icon: 'receipt_long', to: '/finanzen/ust' },
  { label: 'Offene Posten', icon: 'payments', to: '/finanzen/offene-posten' },
  { label: 'DATEV-Export', icon: 'download', to: '/finanzen/datev' },
]

const settingsMenuItems = [
  { label: 'Einstellungen', icon: 'settings', to: '/settings' }
]

// Module visibility (check license status)
const modulesLoaded = ref(false)
const qmEnabled = ref(true)
const erpEnabled = ref(true)

async function checkModules() {
  try {
    const response = await fetch('/api/modules')
    if (response.ok) {
      const modules: Array<{ name: string; licensed: boolean }> = await response.json()
      const qmModule = modules.find(m => m.name === 'qm')
      const erpModule = modules.find(m => m.name === 'erp')
      qmEnabled.value = qmModule?.licensed !== false
      erpEnabled.value = erpModule?.licensed !== false
    }
  } catch {
    // Default: show all modules (graceful degradation)
  }
  modulesLoaded.value = true
}

const menuItems = computed(() => {
  const items = [...coreMenuItems]
  if (qmEnabled.value) items.push(...qmMenuItems)
  if (erpEnabled.value) items.push(...erpMenuItems)
  items.push(...settingsMenuItems)
  return items
})

function toggleDark() {
  $q.dark.toggle()
}

onMounted(() => {
  $q.dark.set('auto')
  checkModules()
})
</script>
