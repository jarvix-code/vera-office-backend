# QM RAG Frontend - Architektur

## System-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                       VERA Office                           │
│                    QM RAG System                            │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│   QM Dashboard   │────────▶│   QM Search View │
│                  │         │                  │
│ Quick-Search Card│         │  Search Input    │
│ "Zur Suche" Btn  │         │  Results List    │
└──────────────────┘         │  Example Queries │
                             │  Stats Dialog    │
                             └─────────┬────────┘
                                       │
                                       │ uses
                                       ▼
                             ┌──────────────────┐
                             │  QMSearch.vue    │
                             │  (Component)     │
                             │                  │
                             │  • Input Field   │
                             │  • Loading State │
                             │  • Results List  │
                             │  • Error Banner  │
                             └─────────┬────────┘
                                       │
                                       │ calls
                                       ▼
                             ┌──────────────────┐
                             │    qmApi         │
                             │  (API Service)   │
                             │                  │
                             │  .search()       │
                             │  .index()        │
                             │  .getStats()     │
                             │  .getDocument()  │
                             └─────────┬────────┘
                                       │
                                       │ HTTP POST/GET
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend API Layer                        │
│                  /api/qm/search                             │
│                  /api/qm/index                              │
│                  /api/qm/stats                              │
│                  /api/qm/document/{id}                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ uses
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Engine Core                          │
│              backend/core/rag_engine.py                     │
│                                                             │
│  • Sentence Transformers (Embedding Model)                 │
│  • ChromaDB (Vector Store)                                 │
│  • SQLite (Document Metadata)                              │
│                                                             │
│  Methods:                                                   │
│  • search(query, top_k, category_filter)                   │
│  • index_documents(force)                                  │
│  • get_stats()                                             │
│  • get_document_by_id(doc_id)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow - Search Query

```
User Input: "Hygieneplan Desinfektion"
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. QMSearch.vue                            │
│    - Trigger search()                      │
│    - Set loading = true                    │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ 2. qmApi.search()                          │
│    POST /api/qm/search                     │
│    Body: {                                 │
│      query: "Hygieneplan Desinfektion",    │
│      top_k: 5                              │
│    }                                       │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ 3. Backend API (qm_search.py)             │
│    - Validate request                      │
│    - Check auth (Bearer Token)             │
│    - Call RAG Engine                       │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ 4. RAG Engine (rag_engine.py)             │
│    a) Embed query with SentenceTransformer │
│       "Hygieneplan Desinfektion"           │
│       → 768-dim vector                     │
│    b) Search ChromaDB (cosine similarity)  │
│    c) Fetch metadata from SQLite           │
│    d) Rank by relevance_score              │
│    e) Return top 5 results                 │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ 5. Backend Response                        │
│    {                                       │
│      query: "Hygieneplan Desinfektion",    │
│      results: [                            │
│        {                                   │
│          doc_id: 123,                      │
│          filename: "Hygieneplan_2024.pdf", │
│          category: "Hygiene",              │
│          preview: "Der Hygieneplan...",    │
│          distance: 0.234,                  │
│          relevance_score: 0.89             │
│        },                                  │
│        ...                                 │
│      ],                                    │
│      result_count: 5,                      │
│      top_k: 5                              │
│    }                                       │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ 6. QMSearch.vue                            │
│    - Set loading = false                   │
│    - Update results[] array                │
│    - Render q-list with:                   │
│      • Filename                            │
│      • Category badge                      │
│      • Preview text                        │
│      • Relevance score (circular progress) │
└────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
App.vue
├── q-drawer (Navigation)
│   └── QM Expansion Item
│       └── "QM-Suche" Link → /qm/search
│
└── q-page-container
    └── router-view
        │
        ├── QmDashboardView.vue
        │   └── Quick-Search Card
        │       └── Button → /qm/search
        │
        └── QmSearchView.vue
            ├── Page Header
            ├── QMSearch.vue (Component)
            │   ├── q-input (Search Field)
            │   ├── q-spinner-dots (Loading)
            │   ├── q-list (Results)
            │   │   └── q-item (Result Item)
            │   │       ├── Filename
            │   │       ├── Category Badge
            │   │       ├── Preview Text
            │   │       └── q-circular-progress (Score)
            │   └── q-banner (Error)
            │
            ├── Example Queries (Chips)
            └── Stats Dialog
                └── RAG Engine Info
```

