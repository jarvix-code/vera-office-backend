# VERA QM RAG - Next Steps

**Status:** Frontend fertig ✅ | Backend-Tests ausstehend ⏳

---

## Sofort (vor dem ersten Test):

### 1. Backend RAG Engine starten
```bash
cd C:\Jarvix\vera-office\backend
python -m backend.core.rag_engine
```

**Prüfen:**
- [ ] Modell geladen? (paraphrase-multilingual-mpnet-base-v2)
- [ ] ChromaDB verbunden?
- [ ] SQLite DB gefunden?

---

### 2. QM-Dokumente indexieren
```bash
curl -X POST http://localhost:8001/api/qm/index \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"force": false}'
```

**Erwartung:**
- Dauer: ~2-3 Minuten für 750 Dokumente
- Status: "completed"
- indexed_count: 750

**Prüfen:**
- [ ] Indexierung erfolgreich?
- [ ] Keine failed_count?
- [ ] ChromaDB Collection erstellt?

---

### 3. Stats-Endpoint testen
```bash
curl -X GET http://localhost:8001/api/qm/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Erwartung:**
```json
{
  "indexed_documents": 750,
  "index_coverage": "100.0%"
}
```

**Prüfen:**
- [ ] Stats korrekt?
- [ ] 100% Coverage?

---

### 4. Search-Endpoint testen
```bash
curl -X POST http://localhost:8001/api/qm/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "Hygieneplan Desinfektion",
    "top_k": 5
  }'
