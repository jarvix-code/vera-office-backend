# VERA Office Frontend

iPad-optimiertes Dokumentenmanagement-System mit Vue 3 + TypeScript + Quasar Framework.

## 🚀 Quick Start

```bash
# Dependencies installieren (falls nicht bereits geschehen)
npm install

# Development Server starten
npm run dev

# Production Build
npm run build

# Preview Production Build
npm run preview
```

## 🌐 Zugriff

- **Development**: http://localhost:5173
- **Backend API**: http://localhost:8000 (wird automatisch proxied)

## 📱 Features

### Seiten
- **Dashboard** - Übersicht, Statistiken, Schnellzugriff
- **Dokument erfassen** - Kamera-Integration für Foto-Aufnahme
- **Dokumente** - Kartenansicht aller Dokumente mit Filter & Suche
- **Dokumentansicht** - PDF-Viewer mit Metadaten
- **Suche** - Natürliche Sprachsuche über alle Dokumente
- **Onboarding** - Setup-Wizard für Ersteinrichtung
- **Aufgaben** - Workflow-Management (in Entwicklung)
- **Export** - Backup & Export-Funktionen (in Entwicklung)
- **Einstellungen** - System-Konfiguration

### Technologien
- **Vue 3** - Composition API mit TypeScript
- **Quasar Framework** - UI-Components für iPad
- **Pinia** - State Management
- **Axios** - API-Client mit Interceptors
- **Vue Router** - Navigation mit Guards
- **Vite** - Build-Tool & Dev-Server

## 🎨 Design

### iPad-Optimierung
- Touch-Targets min. 44px
- Sidebar-Navigation (collapsible)
- Clean & Professional UI
- Weiß/Grau Basis + Blau (#1976D2) als Primärfarbe

### Responsive
- Minimum: 1024x768 (iPad)
- Breakpoints für Tablet & Desktop

## 📦 Projektstruktur

```
frontend/
├── public/
│   └── manifest.json         # PWA Manifest
├── src/
│   ├── views/               # Seiten-Components
│   │   ├── DashboardView.vue
│   │   ├── CaptureView.vue
│   │   ├── DocumentsView.vue
│   │   ├── DocumentDetailView.vue
│   │   ├── SearchView.vue
│   │   ├── OnboardingView.vue
│   │   ├── TasksView.vue
│   │   ├── ExportView.vue
│   │   └── SettingsView.vue
│   ├── stores/              # Pinia Stores
│   │   ├── documents.ts
│   │   └── onboarding.ts
│   ├── services/            # API Services
│   │   └── api.ts
│   ├── router/              # Vue Router
│   │   └── index.ts
│   ├── App.vue              # Root Component mit Layout
│   ├── main.ts              # Entry Point
│   └── quasar-variables.sass
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## 🔌 API Integration

Das Frontend kommuniziert mit dem Backend unter `http://localhost:8000`. 

Alle API-Calls werden durch Vite Proxy geleitet:
```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

### Verfügbare Endpoints (via services/api.ts)

#### Dokumente
- `POST /api/documents/upload` - Dokument hochladen
- `GET /api/documents/list` - Alle Dokumente
- `GET /api/documents/:id` - Einzelnes Dokument
- `GET /api/documents/:id/download` - Download
- `DELETE /api/documents/:id` - Löschen
- `GET /api/documents/search/query?q=...` - Suche

#### Onboarding
- `GET /api/onboarding/status` - Status prüfen
- `POST /api/onboarding/step1` - Unternehmensprofil
- `GET /api/onboarding/step2/suggestions` - Vorschläge
- `POST /api/onboarding/step2` - Kategorien
- `POST /api/onboarding/step3` - Netzwerk
- `POST /api/onboarding/complete` - Abschließen

#### System
- `GET /api/system/status` - System-Status
- `GET /api/system/stats` - Statistiken

## 🛠️ Development

### Voraussetzungen
- Node.js >= 18
- npm >= 9
- Backend läuft auf Port 8000

### Hot Module Replacement
Vite bietet automatisches Neuladen bei Datei-Änderungen.

### TypeScript
Strikte Type-Checks sind aktiviert. Bei Build-Fehlern:
```bash
npm run build
```

## 📱 PWA

Das Frontend ist PWA-ready:
- `manifest.json` in `/public`
- Service Worker (kann später aktiviert werden)
- Install-Funktion auf iPad möglich

## 🎯 Nächste Schritte

1. **Icons** - Favicon und PWA-Icons erstellen
2. **Service Worker** - Offline-Funktionalität
3. **E2E Tests** - Playwright oder Cypress
4. **Erweiterte Features**:
   - Drag & Drop für Uploads
   - Batch-Operations
   - OCR-Vorschau während Upload
   - PDF-Annotation

## 📝 Notizen

- Kamera-Zugriff benötigt HTTPS in Production (oder localhost)
- Für iPad-Tests: Über Netzwerk erreichbar machen mit `npm run dev -- --host`
- Backend-Proxy funktioniert nur im Dev-Modus

## 🐛 Troubleshooting

### Port 5173 bereits belegt
```bash
# Anderen Port verwenden
npm run dev -- --port 5174
```

### Backend nicht erreichbar
```bash
# Backend Status prüfen
curl http://localhost:8000/health
```

### Build-Fehler
```bash
# Dependencies neu installieren
rm -rf node_modules package-lock.json
npm install
```

---

**VERA Office** - Dokumentenmanagement leicht gemacht 📄✨
