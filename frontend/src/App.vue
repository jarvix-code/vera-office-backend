<template>
  <q-layout view="hHh lpR fFf">
    <q-header v-if="!isOnboarding" elevated class="vera-header">
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
          <img src="/vera-logo.svg" style="height: 28px; vertical-align: middle; margin-right: 8px; margin-bottom: 2px;" alt="VERA" />VERA Office
        </q-toolbar-title>
        <q-space />
        <q-btn flat round dense icon="dark_mode" @click="toggleDark" />
        <q-btn flat round dense icon="notifications">
          <q-badge v-if="unreadCount > 0" color="red" floating>{{ unreadCount }}</q-badge>
          <q-menu anchor="bottom right" self="top right" style="min-width: 320px; max-width: 400px;">
            <q-card flat>
              <q-card-section class="q-pb-none row items-center">
                <div class="text-subtitle2 text-weight-bold">Benachrichtigungen</div>
                <q-space />
                <q-btn flat dense round icon="done_all" size="sm" @click="markAllRead" />
              </q-card-section>
              <q-separator class="q-mt-sm" />
              <q-list style="max-height: 360px; overflow-y: auto;">
                <template v-if="notifications.length === 0">
                  <q-item>
                    <q-item-section class="text-center text-grey q-py-md">
                      <q-icon name="notifications_none" size="2rem" class="q-mb-sm" />
                      <div class="text-caption">Keine Benachrichtigungen</div>
                    </q-item-section>
                  </q-item>
                </template>
                <template v-else>
                  <q-item
                    v-for="n in notifications"
                    :key="n.id"
                    clickable
                    v-ripple
                    :class="n.read ? '' : 'bg-blue-1'"
                    @click="n.read = true"
                  >
                    <q-item-section avatar>
                      <q-icon :name="n.icon" :color="n.color" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-body2">{{ n.title }}</q-item-label>
                      <q-item-label caption>{{ n.message }}</q-item-label>
                      <q-item-label caption class="text-grey-6">{{ n.time }}</q-item-label>
                    </q-item-section>
                    <q-item-section side v-if="!n.read">
                      <q-badge color="primary" rounded />
                    </q-item-section>
                  </q-item>
                </template>
              </q-list>
            </q-card>
          </q-menu>
        </q-btn>
        <UserMenu />
      </q-toolbar>
    </q-header>

    <q-drawer
      v-if="!isOnboarding"
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

          <!-- 2. ERP (immer sichtbar, gesperrt wenn kein Modul-Zugang) -->
          <q-separator class="q-my-sm" />
          <q-expansion-item
            icon="account_balance"
            :label="erpAccessible ? 'ERP' : 'ERP (gesperrt)'"
            :header-inset-level="0"
            :header-class="erpAccessible ? '' : 'text-grey-5'"
            :disable="!erpAccessible"
            dense
            @click.capture="!erpAccessible && onLockedModuleClick('erp', '/finanzen')"
          >
            <q-item
              v-for="item in erpMenuItems"
              :key="item.to"
              :to="item.to"
              v-ripple
              active-class="q-router-link--active"
              :inset-level="1"
              :class="erpAccessible ? '' : 'text-grey-5'"
            >
              <q-item-section avatar>
                <q-icon :name="erpAccessible ? item.icon : 'lock'" size="xs" />
              </q-item-section>
              <q-item-section><q-item-label class="text-body2">{{ item.label }}</q-item-label></q-item-section>
            </q-item>
          </q-expansion-item>

          <!-- 3. QM (immer sichtbar, gesperrt wenn kein Modul-Zugang) -->
          <q-separator class="q-my-sm" />
          <q-expansion-item
            icon="checklist"
            :label="qmAccessible ? 'QM' : 'QM (gesperrt)'"
            :header-inset-level="0"
            :header-class="qmAccessible ? '' : 'text-grey-5'"
            :disable="!qmAccessible"
            dense
            @click.capture="!qmAccessible && onLockedModuleClick('qm', '/qm')"
          >
            <q-item
              v-for="item in qmMenuItems"
              :key="item.to"
              :to="item.to"
              v-ripple
              active-class="q-router-link--active"
              :inset-level="1"
              :class="qmAccessible ? '' : 'text-grey-5'"
            >
              <q-item-section avatar>
                <q-icon :name="qmAccessible ? item.icon : 'lock'" size="xs" />
              </q-item-section>
              <q-item-section><q-item-label class="text-body2">{{ item.label }}</q-item-label></q-item-section>
            </q-item>
          </q-expansion-item>

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

    <!-- Modul-Zugangs-Dialog (Name+PIN + Promo-Code) -->
    <ModuleUnlockDialog />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute } from 'vue-router'
import UserMenu from './components/UserMenu.vue'
import ModuleUnlockDialog from './components/ModuleUnlockDialog.vue'
import { useModuleAuthStore } from './stores/moduleAuth'

const $q = useQuasar()
const route = useRoute()
const drawer = ref(true)
const moduleAuth = useModuleAuthStore()

const isOnboarding = computed(() => route.path === '/onboarding')

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

// Modul-Zugänglichkeit basiert auf Modul-Session (Name + PIN)
const qmAccessible = computed(() => moduleAuth.isAdminUser() || moduleAuth.sessionModules.includes('qm'))
const erpAccessible = computed(() => moduleAuth.isAdminUser() || moduleAuth.sessionModules.includes('erp'))

function toggleDark() {
  $q.dark.toggle()
}

// Bug #680 fix: clicking locked ERP/QM header triggers module auth dialog
function onLockedModuleClick(module: string, route: string) {
  moduleAuth.requireAccess(module, route)
}

// Bug #649 fix: Notifications panel
interface Notification {
  id: number
  icon: string
  color: string
  title: string
  message: string
  time: string
  read: boolean
}

const notifications = reactive<Notification[]>([
  { id: 1, icon: 'task_alt', color: 'positive', title: 'Aufgabe erledigt', message: 'Dokument "Hygieneplan 2026" wurde verarbeitet.', time: 'Vor 5 Min.', read: false },
  { id: 2, icon: 'cloud_upload', color: 'primary', title: 'Upload abgeschlossen', message: '3 neue Dokumente wurden erfolgreich importiert.', time: 'Vor 1 Std.', read: false },
  { id: 3, icon: 'info', color: 'info', title: 'System-Info', message: 'VERA läuft auf dem neuesten Stand.', time: 'Heute', read: true },
])

const unreadCount = computed(() => notifications.filter(n => !n.read).length)

function markAllRead() {
  notifications.forEach(n => { n.read = true })
}
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
