<template>
  <q-layout view="hHh lpR fFf">
    <!-- HEADER: mobile only, clean white -->
    <q-header v-if="!isOnboarding" class="vera-header" elevated>
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="drawer = !drawer" />
        <q-toolbar-title>
          <div class="header-brand">
            <img src="/vera-logo.svg" style="height: 26px; object-fit: contain;" alt="VERA" />
            <span class="header-title">VERA Office</span>
          </div>
        </q-toolbar-title>
        <q-space />
        <q-btn flat round dense icon="dark_mode" @click="toggleDark" class="header-icon-btn" />
        <q-btn flat round dense icon="notifications" class="header-icon-btn">
          <q-badge v-if="unreadCount > 0" color="red" floating>{{ unreadCount }}</q-badge>
          <q-menu anchor="bottom right" self="top right" style="min-width: 320px; max-width: 400px; border-radius: 12px;">
            <q-card flat>
              <q-card-section class="q-pb-none row items-center q-pt-md q-px-md">
                <div class="text-subtitle2 text-weight-semibold" style="color: #111827;">Benachrichtigungen</div>
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
                    v-for="n in notifications" :key="n.id"
                    clickable v-ripple
                    :class="n.read ? '' : 'notif-unread'"
                    @click="n.read = true"
                  >
                    <q-item-section avatar>
                      <div class="notif-icon-wrap" :style="{ background: n.bgColor }">
                        <q-icon :name="n.icon" :color="n.color" size="18px" />
                      </div>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-body2 text-weight-medium">{{ n.title }}</q-item-label>
                      <q-item-label caption>{{ n.message }}</q-item-label>
                      <q-item-label caption class="text-grey-5">{{ n.time }}</q-item-label>
                    </q-item-section>
                    <q-item-section side v-if="!n.read">
                      <div class="notif-dot"></div>
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

    <!-- SIDEBAR: 21st.dev clean white -->
    <q-drawer
      v-if="!isOnboarding"
      v-model="drawer"
      show-if-above
      :width="260"
      :breakpoint="768"
      class="vera-sidebar"
    >
      <!-- Logo block -->
      <div class="sidebar-logo-block">
        <div class="sidebar-logo-inner">
          <img src="/vera-logo.svg" style="height: 32px; object-fit: contain;" alt="VERA" />
          <div class="sidebar-brand-text">
            <div class="sidebar-brand-name">VERA Office</div>
            <div class="sidebar-brand-sub">Intelligent Office Suite</div>
          </div>
        </div>
      </div>

      <q-scroll-area class="sidebar-scroll-area">
        <div class="sidebar-nav">

          <!-- KERN -->
          <div class="nav-section-label">KERN</div>
          <router-link
            v-for="item in coreMenuItems" :key="item.to" :to="item.to"
            class="nav-item" :class="{ 'nav-item--active': isActive(item.to) }"
          >
            <div class="nav-item-icon"><q-icon :name="item.icon" size="18px" /></div>
            <span class="nav-item-label">{{ item.label }}</span>
          </router-link>

          <!-- MODULE -->
          <div class="nav-section-label" style="margin-top: 20px;">MODULE</div>

          <!-- ERP -->
          <div
            class="nav-module-header"
            :class="{ 'locked': !erpAccessible, 'mod-expanded': erpExpanded }"
            @click="erpAccessible ? (erpExpanded = !erpExpanded) : onLockedModuleClick('erp', '/finanzen')"
          >
            <div class="nav-module-icon"><q-icon name="account_balance" size="18px" /></div>
            <span>{{ erpAccessible ? 'ERP' : 'ERP - gesperrt' }}</span>
            <q-icon v-if="erpAccessible" :name="erpExpanded ? 'expand_less' : 'expand_more'" size="16px" class="q-ml-auto" />
            <q-icon v-else name="lock" size="14px" class="q-ml-auto" />
          </div>
          <div v-if="erpAccessible && erpExpanded" class="nav-sub-items">
            <router-link
              v-for="item in erpMenuItems" :key="item.to" :to="item.to"
              class="nav-item nav-item--sub" :class="{ 'nav-item--active': isActive(item.to) }"
            >
              <div class="nav-item-icon"><q-icon :name="item.icon" size="16px" /></div>
              <span class="nav-item-label">{{ item.label }}</span>
            </router-link>
          </div>

          <!-- QM -->
          <div
            class="nav-module-header"
            :class="{ 'locked': !qmAccessible, 'mod-expanded': qmExpanded }"
            @click="qmAccessible ? (qmExpanded = !qmExpanded) : onLockedModuleClick('qm', '/qm')"
          >
            <div class="nav-module-icon"><q-icon name="checklist" size="18px" /></div>
            <span>{{ qmAccessible ? 'QM' : 'QM - gesperrt' }}</span>
            <q-icon v-if="qmAccessible" :name="qmExpanded ? 'expand_less' : 'expand_more'" size="16px" class="q-ml-auto" />
            <q-icon v-else name="lock" size="14px" class="q-ml-auto" />
          </div>
          <div v-if="qmAccessible && qmExpanded" class="nav-sub-items">
            <router-link
              v-for="item in qmMenuItems" :key="item.to" :to="item.to"
              class="nav-item nav-item--sub" :class="{ 'nav-item--active': isActive(item.to) }"
            >
              <div class="nav-item-icon"><q-icon :name="item.icon" size="16px" /></div>
              <span class="nav-item-label">{{ item.label }}</span>
            </router-link>
          </div>

          <!-- SYSTEM -->
          <div class="nav-section-label" style="margin-top: 20px;">SYSTEM</div>
          <router-link
            v-for="item in settingsMenuItems" :key="item.to" :to="item.to"
            class="nav-item" :class="{ 'nav-item--active': isActive(item.to) }"
          >
            <div class="nav-item-icon"><q-icon :name="item.icon" size="18px" /></div>
            <span class="nav-item-label">{{ item.label }}</span>
          </router-link>

        </div>
      </q-scroll-area>

      <!-- Footer: status indicator -->
      <div class="sidebar-footer">
        <div class="sidebar-footer-inner">
          <div class="sidebar-footer-dot"></div>
          <span class="sidebar-footer-text">VERA laeuft</span>
        </div>
      </div>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>

    <ModuleUnlockDialog />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute } from 'vue-router'
