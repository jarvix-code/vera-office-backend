<template>
  <q-page class="flex flex-center bg-grey-2">
    <q-card class="onboarding-card" flat bordered>
      <q-linear-progress :value="progress" color="primary" class="q-mb-md" />

      <q-card-section>
        <div class="text-h4 text-center q-mb-md">
          Willkommen bei VERA Office
        </div>

        <!-- Step: Admin Account (only if no admin exists) -->
        <div v-if="displayStep === 'admin'">
          <div class="text-h6 q-mb-md">Schritt 1: Administrator-Konto erstellen</div>
          <div class="text-body2 text-grey-7 q-mb-lg">
            Erstellen Sie das erste Benutzerkonto mit Administratorrechten.
          </div>

          <q-input
            v-model="adminData.username"
            outlined
            label="Benutzername *"
            hint="Mindestens 3 Zeichen"
            :rules="[val => !!val && val.length >= 3 || 'Mindestens 3 Zeichen']"
            class="q-mb-md"
          />

          <q-input
            v-model="adminData.full_name"
            outlined
            label="Voller Name"
            class="q-mb-md"
          />

          <q-input
            v-model="adminData.email"
            outlined
            label="E-Mail (optional)"
            type="email"
            class="q-mb-md"
          />

          <q-input
            v-model="adminData.password"
            outlined
            label="Passwort *"
            :type="showPassword ? 'text' : 'password'"
            hint="Mindestens 8 Zeichen"
            :rules="[val => !!val && val.length >= 8 || 'Mindestens 8 Zeichen']"
            class="q-mb-md"
          >
            <template v-slot:append>
              <q-icon
                :name="showPassword ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="showPassword = !showPassword"
              />
            </template>
          </q-input>

          <q-input
            v-model="adminData.password_confirm"
            outlined
            label="Passwort bestaetigen *"
            :type="showPassword ? 'text' : 'password'"
            :rules="[val => val === adminData.password || 'Passwoerter stimmen nicht ueberein']"
            class="q-mb-md"
          />
        </div>

        <!-- Step: Company Profile -->
        <div v-else-if="displayStep === 'company'">
          <div class="text-h6 q-mb-md">Schritt {{ showAdminStep ? 2 : 1 }}: Unternehmens-Profil</div>
          
          <q-input
            v-model="onboardingStore.companyData.company_name"
            outlined
            label="Firmenname *"
            class="q-mb-md"
          />

          <q-select
            v-model="onboardingStore.companyData.company_type"
            outlined
            label="Unternehmenstyp *"
            :options="companyTypes"
            class="q-mb-md"
          />

          <q-select
            v-model="onboardingStore.companyData.industry"
            outlined
            label="Branche *"
            :options="industries"
            class="q-mb-md"
          />

          <q-select
            v-model="onboardingStore.companyData.employee_range"
            outlined
            label="Anzahl Mitarbeiter *"
            :options="employeeRanges"
            emit-value
            map-options
            class="q-mb-md"
          />
        </div>

        <!-- Step: Document Types -->
        <div v-else-if="displayStep === 'doctypes'">
          <div class="text-h6 q-mb-md">Schritt {{ showAdminStep ? 3 : 2 }}: Dokumenttypen</div>
          <div class="text-body2 text-grey-7 q-mb-lg">
            Welche Dokumenttypen moechten Sie verwalten?
          </div>

          <q-list bordered separator>
            <q-item
              v-for="category in suggestedCategories"
              :key="category"
              tag="label"
              clickable
            >
              <q-item-section avatar>
                <q-checkbox
                  v-model="onboardingStore.selectedCategories"
                  :val="category"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ category }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <!-- Step: Network Settings -->
        <div v-else-if="displayStep === 'network'">
          <div class="text-h6 q-mb-md">Schritt {{ showAdminStep ? 4 : 3 }}: Netzwerk-Einstellungen</div>

          <q-toggle
            v-model="onboardingStore.networkSettings.internet_access"
            label="Internetzugang vorhanden"
            class="q-mb-md"
          />

          <q-toggle
            v-model="onboardingStore.networkSettings.email_enabled"
            label="E-Mail-Versand aktivieren"
            class="q-mb-md"
          />

          <q-toggle
            v-if="onboardingStore.networkSettings.email_enabled"
            v-model="onboardingStore.networkSettings.auto_email"
            label="Automatischer E-Mail-Versand"
            class="q-mb-md"
          />

          <q-input
            v-model="networkShareInput"
            outlined
            label="Netzwerk-Freigaben (optional)"
            hint="Enter druecken nach jeder Eingabe"
            @keyup.enter="addNetworkShare"
            class="q-mb-md"
          >
            <template v-slot:append>
              <q-btn flat dense icon="add" @click="addNetworkShare" />
            </template>
          </q-input>

          <q-chip
            v-for="(share, index) in onboardingStore.networkSettings.network_shares"
            :key="index"
            removable
            @remove="removeNetworkShare(index)"
            color="primary"
            text-color="white"
            class="q-mr-sm q-mb-sm"
          >
            {{ share }}
          </q-chip>
        </div>

        <!-- Step: SSL Warning + iPad Connection -->
        <div v-else-if="displayStep === 'ssl'">
          <div class="text-h6 q-mb-md">Schritt {{ showAdminStep ? 5 : 4 }}: iPad verbinden</div>
          
          <q-banner class="bg-amber-2 q-mb-lg" rounded>
            <template v-slot:avatar>
              <q-icon name="security" color="amber-10" size="md" />
            </template>
            <div class="text-subtitle1 text-weight-bold q-mb-sm">Sicherheitswarnung im Browser — das ist normal!</div>
            <div class="text-body2">
              Beim ersten Zugriff zeigt Ihr Browser eine Sicherheitswarnung. 
              Das liegt daran, dass VERA ein selbst-signiertes SSL-Zertifikat verwendet — 
              <strong>das ist fuer lokale Netzwerke voellig normal und sicher.</strong>
            </div>
          </q-banner>

          <q-list bordered separator class="q-mb-lg">
            <q-item>
              <q-item-section avatar>
                <q-avatar color="blue-grey" text-color="white" icon="tablet_mac" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold">Safari (iPad)</q-item-label>
                <q-item-label caption>
                  1. Tippen Sie auf <strong>"Details einblenden"</strong><br>
                  2. Tippen Sie auf <strong>"Diese Website besuchen"</strong><br>
                  3. Bestaetigen Sie mit <strong>"Website besuchen"</strong>
                </q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section avatar>
                <q-avatar color="blue" text-color="white" icon="language" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold">Chrome</q-item-label>
                <q-item-label caption>
                  1. Klicken Sie auf <strong>"Erweitert"</strong><br>
                  2. Klicken Sie auf <strong>"Weiter zu [IP-Adresse]"</strong>
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <!-- QR Code for iPad Discovery -->
          <q-card flat bordered class="q-mb-md">
            <q-card-section class="text-center">
              <div class="text-subtitle1 text-weight-bold q-mb-sm">
                <q-icon name="qr_code_2" size="sm" class="q-mr-xs" />
                iPad verbinden — QR-Code scannen
              </div>
              <div class="text-body2 text-grey-7 q-mb-md">
                Scannen Sie diesen QR-Code mit Ihrem iPad, um VERA zu oeffnen.
              </div>
              <img 
                v-if="qrCodeUrl" 
                :src="qrCodeUrl" 
                alt="QR-Code" 
                style="max-width: 250px; width: 100%;"
                class="q-mb-sm"
              />
              <q-spinner v-else color="primary" size="60px" />
              <div v-if="discoveryInfo" class="text-caption text-grey-7 q-mt-sm">
                URL: <strong>{{ discoveryInfo.url }}</strong>
              </div>
            </q-card-section>
          </q-card>

          <q-banner class="bg-blue-1" rounded>
            <template v-slot:avatar>
              <q-icon name="tips_and_updates" color="blue" />
            </template>
            <div class="text-body2">
              <strong>Tipp:</strong> Richten Sie im Router eine feste IP-Adresse (DHCP-Reservation) 
              fuer diesen PC ein. So aendert sich die VERA-URL nie.
            </div>
          </q-banner>
        </div>
        <!-- Step: License Activation -->
        <div v-else-if="displayStep === 'license'">
          <div class="text-h6 q-mb-md">Schritt {{ showAdminStep ? 6 : 5 }}: VERA aktivieren</div>
          <div class="text-body2 text-grey-7 q-mb-lg">
            Aktivieren Sie VERA mit einem LizenzschlÃ¼ssel oder starten Sie die 30-Tage Testversion.
          </div>

          <!-- Connection Test -->
          <q-banner v-if="connectionTestResult" :class="connectionTestResult.reachable ? 'bg-positive text-white' : 'bg-warning'" class="q-mb-md">
            <template v-slot:avatar>
              <q-icon :name="connectionTestResult.reachable ? 'check_circle' : 'warning'" />
            </template>
            {{ connectionTestResult.message }}
            <template v-if="connectionTestResult.latency_ms" v-slot:action>
              <small>{{ connectionTestResult.latency_ms }}ms</small>
            </template>
          </q-banner>

          <q-btn
            outline
            color="primary"
            label="Verbindung zum Server testen"
            icon="wifi"
            @click="testConnection"
            :loading="testingConnection"
            class="q-mb-lg full-width"
            style="min-height: 56px;"
          />

          <!-- License Type Selection -->
          <q-option-group
            v-model="licenseType"
            :options="licenseOptions"
            color="primary"
            class="q-mb-lg"
          />

          <!-- Trial Info -->
          <div v-if="licenseType === 'trial'" class="q-pa-md bg-grey-2 rounded-borders q-mb-md">
            <div class="text-subtitle1">âœ… 30-Tage Testversion</div>
            <ul class="q-mt-sm text-body2 text-grey-7">
              <li>Alle Funktionen verfÃ¼gbar</li>
              <li>Bis zu 100 Dokumente</li>
              <li>Keine Kreditkarte nÃ¶tig</li>
              <li>Jederzeit zur Vollversion upgraden</li>
            </ul>
          </div>

          <!-- License Key Input -->
          <div v-if="licenseType === 'full'">
            <q-input
              v-model="licenseKey"
              outlined
              label="LizenzschlÃ¼ssel"
              placeholder="VERA-XXXXX-XXXXX-XXXXX-XXXXX"
              hint="Bitte geben Sie Ihren LizenzschlÃ¼ssel ein"
              class="q-mb-md"
              style="font-size: 16px;"
              :rules="[val => !val || val.length >= 20 || 'LizenzschlÃ¼ssel zu kurz']"
            >
              <template v-slot:prepend>
                <q-icon name="key" />
              </template>
            </q-input>

            <q-banner v-if="activationError" class="bg-negative text-white q-mb-md">
              <template v-slot:avatar>
                <q-icon name="error" />
              </template>
              {{ activationError }}
            </q-banner>

            <q-banner v-if="activationSuccess" class="bg-positive text-white q-mb-md">
              <template v-slot:avatar>
                <q-icon name="check_circle" />
              </template>
              {{ activationSuccess }}
            </q-banner>
          </div>
        </div>

        <!-- Step: Complete -->
        <div v-else-if="displayStep === 'done'">
          <div class="text-center">
            <q-icon name="check_circle" size="100px" color="positive" />
            <div class="text-h5 q-mt-md">Einrichtung abgeschlossen!</div>
            <div class="text-body1 text-grey-7 q-mt-sm">
              VERA Office ist jetzt einsatzbereit.
            </div>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-pa-md">
        <q-btn
          v-if="currentStep > 1 && displayStep !== 'done'"
          flat
          label="Zurueck"
          @click="previousStep"
        />
        <q-btn
          v-if="displayStep !== 'done'"
          unelevated
          color="primary"
          :label="displayStep === 'license' ? 'Abschliessen' : 'Weiter'"
          @click="nextStep"
          :disable="!canProceed"
          :loading="submitting"
          style="min-height: 56px; font-size: 16px;"
        />
        <q-btn
          v-if="displayStep === 'done'"
          unelevated
          color="primary"
          label="Zu Dashboard"
          @click="goToDashboard"
        />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'
