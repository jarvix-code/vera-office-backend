<template>
  <q-dialog v-model="show" persistent>
    <q-card style="min-width: 500px; max-width: 700px">
      <!-- VERA Avatar + Confidence -->
      <q-card-section class="row items-center q-pb-none">
        <q-avatar color="primary" text-color="white" icon="psychology" size="56px" />
        <div class="q-ml-md flex-1">
          <div class="text-h6">VERA fraucht Hilfe</div>
          <q-linear-progress 
            :value="confidence" 
            :color="confidenceColor"
            class="q-mt-sm" 
            size="8px"
          />
          <div class="text-caption q-mt-xs">
            {{ (confidence * 100).toFixed(0) }}% sicher
          </div>
        </div>
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <!-- STUFE 2: QUICK CONFIRM (75-95% Confidence) -->
      <q-card-section v-if="canQuickConfirm && !showExplanation">
        <div class="text-body1 q-mb-md">
          {{ classification.frage }}
        </div>
        
        <!-- Document Info -->
        <q-card flat bordered class="q-mb-md">
          <q-card-section class="q-pa-sm">
            <div class="row items-center">
              <q-icon name="description" size="24px" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-7">Dokument</div>
                <div class="text-body2">{{ documentName }}</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
        
        <!-- Quick Confirm Buttons (1-Click!) -->
        <div class="q-gutter-sm q-mt-lg">
          <q-btn
            label="✓ Ja, richtig"
            color="positive"
            size="lg"
            icon="check_circle"
            class="full-width"
            @click="confirmSuggestion"
          />
          
          <q-btn
            label="✗ Nein, anders"
            color="grey-7"
            outline
            size="md"
            class="full-width"
            @click="showExplanation = true"
          />
        </div>
        
        <!-- Dokument ansehen Link (klein) -->
        <q-btn
          flat
          dense
          size="sm"
          color="primary"
          icon="visibility"
          label="Dokument ansehen"
          class="full-width q-mt-md"
          @click="openDocumentReader"
        />
      </q-card-section>

      <!-- STUFE 3: VOLLE ERKLÄRUNG (<75% Confidence) -->
      <q-card-section v-if="!canQuickConfirm || showExplanation">
        <div class="text-body1 q-mb-md">
          {{ classification.frage }}
        </div>
        
        <!-- Document Info -->
        <q-card flat bordered class="q-mb-md">
          <q-card-section class="q-pa-sm">
            <div class="row items-center">
              <q-icon name="description" size="24px" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-7">Dokument</div>
                <div class="text-body2">{{ documentName }}</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
        
        <!-- Dokument ansehen Button -->
        <q-btn
          flat
          color="primary"
          icon="visibility"
          label="📄 Dokument ansehen"
          class="full-width q-mb-md"
          @click="openDocumentReader"
        />
      </q-card-section>

      <!-- Explanation Form (Stufe 3 oder nach "Nein, anders") -->
      <q-card-section v-if="!canQuickConfirm || showExplanation">
        <q-separator class="q-mb-md" />
        
        <div class="text-subtitle2 q-mb-sm">
          Was ist das für ein Dokument?
        </div>
        
        <!-- FREE TEXT FIELD (WICHTIG: KEINE Dropdowns!) -->
        <q-input
          v-model="userExplanation"
          type="textarea"
          outlined
          placeholder="Erkläre ausführlich - VERA lernt daraus neue Kategorien!"
          hint="Beispiel: 'Das ist ein Wartungsvertrag für unsere Röntgengeräte von SiroDent.'"
          rows="5"
          autofocus
          class="q-mb-md"
        >
          <template v-slot:prepend>
            <q-icon name="edit" />
          </template>
        </q-input>
        
        <!-- Action Buttons -->
        <div class="row q-gutter-sm">
          <q-btn
            color="primary"
            icon="send"
            label="Speichern & VERA lernt"
            :disable="!userExplanation || userExplanation.trim().length < 5"
            @click="submitExplanation"
            class="col"
          />
          <q-btn
            flat
            color="grey-7"
            icon="help_outline"
            label="Ich bin auch unsicher"
            @click="escalate"
            class="col"
          />
        </div>
      </q-card-section>

      <!-- Später Button (nur wenn kein Quick Confirm UND kein Explanation-Form) -->
      <q-card-actions v-if="!canQuickConfirm && !showExplanation" align="right">
        <q-btn flat label="Später" @click="skip" />
        <q-btn 
          color="primary" 
          label="Jetzt helfen" 
          @click="showExplanation = true"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <!-- Document Reader Modal (Vollbild) -->
  <document-reader-modal
    v-model="readerOpen"
    :document-id="documentId"
    @close="readerOpen = false"
  />
