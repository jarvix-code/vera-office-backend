# VERA 3-Spalten-Layout - Implementation Guide

## 🎯 Änderung
Fundamentaler Layout-Umbau gemäß Boris' Anforderung:
> "VERA muss auf jeder Seite sichtbar sein: Rechts 1/3, Kacheln 1/3, Sidebar 1/3"

## 📐 Layout-Struktur

### Desktop (≥1024px)
```
┌─────────────────────────────────────────────────┐
│ Sidebar (33%) │ Content (33%) │ VERA Chat (33%) │
│               │               │ (permanent!)    │
└─────────────────────────────────────────────────┘
```

### Tablet (768-1023px)
```
┌────────────────────────────────┐
│ Content (50%) │ VERA Chat (50%) │
│ Sidebar: Toggle/Hamburger      │
└────────────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────┐
│ Content (100%)   │
│ Sidebar: Toggle  │
│ VERA: Floating   │
│ Button (unten)   │
└──────────────────┘
```

## 📦 Geänderte/Neue Dateien

### 1. **src/App.vue** (UMGEBAUT)
- 3-Spalten-Layout mit Quasar Drawers
- Responsive Widths (33% Desktop, variabel Tablet/Mobile)
- Left Drawer: Navigation (Dokumentenverwaltung, ERP, QM)
- Right Drawer: VERA Chat Panel (permanent auf Desktop!)
- Content: Zentriert zwischen beiden Sidebars
- Floating VERA Button für Mobile

**Wichtige Computed Properties:**
```javascript
const sidebarWidth = computed(() => {
  if ($q.screen.lt.md) return 250        // Mobile
  if ($q.screen.lt.lg) return 280        // Tablet
  return Math.floor($q.screen.width / 3) // Desktop: 33%
})

const veraWidth = computed(() => {
  if ($q.screen.lt.md) return $q.screen.width  // Mobile: Full-Screen
  if ($q.screen.lt.lg) return 350              // Tablet
  return Math.floor($q.screen.width / 3)       // Desktop: 33%
})

const contentStyle = computed(() => {
  if ($q.screen.lt.lg) {
    return { padding: '16px', maxWidth: '100%' }
  }
  
  const leftWidth = sidebarWidth.value
  const rightWidth = veraWidth.value
  
  return {
    marginLeft: `${leftWidth}px`,
    marginRight: `${rightWidth}px`,
    padding: '24px',
    maxWidth: `${$q.screen.width - leftWidth - rightWidth}px`,
    minWidth: '400px'
  }
})
```

### 2. **src/components/VeraChatPanel.vue** (NEU)
Vollständige Chat-Komponente mit:
- ✅ Chat-Historie (q-chat-message)
- ✅ Input-Feld (autogrow, Enter zum Senden)
- ✅ Typing Indicator (Spinner + "VERA tippt...")
- ✅ Avatar (purple-4, icon: auto_awesome)
- ✅ Empty State (wenn keine Messages)
- ✅ Quick Actions (Buttons für häufige Anfragen)
- ✅ Auto-Scroll to Bottom
- ✅ API Integration: `/api/agent/chat`
- ✅ Error Handling (Notifications)
- ✅ Mobile: Close-Button + Full-Screen Overlay

**API Call:**
```javascript
const response = await fetch('/api/agent/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    message: userInput,
    context: {
      source: 'vera-chat-panel',
      timestamp: new Date().toISOString()
    }
  })
})
```

### 3. **src/assets/three-column-layout.css** (NEU)
Globale CSS-Anpassungen für schmalen Content-Bereich:
- ✅ Desktop: Alle Grids → Single-Column erzwungen
- ✅ Kacheln kompakter
- ✅ Tabellen: Kleinere Schrift
- ✅ Formulare: Single-Column bevorzugen
- ✅ Charts: Niedrigere Höhe (250px)
- ✅ Responsive Title-Größen
- ✅ Tablet: 2-Spalten-Grids wo sinnvoll
- ✅ Mobile: Full Single-Column

**Wichtige CSS-Klassen:**
```css
@media (min-width: 1024px) {
  .dashboard-page .info-grid,
  .document-grid,
  .stats-grid,
  .card-grid {
    grid-template-columns: 1fr !important;
  }
}
```

### 4. **src/main.ts** (ERWEITERT)
CSS-Import hinzugefügt:
```typescript
import './assets/three-column-layout.css'
```

## 🔌 API-Integration

### Backend-Endpoint (bereits vorhanden!)
- **Datei:** `backend/api/agent.py`
- **Route:** `POST /api/agent/chat`
- **Request:**
  ```json
  {
    "message": "Was sind meine offenen Aufgaben?",
    "session_id": "default"
  }
  ```
- **Response:**
  ```json
  {
    "response": "Du hast 3 offene Aufgaben...",
    "suggestions": ["Dokument X klassifizieren", "..."],
    "actions": [{"type": "navigate", "target": "/tasks"}]
  }
  ```

### Frontend-Integration
- Komponente sendet Nachricht → Backend `/api/agent/chat`
- Backend nutzt `backend.core.ai.agent`
- Response wird als Chat-Message angezeigt
- Suggestions werden als Quick-Action-Buttons gerendert