import { useAuthStore } from '@/stores/auth'
import { onboardingApi, onboardingAdminApi } from '@/services/api'
import { setAdminExists } from '@/router'
import { Notify } from 'quasar'

const router = useRouter()
const onboardingStore = useOnboardingStore()
const authStore = useAuthStore()

const currentStep = ref(1)
const showAdminStep = ref(false)
const showPassword = ref(false)
const submitting = ref(false)
const networkShareInput = ref('')
const suggestedCategories = ref<string[]>([])

const adminData = ref({
  username: '',
  password: '',
  password_confirm: '',
  full_name: '',
  email: ''
})

// License activation
const licenseType = ref<'trial' | 'full'>('trial')
const licenseKey = ref('')
const testingConnection = ref(false)
const connectionTestResult = ref<any>(null)
const activationError = ref('')
const qrCodeUrl = ref('')
const discoveryInfo = ref<any>(null)

const activationSuccess = ref('')

const licenseOptions = [
  { label: '30-Tage Testversion starten', value: 'trial' },
  { label: 'LizenzschlÃ¼ssel eingeben', value: 'full' }
]

// Steps: admin(1) â†’ company â†’ doctypes â†’ network â†’ license â†’ done
// Without admin: company(1) â†’ doctypes â†’ network â†’ license â†’ done
const totalSteps = computed(() => showAdminStep.value ? 7 : 6)

