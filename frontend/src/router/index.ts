import { createRouter, createWebHistory } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'
import { useAuthStore } from '@/stores/auth'
import { useModuleAuthStore } from '@/stores/moduleAuth'

// Admin exists cache (checked once per session)
let adminExistsCache: boolean | null = null

/** Call after admin creation to update cache */
export function setAdminExists() {
  adminExistsCache = true
}

/** Call to force re-check (e.g. after module unlock) ??? kept for ModuleUnlockDialog compatibility */
export function invalidateModuleLicenseCache() {
  // No-op: module access is now session-based via moduleAuth store
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true }  // Kein Auth erforderlich
    },
    {
      path: '/onboarding',
      name: 'Onboarding',
      component: () => import('@/views/OnboardingView.vue')
    },
    {
      path: '/',
      name: 'Chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/documents',
      name: 'Documents',
      component: () => import('@/views/DocumentsView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/documents/:id',
      name: 'DocumentDetail',
      component: () => import('@/views/DocumentDetailView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/capture',
      name: 'Capture',
      component: () => import('@/views/CaptureView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('@/views/SearchView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/chat',
      redirect: '/'
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/TasksView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/export',
      name: 'Export',
      component: () => import('@/views/ExportView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresOnboarding: true }
    },
    // QM Module
    {
      path: '/qm',
      name: 'QmDashboard',
      component: () => import('@/views/qm/QmDashboardView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'qm' }
    },
    {
      path: '/qm/handbook',
      name: 'QmHandbook',
      component: () => import('@/views/qm/QmHandbookView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'qm' }
    },
    {
      path: '/qm/audits',
      name: 'QmAudits',
      component: () => import('@/views/qm/QmAuditsView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'qm' }
    },
    {
      path: '/qm/hygiene',
      name: 'QmHygiene',
      component: () => import('@/views/qm/QmHygieneView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'qm' }
    },
    {
      path: '/qm/compliance',
      name: 'QmCompliance',
      component: () => import('@/views/qm/QmComplianceView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'qm' }
    },
    {
      path: '/recent',
      name: 'Recent',
      component: () => import('@/views/DocumentsView.vue'),
      meta: { requiresOnboarding: true }
    },
    {
      path: '/inbox',
      name: 'Inbox',
      component: () => import('@/views/InboxView.vue'),
      meta: { requiresOnboarding: true }
    },
    // ERP Module
    {
      path: '/erp',
      redirect: '/finanzen'
    },
    {
      path: '/finanzen',
      name: 'ErpDashboard',
      component: () => import('@/views/erp/ErpDashboardView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'erp' }
    },
    {
      path: '/finanzen/bwa',
      name: 'ErpBwa',
      component: () => import('@/views/erp/ErpBwaView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'erp' }
    },
    {
      path: '/finanzen/ust',
      name: 'ErpUst',
      component: () => import('@/views/erp/ErpUstView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'erp' }
    },
    {
      path: '/finanzen/offene-posten',
      name: 'ErpOpenItems',
      component: () => import('@/views/erp/ErpOpenItemsView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'erp' }
    },
    {
      path: '/finanzen/datev',
      name: 'ErpDatev',
      component: () => import('@/views/erp/ErpDatevExportView.vue'),
      meta: { requiresOnboarding: true, requiresModule: 'erp' }
    }
  ]
})

// Navigation guard: Admin exists ??? Auth ??? Onboarding ??? Module Licenses
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const onboardingStore = useOnboardingStore()
  
  // 0. Check if admin exists ??? if not, force onboarding (cached, checked once)
  if (to.path !== '/onboarding' && adminExistsCache !== true) {
    if (adminExistsCache === null) {
      try {
        const resp = await fetch('/api/onboarding/admin/exists')
        if (resp.ok) {
          const data = await resp.json()
          adminExistsCache = data.exists
        } else {
          adminExistsCache = true // Assume exists on error
        }
      } catch {
        adminExistsCache = true // API not reachable, don't block
      }
    }
    if (adminExistsCache === false) {
      next('/onboarding')
      return
    }
  }
  
  // 1. Auth Check (except /login and /onboarding)
  if (!to.meta.public && to.path !== '/onboarding' && !authStore.isAuthenticated) {
    // Nicht eingeloggt ??? Redirect zu Login
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }
  
  // 2. Onboarding Check
  if (to.meta.requiresOnboarding && !onboardingStore.isComplete) {
    await onboardingStore.checkStatus()
    if (!onboardingStore.isComplete) {
      next('/onboarding')
      return
    }
  }
  
  // 3. Module Access Check (Modul-Session: Name + PIN)
  const requiredModule = to.meta.requiresModule as string | undefined
  if (requiredModule) {
    const moduleAuthStore = useModuleAuthStore()
    if (!moduleAuthStore.hasModuleAccess(requiredModule)) {
      // Keine Session oder Modul nicht freigeschaltet ??? Dialog
      moduleAuthStore.requireAccess(requiredModule, to.fullPath)
      next(false)
      return
    }
  }

  next()
})


// Bug #648 Fix: ChunkLoadError nach Frontend-Rebuild abfangen.
// Wenn der Browser einen gecachten alten main-bundle hat, schlagen dynamische
// Imports mit 404 fehl (Failed to fetch dynamically imported module).
// Hard-Reload zur Zielpfad erzwingt neuen index.html + Bundle vom Server.
let _chunkReloadAttempted = false
router.onError((err: Error, to) => {
  const isChunkError =
    err.message?.includes('Failed to fetch dynamically imported module') ||
    err.message?.includes('Importing a module script failed') ||
    err.name === 'ChunkLoadError'
  if (isChunkError && !_chunkReloadAttempted) {
    _chunkReloadAttempted = true
    const targetPath = to?.fullPath ?? window.location.pathname
    window.location.href = targetPath
  }
})

export default router