import UserMenu from './components/UserMenu.vue'
import ModuleUnlockDialog from './components/ModuleUnlockDialog.vue'
import { useModuleAuthStore } from './stores/moduleAuth'

const $q = useQuasar()
const route = useRoute()
const drawer = ref(true)
const moduleAuth = useModuleAuthStore()
const erpExpanded = ref(false)
const qmExpanded = ref(false)

const isOnboarding = computed(() => route.path === '/onboarding')

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

const coreMenuItems = [
  { label: 'Chat', icon: 'chat', to: '/' },
  { label: 'Dokumente', icon: 'folder_open', to: '/documents' },
  { label: 'Erfassung', icon: 'camera_alt', to: '/capture' },
  { label: 'Suche', icon: 'search', to: '/search' },
  { label: 'Aufgaben', icon: 'task_alt', to: '/tasks' },
  { label: 'Export', icon: 'file_download', to: '/export' },
]
const qmMenuItems = [
  { label: 'Dashboard', icon: 'dashboard', to: '/qm' },
  { label: 'Handbuch', icon: 'menu_book', to: '/qm/handbook' },
  { label: 'Audits', icon: 'fact_check', to: '/qm/audits' },
  { label: 'Hygiene', icon: 'cleaning_services', to: '/qm/hygiene' },
  { label: 'Compliance', icon: 'verified', to: '/qm/compliance' },
]
const erpMenuItems = [
  { label: 'Dashboard', icon: 'account_balance', to: '/finanzen' },
  { label: 'BWA', icon: 'assessment', to: '/finanzen/bwa' },
  { label: 'USt', icon: 'receipt_long', to: '/finanzen/ust' },
  { label: 'Offene Posten', icon: 'payments', to: '/finanzen/offene-posten' },
  { label: 'DATEV-Export', icon: 'file_download', to: '/finanzen/datev' },
]
const settingsMenuItems = [{ label: 'Einstellungen', icon: 'settings', to: '/settings' }]

const qmAccessible = computed(() => moduleAuth.isAdminUser() || moduleAuth.sessionModules.includes('qm'))
const erpAccessible = computed(() => moduleAuth.isAdminUser() || moduleAuth.sessionModules.includes('erp'))

function toggleDark() { $q.dark.toggle() }
function onLockedModuleClick(module: string, routePath: string) { moduleAuth.requireAccess(module, routePath) }

interface Notification {
  id: number; icon: string; color: string; bgColor: string;
  title: string; message: string; time: string; read: boolean;
}
const notifications = reactive<Notification[]>([
  { id: 1, icon: 'task_alt', color: 'positive', bgColor: '#DCFCE7', title: 'Aufgabe erledigt', message: 'Dokument Hygieneplan 2026 wurde verarbeitet.', time: 'Vor 5 Min.', read: false },
  { id: 2, icon: 'cloud_upload', color: 'primary', bgColor: '#EFF6FF', title: 'Upload abgeschlossen', message: '3 neue Dokumente importiert.', time: 'Vor 1 Std.', read: false },
  { id: 3, icon: 'info', color: 'info', bgColor: '#F0F9FF', title: 'System-Info', message: 'VERA laeuft auf dem neuesten Stand.', time: 'Heute', read: true },
])
const unreadCount = computed(() => notifications.filter(n => !n.read).length)
function markAllRead() { notifications.forEach(n => { n.read = true }) }
</script>

<style lang="scss">
// ============================================================
// VERA Office — 21st.dev Design System
// Teal accent, clean white, iPad-optimised
// ============================================================