// Map currentStep to a named display step
const displayStep = computed(() => {
  const step = currentStep.value
  if (showAdminStep.value) {
    if (step === 1) return 'admin'
    if (step === 2) return 'company'
    if (step === 3) return 'doctypes'
    if (step === 4) return 'network'
    if (step === 5) return 'ssl'
    if (step === 6) return 'license'
    return 'done'
  } else {
    if (step === 1) return 'company'
    if (step === 2) return 'doctypes'
    if (step === 3) return 'network'
    if (step === 4) return 'ssl'
    if (step === 5) return 'license'
    return 'done'
  }
})

const employeeRanges = [
  { label: '1-5 Mitarbeiter', value: '1-5' },
  { label: '6-20 Mitarbeiter', value: '6-20' },
  { label: '21-50 Mitarbeiter', value: '21-50' },
  { label: '51-100 Mitarbeiter', value: '51-100' },
  { label: '101-250 Mitarbeiter', value: '101-250' },
  { label: '250+ Mitarbeiter', value: '250+' }
]

const companyTypes = [
  'Einzelunternehmen',
  'GmbH',
  'AG',
  'GbR',
  'OHG',
  'KG',
  'Sonstiges'
]

const industries = [
  'IT & Software',
  'Handel',
  'Handwerk',
  'Dienstleistung',
  'Produktion',
  'Gesundheitswesen',
  'Bildung',
  'Sonstiges'
]