---

## API Endpoints

### POST /api/qm/search
**Purpose:** Semantische Suche über QM-Dokumente

**Request:**
```json
{
  "query": "Hygieneplan Desinfektion",
  "top_k": 5,
  "category_filter": "Hygiene" // optional
}
```

**Response:**
```json
{
  "query": "Hygieneplan Desinfektion",
  "results": [
    {
      "doc_id": 123,
      "filename": "Hygieneplan_2024.pdf",
      "category": "Hygiene",
      "preview": "Der Hygieneplan beschreibt...",
      "distance": 0.234,
      "relevance_score": 0.89
    }
  ],
  "result_count": 5,
  "top_k": 5
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized (no token)
- 403: Forbidden (QM module not licensed)
- 500: Search failed (RAG Engine error)

---

### POST /api/qm/index
**Purpose:** Alle QM-Dokumente indexieren (Embeddings erstellen)

**Request:**
```json
{
  "force": false // true = re-index all
}
```

**Response:**
```json
{
  "status": "completed",
  "indexed_count": 750,
  "failed_count": 0,
  "total_documents": 750,
  "collection_count": 750,
  "message": "Indexing completed successfully"
}
```

**Duration:** ~2-3 Minuten für 750 Dokumente

---

### GET /api/qm/stats
**Purpose:** RAG Engine Statistiken

**Response:**
```json
{
  "model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
  "vector_store": "chromadb",
  "indexed_documents": 750,
  "available_documents": 750,
  "index_coverage": "100.0%",
  "embedding_dimension": 768,
  "chroma_path": "C:/Jarvix/vera-office/data/qm_chroma/",
  "db_path": "C:/Jarvix/vera-office/data/qm.db"
}
```

---

### GET /api/qm/document/{doc_id}
**Purpose:** Vollständiges Dokument abrufen

**Response:**
```json
{
  "id": 123,
  "filename": "Hygieneplan_2024.pdf",
  "ocr_text": "Der Hygieneplan...",
  "category": "Hygiene",
  "created_at": "2024-01-15T10:30:00",
  "file_path": "/data/qm_documents/Hygieneplan_2024.pdf"
}
```

---

## State Management

### QMSearch Component State
```typescript
const query = ref('')              // Search query
const results = ref([])            // Search results
const loading = ref(false)         // Loading state
const searched = ref(false)        // Has search been executed?
const error = ref<string | null>(null) // Error message
```

### QmSearchView State
```typescript
const showStats = ref(false)       // Stats dialog visible?
const stats = ref<any>(null)       // RAG engine stats
```

---

## Error Handling

```
User Action: Search Query
    │
    ▼
Try: qmApi.search()
    │
    ├─ Success (200)
    │  └─▶ Display results
    │
    ├─ 401 Unauthorized
    │  └─▶ Redirect to /login
    │
    ├─ 403 Forbidden (Module not licensed)
    │  └─▶ Redirect to /module-teaser/qm
    │
    └─ 500 Internal Server Error
       └─▶ Show error banner
           "Suche fehlgeschlagen: [detail]"
```

---

## Authentication Flow

```
1. User navigates to /qm/search
   │
   ▼
2. Router Guard checks:
   ├─ Is user authenticated? (authStore.isAuthenticated)
   │  └─ No → Redirect to /login
   │
   ├─ Is onboarding complete? (onboardingStore.isComplete)
   │  └─ No → Redirect to /
   │
   └─ Is QM module licensed? (requiresModule: 'qm')
      ├─ Admin? → Allow (override)
      └─ Module licensed? → Allow
         └─ Not licensed → Redirect to /module-teaser/qm

3. API calls include Bearer Token:
   Authorization: Bearer <token>
   (auto-injected by axios interceptor)
