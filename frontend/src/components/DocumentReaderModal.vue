<template>
  <q-dialog v-model="show" full-width full-height>
    <q-card class="full-height">
      <!-- Header -->
      <q-bar class="bg-primary text-white">
        <q-btn 
          flat 
          dense 
          icon="arrow_back" 
          @click="close"
        >
          <q-tooltip>Zurück</q-tooltip>
        </q-btn>
        
        <div class="col text-center">
          <span class="text-weight-medium">{{ documentName }}</span>
        </div>
        
        <q-btn 
          flat 
          dense 
          icon="download" 
          @click="downloadDocument"
        >
          <q-tooltip>Download</q-tooltip>
        </q-btn>
        
        <q-btn flat dense icon="close" v-close-popup />
      </q-bar>

      <!-- PDF Viewer -->
      <q-card-section class="full-height q-pa-none">
        <div v-if="loading" class="full-height flex flex-center">
          <q-spinner color="primary" size="50px" />
          <div class="q-mt-md">Dokument wird geladen...</div>
        </div>
        
        <div v-else-if="error" class="full-height flex flex-center">
          <q-icon name="error_outline" color="negative" size="64px" />
          <div class="q-mt-md text-negative">{{ error }}</div>
          <q-btn 
            outline 
            color="primary" 
            label="Erneut versuchen" 
            @click="loadDocument"
            class="q-mt-md"
          />
        </div>
        
        <!-- PDF Iframe -->
        <iframe
          v-else
          :src="documentUrl"
          class="full-width full-height"
          style="border: none;"
        />
      </q-card-section>

      <!-- Footer with Action Button -->
      <q-card-actions align="center" class="bg-grey-2">
        <q-btn
          color="primary"
          icon="check"
          label="✓ Fertig - VERA erklären"
          size="lg"
          @click="close"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'

export default {
  name: 'DocumentReaderModal',
  
  props: {
    modelValue: Boolean,
    documentId: {
      type: Number,
      required: true
    }
  },
  
  emits: ['update:modelValue', 'close'],
  
  setup(props, { emit }) {
    const $q = useQuasar()
    
    const show = computed({
      get: () => props.modelValue,
      set: (val) => emit('update:modelValue', val)
    })
    
    const loading = ref(false)
    const error = ref(null)
    const documentUrl = ref(null)
    const documentName = ref('Dokument')
    
    const loadDocument = async () => {
      loading.value = true
      error.value = null
      
      try {
        // Get document metadata
        const metaResponse = await fetch(`/api/documents/${props.documentId}`)
        if (!metaResponse.ok) throw new Error(`HTTP ${metaResponse.status}`)
        const metaData = await metaResponse.json()
        documentName.value = metaData.filename || 'Dokument'
        
        // Build PDF URL
        // Note: Using blob URL for better security
        const pdfResponse = await fetch(`/api/documents/${props.documentId}/download`)
        if (!pdfResponse.ok) throw new Error(`HTTP ${pdfResponse.status}`)
        
        const blob = await pdfResponse.blob()
        documentUrl.value = URL.createObjectURL(blob)
        
      } catch (err) {
        console.error('Failed to load document:', err)
        error.value = 'Dokument konnte nicht geladen werden'
      } finally {
        loading.value = false
      }
    }
    
    const downloadDocument = async () => {
      try {
        const response = await fetch(`/api/documents/${props.documentId}/download`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        
        // Create download link
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = documentName.value
        link.click()
        
        URL.revokeObjectURL(url)
        
        $q.notify({
          type: 'positive',
          message: 'Download gestartet',
          icon: 'download'
        })
        
      } catch (err) {
        console.error('Download failed:', err)
        $q.notify({
          type: 'negative',
          message: 'Download fehlgeschlagen',
          caption: err.message
        })
      }
    }
    
    const close = () => {
      // Clean up blob URL
      if (documentUrl.value) {
        URL.revokeObjectURL(documentUrl.value)
        documentUrl.value = null
      }
      
      emit('close')
      emit('update:modelValue', false)
    }
    
    // Load document when dialog opens
    watch(() => props.modelValue, (newVal) => {
      if (newVal && props.documentId) {
        loadDocument()
      }
    }, { immediate: true })
    
    return {
      show,
      loading,
      error,
      documentUrl,
      documentName,
      loadDocument,
      downloadDocument,
      close
    }
  }
}
</script>

<style scoped>
/* Ensure iframe fills available space */
iframe {
  height: calc(100vh - 120px); /* Account for header and footer */
}
</style>