## 🎨 Design-Details

### Farben
- **VERA Avatar:** `purple-4` (#A78BFA)
- **User Messages:** `purple-4` Background, White Text
- **VERA Messages:** `grey-3` Background, Dark Text
- **Typing Indicator:** `purple-4` Spinner

### Spacing
- **Chat Messages:** `q-mb-md` (16px)
- **Chat Input:** 16px Padding
- **Quick Actions:** 4px Gap

### Mobile UX
- **Floating Button:** Bottom-Right (18px offset)
- **Badge:** Zeigt ungelesene Messages (rot)
- **Pulse Animation:** Bei ungelesenen Messages
- **Full-Screen Overlay:** Chat nimmt gesamten Screen ein

## 🧪 Testing

### Test-Schritte
1. **Desktop (≥1024px):**
   - [ ] Alle 3 Spalten sichtbar (33% je)
   - [ ] VERA Chat permanent rechts
   - [ ] Content zentriert
   - [ ] Kacheln Single-Column
   - [ ] Navigation funktioniert

2. **Tablet (768-1023px):**
   - [ ] Sidebar: Hamburger-Menu
   - [ ] Content + VERA: 50/50
   - [ ] VERA Chat funktioniert

3. **Mobile (<768px):**
   - [ ] Nur Content sichtbar
   - [ ] Floating VERA Button (unten rechts)
   - [ ] Button → Full-Screen Chat
   - [ ] Close-Button funktioniert

4. **VERA Chat:**
   - [ ] Message senden funktioniert
   - [ ] Typing Indicator erscheint
   - [ ] Response wird angezeigt
   - [ ] Scroll to Bottom funktioniert
   - [ ] Quick Actions funktionieren
   - [ ] Error Handling (wenn Backend offline)

### Dev Server starten
```bash
cd frontend
npm run dev
```

### Build testen
```bash
cd frontend
npm run build
```

## 🚀 Deployment

### Produktions-Build
```bash
cd frontend
npm run build
```

### Dateien landen in:
```
frontend/dist/
```

### Backend serviert Frontend:
- Route: `/*` (catch-all)
- Statische Dateien aus `frontend/dist`

## 📊 Success Criteria

✅ 3-Spalten-Layout (33/33/33) auf Desktop  
✅ VERA Chat permanent sichtbar (rechts)  
✅ Sidebar links (33%)  
✅ Content zentriert (33%)  
✅ Mobile: VERA als Floating Button  
✅ Responsive Design funktioniert  
✅ Content-Breiten angepasst (Single-Column)  
✅ API-Integration funktioniert  
✅ Error Handling vorhanden  

## ⚠️ Breaking Changes

### View-Anpassungen nötig
Alle Views müssen für schmalen Content-Bereich optimiert werden:
- **Dashboard:** Grid → Single-Column
- **Documents:** Card-Grid → Single-Column
- **Search:** Results → Single-Column
- **Tasks:** Task-Grid → Single-Column
- **Settings:** Settings-Grid → Single-Column

**Lösung:** Globale CSS (`three-column-layout.css`) erzwingt bereits Single-Column!

### Potenzielle Probleme
1. **Zu wenig Platz für Tabellen:**
   - Lösung: Horizontal Scroll aktiviert
   - Kleinere Schrift (0.875rem)

2. **Charts zu schmal:**
   - Lösung: Höhe reduziert (250px)
   - Responsive Width (100%)

3. **Formulare zu eng:**
   - Lösung: Single-Column erzwungen
   - Kleinere Labels

## 🔧 Troubleshooting

### Problem: VERA Chat zeigt "Internal Server Error"
- **Ursache:** Backend `/api/agent/chat` nicht erreichbar
- **Fix:** Backend starten, Logs prüfen

### Problem: 3-Spalten-Layout nicht sichtbar
- **Ursache:** Screen zu klein (<1024px)
- **Fix:** Zoom raus oder größeren Monitor nutzen

### Problem: Content zu schmal/unleserlich
- **Ursache:** Grid-Columns nicht angepasst
- **Fix:** CSS `three-column-layout.css` prüfen

### Problem: Floating Button überlappt Content
- **Ursache:** Z-Index-Konflikt
- **Fix:** `z-index: 3000` für Floating Button

## 📝 Nächste Schritte

1. **Backend VERA Agent verbessern:**
   - Bessere Suggestions
   - Context-Awareness (aktueller View)
   - Proaktive Hinweise

2. **Chat-Features erweitern:**
   - Voice Input (Mic-Button)
   - File Upload (Drag & Drop)
   - Rich Messages (Cards, Buttons)
   - Message History persistent speichern

3. **UX-Verbesserungen:**
   - Keyboard Shortcuts (Cmd+K → VERA öffnen)
   - Mention-System (@VERA)
   - Notifications (wenn VERA antwortet)

4. **Mobile-Optimierung:**
   - Push-Notifications
   - Swipe-Gestures
   - Voice-First UI

## 👤 Kontakt
Bei Fragen/Problemen: Boris Reimers

---
**Last Updated:** 2026-03-28  
**Version:** 1.0.0  
**Status:** ✅ READY FOR TESTING