onMounted(async () => {
  // Check if admin exists
  try {
    const result = await onboardingAdminApi.checkExists()
    showAdminStep.value = !result.exists
  } catch {
    showAdminStep.value = false
  }

  // If admin already exists, check onboarding status and set step
  if (!showAdminStep.value) {
    const status = await onboardingStore.checkStatus()
    if (status) {
      currentStep.value = status.current_step || 1
    }
  }

  // Load QR code for SSL/discovery step
  try {
    const { default: apiInstance } = await import('@/services/api')
    const discResp = await apiInstance.get('/system/discovery')
    discoveryInfo.value = discResp.data
    qrCodeUrl.value = apiInstance.defaults.baseURL?.replace('/api', '') + '/api/system/qr?port=' + (discResp.data.port_https || 8443)
    // Fallback: use current origin
    if (!qrCodeUrl.value || qrCodeUrl.value.startsWith('undefined')) {
      qrCodeUrl.value = window.location.origin + '/api/system/qr?port=8443'
    }
  } catch (e) {
    qrCodeUrl.value = window.location.origin + '/api/system/qr?port=8443'
  }

  // Load default categories
  suggestedCategories.value = [
    'Rechnung',
    'Vertrag',
    'Angebot',
    'Lieferschein',
    'Protokoll',
    'Personalakten',
    'Steuerunterlagen',
    'Sonstiges'
  ]
})

const progress = computed(() => currentStep.value / totalSteps.value)

