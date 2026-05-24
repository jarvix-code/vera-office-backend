# VERA Office — QA Checkliste

## Nach JEDEM Build / Sprint durchlaufen!

### 🔗 Navigation & Links
- [ ] Sidebar: Jeder Menüpunkt führt zur richtigen View
- [ ] Sidebar: Aktiver Menüpunkt ist visuell hervorgehoben
- [ ] Logo/Brand-Link → führt zu Startseite (Chat)
- [ ] Alle internen Router-Links funktionieren (kein 404, kein Whitescreen)
- [ ] Browser Zurück-Button funktioniert korrekt
- [ ] Deep-Links funktionieren (z.B. /documents/1 direkt aufrufen)

### 🔘 Buttons & Aktionen
- [ ] Alle Buttons haben Click-Handler
- [ ] Buttons zeigen Loading-State während API-Calls
- [ ] Disabled-State bei ungültigen Formularen
- [ ] Kein Button führt ins Leere / löst keinen Fehler aus
- [ ] "Abbrechen" / "Zurück" Buttons funktionieren

### 📱 iPad / Touch
- [ ] Alle Touch-Targets >= 44px
- [ ] Kein Hover-only Content (alles auch per Touch erreichbar)
- [ ] Keyboard erscheint bei Texteingaben
- [ ] Kein horizontales Scrollen
- [ ] Landscape + Portrait funktioniert

### 📡 API-Verbindungen
- [ ] Alle Frontend API-Calls gehen an /api/... (nicht localhost)
- [ ] Fehlerhandling bei API-Fehlern (Toast/Meldung, kein Whitescreen)
- [ ] Loading-Indicators bei Datenladen
- [ ] Leere States ("Noch keine Dokumente") statt leerer Seiten

### 🎨 Theme & Darstellung
- [ ] Violet Primary überall konsistent
- [ ] Dark Mode Toggle funktioniert
- [ ] Keine alten blauen Quasar-Defaults sichtbar
- [ ] Schrift lesbar (Inter Font geladen)
- [ ] Keine abgeschnittenen Texte

### 📄 Dokument-Pipeline
- [ ] Foto aufnehmen → Upload funktioniert
- [ ] OCR läuft durch (Text wird erkannt)
- [ ] PDF wird generiert und ist lesbar
- [ ] Originalbild wird aufbewahrt
- [ ] Qualitätsprüfung gibt Score
- [ ] Klassifizierung funktioniert (oder Fallback)
- [ ] Dokument erscheint in Dokumentenliste
- [ ] Dokument-Detail-View zeigt alle Infos

### 💬 Chat
- [ ] Nachrichten senden funktioniert
- [ ] VERA antwortet
- [ ] Chat-History bleibt erhalten
- [ ] Voice Input (Mikrofon-Button) funktioniert auf iPad
- [ ] Scroll-Verhalten korrekt (neueste unten)

### 🔍 Suche
- [ ] Suchfeld vorhanden und funktional
- [ ] Ergebnisse werden angezeigt
- [ ] Klick auf Ergebnis → Dokument-Detail

### ⚙️ Onboarding
- [ ] Frischer Start (DB leer) → Onboarding startet
- [ ] Alle Schritte durchklickbar
- [ ] Nach Abschluss → Hauptapp zugänglich
- [ ] Onboarding-Daten korrekt gespeichert

---
*Diese Checkliste nach JEDEM Build/Deploy durchgehen!*
*Sub-Agents: Führt diese Checks am Ende eurer Arbeit durch!*
