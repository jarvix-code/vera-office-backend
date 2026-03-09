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
        <UserMenu />
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
        <div class="text-caption" style="color: #CBD5E1;">Intelligent Office Assistant</div>
      </div>

      <q-scroll-area class="fit" style="margin-top: -8px;">
        <q-list padding>
          <!-- 1. DOKUMENTENVERWALTUNG -->
          <q-expansion-item
            icon="folder_open"
            label="Dokumentenverwaltung"
            :header-inset-level="0"
            default-opened
            dense
          >
            <q-item
              v-for="item in coreMenuItems"
              :key="item.to"
              :to="item.to"
              v-ripple
              active-class="q-router-link--active"
              :inset-level="1"
            >
              <q-item-section avatar><q-icon :name="item.icon" size="xs" /></q-item-section>
              <q-item-section><q-item-label class="text-body2">{{ item.label }}</q-item-label></q-item-section>
            </q-item>
          </q-expansion-item>

          <!-- 2. ERP (wenn lizenziert) -->
          <template v-if="erpEnabled">
            <q-separator class="q-my-sm" />
            <q-expansion-item
              icon="account_balance"
              label="ERP"
              :header-inset-level="0"
              dense
            >
              <q-item
                v-for="item in erpMenuItems"
                :key="item.to"
                :to="item.to"
                v-ripple
                active-class="q-router-link--active"
                :inset-level="1"
              >
                <q-item-section avatar><q-icon :name="item.icon" size="xs" /></q-item-section>
                <q-item-section><q-item-label class="text-body2">{{ item.label }}</q-item-label></q-item-section>
              </q-item>
            </q-expansion-item>
          </template>

          <!-- 3. QM (wenn lizenziert) -->
          <template v-if="qmEnabled">
            <q-separator class="q-my-sm" />
            <q-expansion-item
              icon="checklist"
              label="QM"
              :header-inset-level="0"
              dense
            >
              <q-item
                v-for="item in qmMenuItems"
                :key="item.to"
                :to="item.to"
                v-ripple
                active-class="q-router-link--active"
                :inset-level="1"
              >
                <q-item-section avatar><q-icon :name="item.icon" size="xs" /></q-item-section>
                <q-item-section><q-item-label class="text-body2">{{ item.label }}</q-item-label></q-item-section>
              </q-item>
            </q-expansion-item>
          </template>

          <!-- SYSTEM -->
          <q-separator class="q-my-md" />
          <q-item-label header class="text-caption text-weight-bold">SYSTEM</q-item-label>
          <q-item
            v-for="item in settingsMenuItems"
            :key="item.to"
            :to="item.to"
            v-ripple
            active-class="q-router-link--active"
          >
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
import UserMenu from './components/UserMenu.vue'

const $q = useQuasar()
const drawer = ref(true)

// Dokumentenverwaltung (vollständige Liste)
const coreMenuItems = [
  { label: 'Home', icon: 'home', to: '/' },
  { label: 'Dokumente', icon: 'folder', to: '/documents' },
  { label: 'Erfassung', icon: 'camera_alt', to: '/capture' },
  { label: 'Suche', icon: 'search', to: '/search' },
  { label: 'Aufgaben', icon: 'task_alt', to: '/tasks' },
  { label: 'Export', icon: 'download', to: '/export' },
]

// QM (als Expansion-Item, nicht alle einzeln)
const qmMenuItems = [
  { label: 'Dashboard', icon: 'dashboard', to: '/qm' },
  { label: 'Handbuch', icon: 'menu_book', to: '/qm/handbook' },
  { label: 'Audits', icon: 'fact_check', to: '/qm/audits' },
  { label: 'Hygiene', icon: 'cleaning_services', to: '/qm/hygiene' },
  { label: 'Compliance', icon: 'verified', to: '/qm/compliance' },
]

// ERP (als Expansion-Item)
const erpMenuItems = [
  { label: 'Dashboard', icon: 'account_balance', to: '/finanzen' },
  { label: 'BWA', icon: 'assessment', to: '/finanzen/bwa' },
  { label: 'USt', icon: 'receipt_long', to: '/finanzen/ust' },
  { label: 'Offene Posten', icon: 'payments', to: '/finanzen/offene-posten' },
  { label: 'DATEV-Export', icon: 'download', to: '/finanzen/datev' },
]

// SYSTEM (nur Einstellungen)
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

function toggleDark() {
  $q.dark.toggle()
}

onMounted(() => {
  checkModules()
})
</script>

<style>
.vera-sidebar {
  background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
}

/* ✅ FIX: Helle Textfarben für Sidebar (Bug #6) */
.vera-sidebar .q-item__label {
  color: #E2E8F0 !important; /* Hellgrau für gute Lesbarkeit */
}

.vera-sidebar .q-item-label--header {
  color: #FFFFFF !important; /* Weiß für Überschriften (KERN, QUALITÄTSMANAGEMENT, etc.) */
  font-weight: bold;
  letter-spacing: 0.05em;
}

.vera-sidebar .q-icon {
  color: #CBD5E1 !important; /* Helle Icons */
}

.vera-sidebar .q-expansion-item__label {
  color: #E2E8F0 !important; /* Expansion-Header (QM-System, Buchhaltung) */
}

/* Aktiver Menu-Item: Deutlich hervorgehoben */
.q-router-link--active {
  background: rgba(124, 58, 237, 0.25) !important;
  border-left: 4px solid #A78BFA !important; /* Helleres Lila für besseren Kontrast */
}

.q-router-link--active .q-item__label {
  color: #FFFFFF !important; /* Weiß für aktiven Item */
  font-weight: 600;
}

.q-router-link--active .q-icon {
  color: #A78BFA !important; /* Lila-Icon für aktiven Item */
}

/* Header-Styles */
.vera-header {
  background: #FFFFFF;
  color: #1E293B;
}

body.body--dark .vera-header {
  background: #1E293B;
  color: #FFFFFF;
}
</style>