```

---

## Performance Considerations

### Frontend:
- **Lazy Loading:** QmSearchView only loaded when route accessed
- **Debouncing:** Could add debounce to search input (future)
- **Pagination:** Results limited to top_k (default: 5)

### Backend:
- **Indexing:** Pre-computed embeddings (no runtime embedding)
- **Vector Search:** ChromaDB optimized for cosine similarity
- **Caching:** Could cache frequent queries (future)

### Network:
- **Compression:** Gzip enabled (API responses)
- **Timeouts:** 30s timeout on API calls
- **Silent Polling:** Stats use `_silent: true` to avoid error toasts

---

## Security

### Authentication:
- ✅ Bearer Token required (localStorage)
- ✅ Token auto-injected by axios interceptor
- ✅ 401 → Auto-logout + redirect

### Authorization:
- ✅ QM module license check (router guard)
- ✅ Admin override for all modules
- ✅ Backend validates license on every API call

### Input Validation:
- ✅ Query length: 1-500 chars
- ✅ top_k range: 1-20
- ✅ Category filter: optional string

### SQL Injection:
- ✅ SQLAlchemy ORM (parameterized queries)
- ✅ No raw SQL concatenation

---

## Future Enhancements

### Priority P1:
1. **Document Navigation:**
   - Click on result → Open document
   - Route: `/qm/documents/{doc_id}` or PDF viewer

2. **Example Query Triggers:**
   - Click chip → Auto-fill + execute search
   - Via `ref` to QMSearch component

### Priority P2:
3. **Category Filter UI:**
   - Dropdown or chips for category selection
   - Backend already supports `category_filter`

4. **History/Recent Searches:**
   - LocalStorage for last 10 queries
   - Quick-access in Dashboard

5. **Export Results:**
   - PDF/CSV export of search results

6. **Auto-Complete:**
   - Suggestion dropdown during typing
   - Based on frequent queries

### Priority P3:
7. **Advanced Filters:**
   - Date range
   - File type
   - Author

8. **Saved Searches:**
   - User can save frequent queries
   - Quick-access menu

9. **Analytics:**
   - Track popular queries
   - Optimize indexing based on usage

---

## Dependencies

### Frontend:
- Vue 3.x
- Quasar 2.x
- Vue Router 4.x
- Axios (HTTP client)
- TypeScript

### Backend:
- FastAPI
- Pydantic (validation)
- sentence-transformers (embedding model)
- ChromaDB (vector store)
- SQLite (metadata)
- SQLAlchemy (ORM)

### Model:
- `paraphrase-multilingual-mpnet-base-v2`
- 768-dimensional embeddings
- Multilingual support (German optimized)

---

## Deployment Architecture

```
VERA Office (USB Stick / Installer)
│
├── Frontend (Static Build)
│   └── backend/static/
│       └── dist/
│           ├── index.html
│           ├── assets/
│           │   ├── QmSearchView-*.js
│           │   ├── QmSearchView-*.css
│           │   └── ...
│           └── ...
│
├── Backend (FastAPI)
│   └── api/
│       └── qm_search.py
│           └── /api/qm/search
│           └── /api/qm/index
│           └── /api/qm/stats
│
├── RAG Engine
│   └── core/
│       └── rag_engine.py
│
├── Data
│   ├── qm.db (SQLite)
│   └── qm_chroma/ (ChromaDB)
│
└── Models
    └── sentence-transformers/
        └── paraphrase-multilingual-mpnet-base-v2/
```

---

## Monitoring & Logging

### Frontend Console:
```javascript
console.log('[QM Search] Query:', query)
console.log('[QM Search] Results:', results)
console.error('[QM Search] Error:', error)
```

### Backend Logs:
```python
logger.info(f"Search query: {query}")
logger.info(f"Results: {len(results)}")
logger.error(f"Search failed: {e}")
```

**Log File:** `backend/logs/vera.log`

---

**Architektur-Dokumentation v1.0**  
Erstellt: 2026-03-28