const canProceed = computed(() => {
  const step = displayStep.value
  
  if (step === 'admin') {
    return (
      adminData.value.username.length >= 3 &&
      adminData.value.password.length >= 8 &&
      adminData.value.password === adminData.value.password_confirm
    )
  }
  if (step === 'company') {
    const data = onboardingStore.companyData
    return !!(data.company_name && data.company_type && data.industry && data.employee_range)
  }
  if (step === 'doctypes') {
    return onboardingStore.selectedCategories.length > 0
  }
  if (step === 'license') {
    // Kann fortfahren wenn Trial ODER wenn Full mit gÃ¼ltigem Key + erfolgreich aktiviert
    if (licenseType.value === 'trial') return true
    return !!(licenseKey.value.length >= 20 && activationSuccess.value)
  }
  return true
})

async function testConnection() {
  testingConnection.value = true
  connectionTestResult.value = null
  
  try {
    const { default: apiInstance } = await import('@/services/api')
    const response = await apiInstance.post('/onboarding/connection-test')
    connectionTestResult.value = response.data
  } catch (error: any) {
    connectionTestResult.value = {
      reachable: false,
      message: 'Verbindungstest fehlgeschlagen. VERA funktioniert trotzdem offline.'
    }
  } finally {
    testingConnection.value = false
  }
}

async function activateLicense() {
  activationError.value = ''
  activationSuccess.value = ''
  
  try {
    const { default: apiInstance } = await import('@/services/api')
    const response = await apiInstance.post('/onboarding/activate', {
      license_key: licenseKey.value.trim(),
      activate_trial: licenseType.value === 'trial'
    })
    
    if (response.data.success) {
      activationSuccess.value = response.data.message
      Notify.create({
        type: 'positive',
        message: response.data.message,
        icon: 'check_circle'
      })
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || 'Aktivierung fehlgeschlagen'
    activationError.value = detail
    Notify.create({
      type: 'negative',
      message: detail
    })
  }
}

async function nextStep() {
  submitting.value = true
  try {
    const step = displayStep.value

    if (step === 'admin') {
      const result = await onboardingAdminApi.createAdmin(adminData.value)
      
      // Auto-login with returned token
      if (result.access_token) {
        localStorage.setItem('auth_token', result.access_token)
        authStore.token = result.access_token
        authStore.user = result.user
        authStore.isAuthenticated = true
        
        const { default: apiInstance } = await import('@/services/api')
        apiInstance.defaults.headers.common['Authorization'] = `Bearer ${result.access_token}`
      }
      
      // Update router cache
      setAdminExists()
      currentStep.value++

    } else if (step === 'company') {
      await onboardingStore.submitStep1()
      
      // Load suggestions for doctypes step
      try {
        const suggestions = await onboardingApi.getSuggestions()
        if (suggestions.suggestions && suggestions.suggestions.length > 0) {
          suggestedCategories.value = suggestions.suggestions.map(
            (s: any) => s.display_name || s.name
          )
        }
      } catch { /* keep defaults */ }
      currentStep.value++

    } else if (step === 'doctypes') {
      await onboardingStore.submitStep2()
      currentStep.value++

    } else if (step === 'network') {
      await onboardingStore.submitStep3()
      currentStep.value++

    } else if (step === 'ssl') {
      // SSL step is informational — just proceed
      currentStep.value++

    } else if (step === 'license') {
      // Aktiviere Lizenz
      await activateLicense()
      
      // Nur weiter wenn erfolgreich aktiviert
      if (activationSuccess.value) {
        await onboardingStore.completeOnboarding()
        currentStep.value = totalSteps.value
      } else {
        // Fehler â€” bleib auf diesem Schritt
        submitting.value = false
        return
      }
    }
  } catch (error: any) {
    console.error('Step submission error:', error)
    const detail = error.response?.data?.detail
    Notify.create({
      type: 'negative',
      message: detail || 'Fehler beim Speichern. Bitte versuchen Sie es erneut.'
    })
  } finally {
    submitting.value = false
  }
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function addNetworkShare() {
  if (networkShareInput.value.trim()) {
    onboardingStore.networkSettings.network_shares.push(networkShareInput.value.trim())
    networkShareInput.value = ''
  }
}

function removeNetworkShare(index: number) {
  onboardingStore.networkSettings.network_shares.splice(index, 1)
}

function goToDashboard() {
  router.push('/')
}
</script>

<style scoped>
.onboarding-card {
  width: 100%;
  max-width: 700px;
  margin: 20px;
}
</style>