```

**Erwartung:**
- 5 Ergebnisse
- Relevanz-Score > 0.5
- Preview-Text vorhanden

**Prüfen:**
- [ ] Ergebnisse sinnvoll?
- [ ] Performance < 2s?

---

## Dann (Frontend-Test):

### 5. Frontend Dev-Server starten
```bash
cd C:\Jarvix\vera-office\frontend
npm run dev
```

**URL:** http://localhost:5173

**Prüfen:**
- [ ] Server läuft?
- [ ] Login funktioniert?

---

### 6. Navigation testen
1. Einloggen (Admin-Account)
2. QM-Menü in Sidebar öffnen
3. "QM-Suche" klicken

**Prüfen:**
- [ ] Route /qm/search erreichbar?
- [ ] Seite lädt ohne Fehler?
- [ ] Suchfeld sichtbar?
- [ ] Beispiel-Queries als Chips?

---

### 7. Suche testen
1. Query eingeben: "Hygieneplan Desinfektion"
2. Enter drücken ODER Send-Button klicken

**Prüfen:**
- [ ] Loading-Spinner erscheint?
- [ ] Ergebnisse werden angezeigt?
- [ ] Relevanz-Score sichtbar? (Circular Progress)
- [ ] Preview-Text lesbar?
- [ ] Kategorie-Badge vorhanden?

---

### 8. Error-Handling testen
**Szenario A: Backend offline**
1. Backend stoppen
2. Suche ausführen

**Erwartung:**
- [ ] Error-Banner erscheint
- [ ] Fehlermeldung: "Suche fehlgeschlagen"

**Szenario B: Keine Ergebnisse**
1. Query: "asdfghjklqwertzuiop"
2. Enter

**Erwartung:**
- [ ] "Keine Ergebnisse gefunden"-State
- [ ] Icon + Text sichtbar

**Szenario C: Leere Query**
1. Query: "" (leer)
2. Enter

**Erwartung:**
- [ ] Suche wird NICHT ausgeführt
- [ ] Button disabled

---

### 9. Stats-Dialog testen
1. Info-Button (oben rechts) klicken

**Prüfen:**
- [ ] Dialog öffnet?
- [ ] Stats laden?
- [ ] Alle Felder gefüllt? (Modell, indexierte Docs, Coverage, etc.)
- [ ] Schließen-Button funktioniert?

---

### 10. Quick-Search testen
1. QM Dashboard öffnen (/qm)

**Prüfen:**
- [ ] Quick-Search Card sichtbar? (oben, lila)
- [ ] "Zur Suche"-Button vorhanden?
- [ ] Click → Route /qm/search?

---

## Danach (Mobile-Test):

### 11. iPad-Test
**Viewport:** 768x1024 (iPad Mini) oder 1024x1366 (iPad Pro)

**Browser DevTools:**
- F12 → Toggle Device Toolbar
- Wähle "iPad"

**Prüfen:**
- [ ] Suchfeld gut bedienbar? (Touch-Target groß genug)
- [ ] Ergebnisse scrollbar?
- [ ] Circular Progress lesbar?
- [ ] Navigation funktioniert?

---

## Abschließend (Deployment):

### 12. Produktiv-Build erstellen
```bash
cd C:\Jarvix\vera-office\frontend
npm run build
```

**Prüfen:**
- [ ] Build erfolgreich?
- [ ] Keine Fehler?

---

### 13. Frontend-Build nach Backend kopieren
```bash
cp -r dist/* ../backend/static/
```

**Prüfen:**
- [ ] Dateien kopiert?
- [ ] QmSearchView-*.js vorhanden?

---

### 14. Backend mit neuem Frontend starten
```bash
cd C:\Jarvix\vera-office\backend
python -m uvicorn main:app --reload
```

**Prüfen:**
- [ ] Backend läuft?
- [ ] Frontend unter http://localhost:8001/ erreichbar?
- [ ] QM-Suche funktioniert?

---

### 15. Installer-Package erstellen
**TODO:** Installer-Scripte aktualisieren

**Prüfen:**
- [ ] Frontend-Build enthalten?
- [ ] RAG Engine enthalten?
- [ ] ChromaDB enthalten?
- [ ] Sentence-Transformers Modell enthalten?

---

### 16. USB-Stick-Test (Rule #50)
1. Installer auf USB-Stick kopieren
2. Praxis-PC (ohne Internet)
3. Installer ausführen

**Prüfen:**
- [ ] Installation erfolgreich?
- [ ] VERA startet?
- [ ] QM-Suche funktioniert offline?

---

## Troubleshooting-Guide

**Problem → Lösung**

| Problem | Check | Fix |
|---------|-------|-----|
| No results | Dokumente indexiert? | `POST /api/qm/index` |
| Search failed | Backend läuft? | `python -m uvicorn main:app` |
| 401 Error | Token gültig? | Neu einloggen |
| 403 Error | QM-Modul lizenziert? | Admin-Account verwenden |
| Langsame Suche | top_k zu hoch? | Auf 5 reduzieren |
| Frontend 404 | Build kopiert? | `cp -r dist/* ../backend/static/` |

---

## Checkliste für Boris

**Vor dem ersten Test:**
- [ ] Backend RAG Engine gestartet
- [ ] QM-Dokumente indexiert (750 Docs)
- [ ] Stats-Endpoint gibt 100% Coverage
- [ ] Search-Endpoint funktioniert (curl)

**Frontend-Test:**
- [ ] Dev-Server läuft
- [ ] Login funktioniert
- [ ] Navigation zu /qm/search
- [ ] Suche liefert Ergebnisse
- [ ] Relevanz-Score sichtbar
- [ ] Error-Handling funktioniert
- [ ] Stats-Dialog öffnet
- [ ] Quick-Search im Dashboard

**Deployment:**
- [ ] Produktiv-Build erstellt
- [ ] Frontend nach Backend kopiert
- [ ] Backend mit neuem Frontend läuft
- [ ] Installer-Package erstellt
- [ ] USB-Stick-Test erfolgreich

---

## Support

**Dokumentation:**
- `QM_RAG_FRONTEND.md` - Vollständige Doku
- `QM_RAG_ARCHITECTURE.md` - Architektur
- `TEST_QM_RAG.md` - Test-Anleitung
- `QM_RAG_SUMMARY.md` - Abschlussbericht

**Logs:**
- Frontend: Browser Console (F12)
- Backend: `backend/logs/vera.log`

**Kontakt:**
- Bei Problemen: Logs prüfen + Error-Message
- Bei Fragen: Doku lesen + TEST_QM_RAG.md

---

**Erfolg = Alle Checkboxen ✅**

**Dann:** VERA QM RAG ist READY FOR PRODUCTION! 🚀
