<template>
  <q-dialog v-model="show" persistent>
    <q-card style="min-width: 500px">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">📝 Feedback senden</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section>
        <p class="text-body2 text-grey-7">
          Hilf uns VERA zu verbessern! Dein Feedback wird an unser Entwicklungsteam weitergeleitet.
        </p>

        <q-select
          v-model="type"
          :options="typeOptions"
          label="Art des Feedbacks"
          outlined
          dense
          class="q-mb-md"
        />

        <q-input
          v-model="message"
          type="textarea"
          label="Dein Feedback"
          outlined
          rows="6"
          autogrow
          placeholder="Beschreibe dein Problem oder deinen Verbesserungsvorschlag..."
          :rules="[val => !!val || 'Bitte gib eine Nachricht ein']"
        />

        <q-file
          v-model="screenshot"
          label="Screenshot (optional)"
          outlined
          dense
          accept="image/*"
          class="q-mt-md"
        >
          <template v-slot:prepend>
            <q-icon name="camera_alt" />
          </template>
        </q-file>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Abbrechen" color="grey" v-close-popup />
        <q-btn
          unelevated
          label="Senden"
          color="primary"
          @click="submitFeedback"
          :loading="loading"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import api from '../services/api'

export default {
  name: 'FeedbackDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const $q = useQuasar()
    
    // Computed für v-model binding (read + write)
    const show = computed({
      get: () => props.modelValue,
      set: (val) => emit('update:modelValue', val)
    })
    
    const type = ref({ label: '🐛 Bug melden', value: 'bug' })
    const message = ref('')
    const screenshot = ref(null)
    const loading = ref(false)

    const typeOptions = [
      { label: '🐛 Bug melden', value: 'bug' },
      { label: '💡 Verbesserungsvorschlag', value: 'feature' },
      { label: '❓ Frage / Hilfe', value: 'question' },
      { label: '💬 Sonstiges', value: 'other' }
    ]

    const submitFeedback = async () => {
      if (!message.value.trim()) {
        $q.notify({
          type: 'warning',
          message: 'Bitte gib eine Nachricht ein'
        })
        return
      }

      loading.value = true

      try {
        const formData = new FormData()
        formData.append('type', type.value.value)
        formData.append('message', message.value)
        if (screenshot.value) {
          formData.append('screenshot', screenshot.value)
        }

        // Use absolute URL to bypass /api prefix (feedback route is public)
        await fetch('/feedback/submit', {
          method: 'POST',
          body: formData
        })

        $q.notify({
          type: 'positive',
          message: '✅ Feedback gesendet! Danke für deine Hilfe.',
          icon: 'done'
        })

        // Reset form
        type.value = { label: '🐛 Bug melden', value: 'bug' }
        message.value = ''
        screenshot.value = null

        // Close dialog
        emit('update:modelValue', false)
      } catch (error) {
        console.error('Feedback error:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler beim Senden. Bitte versuche es erneut.',
          icon: 'error'
        })
      } finally {
        loading.value = false
      }
    }

    return {
      show,
      type,
      message,
      screenshot,
      loading,
      typeOptions,
      submitFeedback
    }
  }
}
</script>