</template>

<script>
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import DocumentReaderModal from './DocumentReaderModal.vue'

export default {
  name: 'ActiveLearningDialog',
  
  components: {
    DocumentReaderModal
  },
  
  props: {
    modelValue: Boolean,
    classification: {
      type: Object,
      required: true
    },
    documentId: {
      type: Number,
      required: true
    },
    documentName: {
      type: String,
      default: 'unbekannt.pdf'
    }
  },
  
  emits: ['update:modelValue', 'confirmed', 'skipped', 'escalated'],
  
  setup(props, { emit }) {
    const $q = useQuasar()
    
    const show = computed({
      get: () => props.modelValue,
      set: (val) => emit('update:modelValue', val)
    })
    
    const userExplanation = ref('')
    const showExplanation = ref(false)
    const readerOpen = ref(false)
    
    const confidence = computed(() => {
      return props.classification?.confidence || 0
    })
    
    const canQuickConfirm = computed(() => {
      // STUFE 2: Quick Confirm möglich bei 75-95% Confidence
      return props.classification?.can_quick_confirm || false
    })
    
    const confidenceColor = computed(() => {
      const conf = confidence.value
      if (conf >= 0.95) return 'positive'  // Grün für Auto (≥95%)
      if (conf >= 0.75) return 'warning'   // Orange für Quick Confirm (75-95%)
      return 'negative'  // Rot für Needs Explanation (<75%)
    })
    
    const openDocumentReader = () => {
      readerOpen.value = true
    }
    
    const confirmSuggestion = async () => {
      // STUFE 2: User bestätigt VERA's Vorschlag (1-Click!)
      const vorschlag = props.classification?.vorschlag
      
      if (!vorschlag) {
        $q.notify({
          type: 'warning',
          message: 'Kein Vorschlag vorhanden.'
        })
        return
      }
      
      try {
        const params = new URLSearchParams({
          doc_id: props.documentId.toString(),
          confirmed_class: vorschlag
        })
        
        const response = await fetch(`/api/demo/confirm-suggestion?${params}`, {
          method: 'POST'
        })
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        
        $q.notify({
          type: 'positive',
          message: data.message,
          icon: 'check_circle'
        })
        
        emit('confirmed', {
          category: vorschlag,
          was_suggestion: true,
          confidence: confidence.value
        })
        
        show.value = false
        
      } catch (error) {
        console.error('Failed to confirm suggestion:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler beim Bestätigen',
          caption: error.message
        })
      }
    }
    
    const submitExplanation = async () => {
      if (!userExplanation.value || userExplanation.value.trim().length < 5) {
        $q.notify({
          type: 'warning',
          message: 'Bitte gib eine ausführlichere Erklärung.'
        })
        return
      }
      
      try {
        const response = await fetch('/api/active-learning/explain', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doc_id: props.documentId,
            explanation: userExplanation.value,
            user_name: 'Boris' // TODO: Get from auth
          })
        })
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        
        $q.notify({
          type: 'positive',
          message: data.message,
          caption: `Kategorie: ${data.category}`,
          icon: 'check_circle'
        })
        
        emit('confirmed', {
          category: data.category,
          explanation: userExplanation.value
        })
        
        show.value = false
        
      } catch (error) {
        console.error('Failed to submit explanation:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler beim Speichern',
          caption: error.message
        })
      }
    }
    
    const escalate = async () => {
      try {
        const response = await fetch('/api/active-learning/escalate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doc_id: props.documentId,
            user_comment: userExplanation.value || 'Ich bin auch unsicher',
            user_name: 'Boris' // TODO: Get from auth
          })
        })
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        
        $q.notify({
          type: 'info',
          message: data.message,
          caption: `Position in Queue: ${data.queue_position}`,
          icon: 'schedule'
        })
        
        emit('escalated')
        show.value = false
        
      } catch (error) {
        console.error('Failed to escalate:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler bei Escalation',
          caption: error.message
        })
      }
    }
    
    const skip = () => {
      emit('skipped')
      show.value = false
    }
    
    return {
      show,
      userExplanation,
      showExplanation,
      readerOpen,
      confidence,
      canQuickConfirm,
      confidenceColor,
      openDocumentReader,
      confirmSuggestion,
      submitExplanation,
      escalate,
      skip
    }
  }
}
</script>

<style scoped>
/* No custom styles needed - Quasar does it all */
</style>
