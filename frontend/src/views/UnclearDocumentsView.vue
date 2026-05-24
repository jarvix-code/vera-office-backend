<template>
  <q-page padding>
    <div class="q-mb-md">
      <h4 class="q-my-md">📋 Unklare Dokumente</h4>
      <p class="text-grey-7">
        Dokumente die noch nicht klassifiziert werden konnten.
      </p>
    </div>

    <!-- Status Tabs -->
    <q-tabs
      v-model="activeTab"
      dense
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="left"
    >
      <q-tab 
        name="user" 
        icon="person"
      >
        <div class="row items-center">
          <span>Braucht deine Hilfe</span>
          <q-badge 
            v-if="counts.needs_user_help > 0"
            color="red" 
            :label="counts.needs_user_help"
            class="q-ml-sm"
          />
        </div>
      </q-tab>
      
      <q-tab 
        name="dev" 
        icon="code"
      >
        <div class="row items-center">
          <span>Entwickler-Review</span>
          <q-badge 
            v-if="counts.needs_dev_review > 0"
            color="orange" 
            :label="counts.needs_dev_review"
            class="q-ml-sm"
          />
        </div>
      </q-tab>
      
      <q-tab 
        name="processing" 
        icon="sync"
      >
        <div class="row items-center">
          <span>OCR läuft</span>
          <q-badge 
            v-if="counts.processing > 0"
            color="blue" 
            :label="counts.processing"
            class="q-ml-sm"
          />
        </div>
      </q-tab>
    </q-tabs>

    <q-separator class="q-mb-md" />

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner color="primary" size="50px" />
    </div>

    <!-- Tab Panels -->
    <q-tab-panels v-else v-model="activeTab" animated>
      <!-- User Help Queue -->
      <q-tab-panel name="user">
        <div v-if="documents.needs_user_help.length === 0" class="text-center q-pa-xl text-grey-6">
          <q-icon name="check_circle" size="64px" color="positive" />
          <div class="q-mt-md text-h6">Keine offenen Dokumente</div>
          <div>Alle Dokumente sind klassifiziert! 🎉</div>
        </div>
        
        <q-list v-else separator>
          <q-item 
            v-for="doc in documents.needs_user_help" 
            :key="doc.id"
            clickable
            @click="helpDocument(doc)"
          >
            <q-item-section avatar>
              <q-avatar color="red" text-color="white" icon="help_outline" />
            </q-item-section>
            
            <q-item-section>
              <q-item-label>{{ doc.filename }}</q-item-label>
              <q-item-label caption>
                Wartet seit: {{ formatDate(doc.waiting_since) }}
              </q-item-label>
              <q-item-label caption v-if="doc.confidence">
                Confidence: {{ (doc.confidence * 100).toFixed(0) }}%
              </q-item-label>
            </q-item-section>
            
            <q-item-section side>
              <q-btn 
                color="primary" 
                label="Jetzt helfen" 
                @click.stop="helpDocument(doc)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- Developer Queue -->
      <q-tab-panel name="dev">
        <div v-if="documents.needs_dev_review.length === 0" class="text-center q-pa-xl text-grey-6">
          <q-icon name="done_all" size="64px" color="positive" />
          <div class="q-mt-md text-h6">Keine Developer-Reviews</div>
        </div>
        
        <q-list v-else separator>
          <q-item 
            v-for="doc in documents.needs_dev_review" 
            :key="doc.id"
          >
            <q-item-section avatar>
              <q-avatar color="orange" text-color="white" icon="code" />
            </q-item-section>
            
            <q-item-section>
              <q-item-label>{{ doc.filename }}</q-item-label>
              <q-item-label caption v-if="doc.user_comment">
                User-Kommentar: "{{ doc.user_comment }}"
              </q-item-label>
              <q-item-label caption>
                Wartet seit: {{ formatDate(doc.waiting_since) }}
              </q-item-label>
            </q-item-section>
            
            <q-item-section side>
              <q-btn 
                outline
                color="orange" 
                label="Review" 
                @click="reviewDocument(doc)"
                disabled
              >
                <q-tooltip>
                  Nur für Entwickler verfügbar
                </q-tooltip>
              </q-btn>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- Processing Queue -->
      <q-tab-panel name="processing">
        <div v-if="documents.processing.length === 0" class="text-center q-pa-xl text-grey-6">
          <q-icon name="check_circle" size="64px" color="positive" />
          <div class="q-mt-md text-h6">Keine Verarbeitung läuft</div>
        </div>
        
        <q-list v-else separator>
          <q-item 
            v-for="doc in documents.processing" 
            :key="doc.id"
          >
            <q-item-section avatar>
              <q-spinner color="blue" size="32px" />
            </q-item-section>
            
            <q-item-section>
              <q-item-label>{{ doc.filename }}</q-item-label>
              <q-item-label caption>
                OCR-Verarbeitung läuft...
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Active Learning Dialog -->
    <active-learning-dialog
      v-model="dialogOpen"
      :classification="currentClassification"
      :document-id="currentDocumentId"
      :document-name="currentDocumentName"
      @confirmed="onDocumentHelped"
      @skipped="onSkipped"
      @escalated="onEscalated"
    />
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { formatDistanceToNow } from 'date-fns'
import { de } from 'date-fns/locale'
import ActiveLearningDialog from '@/components/ActiveLearningDialog.vue'

