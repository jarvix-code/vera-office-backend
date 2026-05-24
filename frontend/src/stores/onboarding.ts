import { defineStore } from 'pinia'
import { ref } from 'vue'
import { onboardingApi } from '@/services/api'

export const useOnboardingStore = defineStore('onboarding', () => {
  const isComplete = ref(false)
  const currentStep = ref(1)
  const companyData = ref({
    company_name: '',
    company_type: '',
    industry: '',
    employee_range: ''
  })
  const selectedCategories = ref<string[]>([])
  const networkSettings = ref({
    internet_access: true,
    email_enabled: false,
    auto_email: false,
    network_shares: [] as string[]
  })

  async function checkStatus() {
    try {
      const status = await onboardingApi.getStatus()
      isComplete.value = status.completed
      currentStep.value = status.current_step || 1
      return status
    } catch (error) {
      console.error('Failed to check onboarding status:', error)
      return null
    }
  }

  async function submitStep1() {
    const result = await onboardingApi.submitStep1(companyData.value)
    currentStep.value = 2
    return result
  }

  async function submitStep2() {
    const result = await onboardingApi.submitStep2(selectedCategories.value)
    currentStep.value = 3
    return result
  }

  async function submitStep3() {
    const result = await onboardingApi.submitStep3(networkSettings.value)
    currentStep.value = 4
    return result
  }

  async function completeOnboarding() {
    const result = await onboardingApi.complete()
    isComplete.value = true
    return result
  }

  return {
    isComplete,
    currentStep,
    companyData,
    selectedCategories,
    networkSettings,
    checkStatus,
    submitStep1,
    submitStep2,
    submitStep3,
    completeOnboarding
  }
})