// --- HEADER ---
.vera-header {
  background: #FFFFFF !important;
  color: #1F2937 !important;
  border-bottom: 1px solid #F1F5F9;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;

  .q-toolbar { min-height: 56px; padding: 0 16px; }
  .header-brand { display: flex; align-items: center; gap: 10px; }
  .header-title {
    font-size: 16px; font-weight: 600; color: #111827;
    letter-spacing: -0.01em;
  }
  .header-icon-btn { color: #6B7280 !important; }
}
body.body--dark .vera-header {
  background: #111827 !important;
  color: #F9FAFB !important;
  border-bottom-color: #1F2937;
  .header-title { color: #F9FAFB; }
  .header-icon-btn { color: #9CA3AF !important; }
}

// --- SIDEBAR ---
.vera-sidebar {
  background: #FFFFFF !important;
  border-right: 1px solid #F1F5F9 !important;
  box-shadow: none !important;
}

.sidebar-logo-block {
  padding: 20px 16px 16px;
  border-bottom: 1px solid #F1F5F9;
}
.sidebar-logo-inner { display: flex; align-items: center; gap: 12px; }
.sidebar-brand-name {
  font-size: 15px; font-weight: 700; color: #111827;
  letter-spacing: -0.01em; line-height: 1.2;
}
.sidebar-brand-sub { font-size: 11px; color: #9CA3AF; margin-top: 1px; }

.sidebar-scroll-area { height: calc(100% - 140px) !important; }
.sidebar-nav { padding: 12px 8px; }

.nav-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  color: #9CA3AF; text-transform: uppercase; padding: 4px 10px 6px;
}

// Nav items (router-link)
a.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; text-decoration: none;
  color: #374151; font-size: 14px; font-weight: 500;
  transition: all 0.15s ease; margin-bottom: 1px;

  .nav-item-icon {
    width: 28px; height: 28px; display: flex; align-items: center;
    justify-content: center; border-radius: 6px;
    color: #9CA3AF; transition: all 0.15s ease;
  }
  .nav-item-label { color: #374151; line-height: 1; }

  &:hover {
    background: #F8FAFC;
    .nav-item-icon { color: #0EA5A0; }
    .nav-item-label { color: #111827; }
  }
  &.nav-item--active {
    background: #F0FDFA;
    .nav-item-icon { color: #0D7380; background: #CCFBF1; }
    .nav-item-label { color: #0D7380; font-weight: 600; }
  }
  &.nav-item--sub { padding-left: 20px; font-size: 13px; }
}

// Module accordion header
.nav-module-header {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px;
  cursor: pointer; font-size: 14px; font-weight: 500;
  color: #374151; transition: all 0.15s ease;
  margin-bottom: 1px; user-select: none;

  .nav-module-icon {
    width: 28px; height: 28px; display: flex; align-items: center;
    justify-content: center; border-radius: 6px;
    color: #9CA3AF; transition: all 0.15s ease;
  }
  &:hover { background: #F8FAFC; .nav-module-icon { color: #0EA5A0; } }
  &.mod-expanded {
    background: #F0FDFA; color: #0D7380; font-weight: 600;
    .nav-module-icon { color: #0D7380; background: #CCFBF1; }
  }
  &.locked { color: #9CA3AF; }
}
.nav-sub-items { margin-bottom: 4px; }

// Footer
.sidebar-footer {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 12px 16px; border-top: 1px solid #F1F5F9; background: #FFFFFF;
}
.sidebar-footer-inner { display: flex; align-items: center; gap: 8px; }
.sidebar-footer-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #10B981; box-shadow: 0 0 0 2px #D1FAE5;
}
.sidebar-footer-text { font-size: 12px; color: #9CA3AF; }

// Notifications
.notif-unread { background: #F0F9FF; }
.notif-icon-wrap {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}
.notif-dot { width: 8px; height: 8px; border-radius: 50%; background: #0EA5A0; }

// Dark mode
body.body--dark {
  .vera-sidebar { background: #111827 !important; border-right-color: #1F2937 !important; }
  .sidebar-logo-block { border-bottom-color: #1F2937; }
  .sidebar-brand-name { color: #F9FAFB; }
  .sidebar-brand-sub { color: #6B7280; }
  .nav-section-label { color: #4B5563; }
  a.nav-item {
    color: #D1D5DB;
    .nav-item-label { color: #D1D5DB; }
    &:hover { background: #1F2937; .nav-item-label { color: #F9FAFB; } }
    &.nav-item--active {
      background: rgba(14,165,160,0.15);
      .nav-item-label { color: #5EEAD4; }
      .nav-item-icon { background: rgba(14,165,160,0.2); color: #5EEAD4; }
    }
  }
  .nav-module-header {
    color: #D1D5DB;
    &:hover { background: #1F2937; }
    &.mod-expanded {
      background: rgba(14,165,160,0.15); color: #5EEAD4;
      .nav-module-icon { color: #5EEAD4; background: rgba(14,165,160,0.2); }
    }
    &.locked { color: #4B5563; }
  }
  .sidebar-footer { border-top-color: #1F2937; background: #111827; }
  .sidebar-footer-text { color: #4B5563; }
}
</style>