export default {
  name: 'UnclearDocumentsView',
  
  components: {
    ActiveLearningDialog
  },
  
  setup() {
    const $q = useQuasar()
    
    const activeTab = ref('user')
    const loading = ref(false)
    const documents = ref({
      needs_user_help: [],
      needs_dev_review: [],
      processing: []
    })
    const counts = ref({
      needs_user_help: 0,
      needs_dev_review: 0,
      processing: 0
    })
    
    // Active Learning Dialog State
    const dialogOpen = ref(false)
    const currentClassification = ref(null)
    const currentDocumentId = ref(null)
    const currentDocumentName = ref('')
    
    const loadDocuments = async () => {
      loading.value = true
      
      try {
        const response = await fetch('/api/active-learning/unclear-documents')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        
        documents.value = data.by_status
        counts.value = data.counts
        
      } catch (error) {
        console.error('Failed to load unclear documents:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler beim Laden der Dokumente',
          caption: error.message
        })
      } finally {
        loading.value = false
      }
    }
    
    const helpDocument = async (doc) => {
      try {
        // Classify document with Active Learning
        const response = await fetch('/api/active-learning/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doc_id: doc.id,
            user_name: 'Boris' // TODO: Get from auth
          })
        })
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        
        const data = await response.json()
        
        if (data.action === 'auto_classified') {
          // Already classified!
          $q.notify({
            type: 'positive',
            message: 'Dokument wurde automatisch klassifiziert',
            caption: `Kategorie: ${data.category}`
          })
          
          // Reload list
          await loadDocuments()
          
        } else {
          // Needs confirmation → Open dialog
          currentDocumentId.value = doc.id
          currentDocumentName.value = doc.filename
          currentClassification.value = {
            frage: data.frage,
            vorschlag: data.vorschlag,
            alternativen: data.alternativen,
            confidence: doc.confidence || 0.5
          }
          
          dialogOpen.value = true
        }
        
      } catch (error) {
        console.error('Failed to classify document:', error)
        $q.notify({
          type: 'negative',
          message: 'Fehler bei Klassifikation',
          caption: error.message
        })
      }
    }
    
    const reviewDocument = (doc) => {
      // TODO: Implement developer review
      $q.notify({
        type: 'info',
        message: 'Developer-Review noch nicht implementiert'
      })
    }
    
    const onDocumentHelped = () => {
      $q.notify({
        type: 'positive',
        message: 'Danke für deine Hilfe!',
        icon: 'thumb_up'
      })
      
      // Reload list
      loadDocuments()
    }
    
    const onSkipped = () => {
      // Just reload list
      loadDocuments()
    }
    
    const onEscalated = () => {
      // Reload list
      loadDocuments()
    }
    
    const formatDate = (dateStr) => {
      if (!dateStr) return 'unbekannt'
      
      try {
        const date = new Date(dateStr)
        return formatDistanceToNow(date, { addSuffix: true, locale: de })
      } catch {
        return dateStr
      }
    }
    
    onMounted(() => {
      loadDocuments()
    })
    
    return {
      activeTab,
      loading,
      documents,
      counts,
      dialogOpen,
      currentClassification,
      currentDocumentId,
      currentDocumentName,
      loadDocuments,
      helpDocument,
      reviewDocument,
      onDocumentHelped,
      onSkipped,
      onEscalated,
      formatDate
    }
  }
}
</script>

<style scoped>
/* No custom styles needed */
</style>
