# QM RAG Frontend - Test-Anleitung

## Schnelltest nach Deployment

### 1. Frontend prüfen
```bash
# Im Browser
http://localhost:5173/qm/search

# Erwartung:
- ✅ Seite lädt
- ✅ "QM-Wissensdatenbank" Header sichtbar
- ✅ Suchfeld vorhanden
- ✅ Beispiel-Queries als Chips
```

### 2. Navigation prüfen
```bash
# QM Menü in Sidebar öffnen
# Erwartung:
- ✅ "QM-Suche" Eintrag vorhanden
- ✅ Click → Route /qm/search
```

### 3. Dashboard prüfen
```bash
# http://localhost:5173/qm
# Erwartung:
- ✅ Quick-Search Card oben (lila Hintergrund)
- ✅ "Zur Suche" Button
- ✅ Click → Route /qm/search
```

### 4. Backend-API testen

**A) Stats abrufen:**
```bash
curl -X GET http://localhost:8001/api/qm/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Erwartung:**
```json
{
  "model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
  "indexed_documents": 750,
  "available_documents": 750,
  "index_coverage": "100.0%"
}
```

**B) Search testen:**
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
```json
{
  "query": "Hygieneplan Desinfektion",
  "results": [
    {
      "doc_id": 123,
      "filename": "Hygieneplan_2024.pdf",
      "category": "Hygiene",
      "preview": "Der Hygieneplan beschreibt...",
      "relevance_score": 0.89
    }
  ],
  "result_count": 5
}
```

### 5. E2E Test (Frontend → Backend)

1. **Login:**
   - http://localhost:5173/login
   - Admin-Account einloggen

2. **Navigation:**
   - QM Menü → "QM-Suche"

3. **Suche ausführen:**
   - Query eingeben: "Hygieneplan Desinfektion"
   - Enter drücken ODER Send-Button klicken

4. **Ergebnis prüfen:**
   - ✅ Loading-Spinner erscheint
   - ✅ Ergebnisse werden angezeigt
   - ✅ Relevanz-Score sichtbar (Circular Progress)
   - ✅ Preview-Text vorhanden
   - ✅ Kategorie-Badge sichtbar

5. **Fehlerfall testen:**
   - Backend stoppen
   - Suche ausführen
   - ✅ Error-Banner erscheint mit Fehlermeldung

### 6. Mobile-Test (iPad)

**Responsive Layout:**
- ✅ Touch-Targets groß genug (min. 44x44px)
- ✅ Suchfeld auf Tablet gut bedienbar
- ✅ Ergebnisse scrollbar
- ✅ Circular Progress gut lesbar

**Viewport-Tests:**
```
iPad Mini (768x1024)
iPad Pro (1024x1366)
```

### 7. Performance-Test

**Query-Response-Time:**
```bash
# Mit curl und time messen
time curl -X POST http://localhost:8001/api/qm/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "Hygieneplan", "top_k": 5}'
```

**Erwartung:**
- < 2 Sekunden für 5 Ergebnisse
- < 5 Sekunden für 20 Ergebnisse

### 8. Indexierung testen

**Initial-Index erstellen:**
```bash
curl -X POST http://localhost:8001/api/qm/index \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"force": false}'
```

**Erwartung:**
```json
{
  "status": "completed",
  "indexed_count": 750,
  "failed_count": 0,
  "total_documents": 750,
  "collection_count": 750
}
```

**Dauer:** Ca. 2-3 Minuten für 750 Dokumente

### 9. Fehlerszenarien

**A) Keine Ergebnisse:**
- Query: "asdfghjklqwertzuiop"
- ✅ "Keine Ergebnisse gefunden" State

**B) Leere Query:**
- Query: "" (leer)
- ✅ Suche wird nicht ausgeführt
- ✅ Button disabled

**C) Backend offline:**
- Backend stoppen
- Query ausführen
- ✅ Error-Banner: "Suche fehlgeschlagen"

**D) Nicht authentifiziert:**
- Ohne Token suchen
- ✅ 401 → Redirect zu /login

**E) QM-Modul nicht lizenziert:**
- Lizenz entfernen
- Route /qm/search aufrufen
- ✅ Redirect zu /module-teaser/qm

### 10. Browser-Kompatibilität

Testen in:
- ✅ Chrome (Desktop + Mobile)
- ✅ Firefox
- ✅ Safari (macOS + iOS)
- ✅ Edge

## Troubleshooting

### Problem: "No results found"
**Check:**
1. Sind Dokumente indexiert? `GET /api/qm/stats`
2. Ist RAG Engine gestartet?
3. ChromaDB Collection vorhanden?

**Fix:**
```bash
POST /api/qm/index {"force": true}
```

### Problem: "Search failed"
**Check:**
1. Backend läuft? `curl http://localhost:8001/api/system/status`
2. Auth Token gültig?
3. Browser Console → Network Tab → 500er Error?

**Fix:**
- Backend-Logs prüfen
- `backend/logs/vera.log`

### Problem: Langsame Suche (> 10s)
**Check:**
1. Wie viele Dokumente? `GET /api/qm/stats`
2. Hardware? (CPU, RAM)
3. top_k zu hoch? (> 20)

**Fix:**
- top_k reduzieren (default: 5)
- Hardware upgraden
- Index-Optimierung

### Problem: Frontend-Build fehlschlägt
**Check:**
```bash
cd frontend
npm install
npm run build
```

**Häufige Fehler:**
- Node-Version? (empfohlen: v24.x)
- Dependencies? `npm ci`
- TypeScript-Errors? `npm run type-check`

## Success Checklist

- [ ] Frontend kompiliert (`npm run build`)
- [ ] Route `/qm/search` erreichbar
- [ ] Navigation zeigt "QM-Suche"
- [ ] Dashboard hat Quick-Search Card
- [ ] API `/api/qm/search` antwortet
- [ ] API `/api/qm/stats` antwortet
- [ ] Suche liefert Ergebnisse
- [ ] Relevanz-Score wird angezeigt
- [ ] Loading-State funktioniert
- [ ] Error-Handling funktioniert
- [ ] Mobile-Layout OK (iPad)
- [ ] Performance < 2s pro Query
- [ ] Beispiel-Queries sichtbar
- [ ] Stats-Dialog öffnet

## Next Steps nach erfolgreichen Tests

1. **Dokument-Navigation implementieren:**
   - Click auf Ergebnis → Dokument öffnen
   - PDF-Viewer oder Detail-View

2. **Beispiel-Queries funktional machen:**
   - Click auf Chip → Suche triggern

3. **Category-Filter UI:**
   - Dropdown für Kategorie-Auswahl

4. **Produktiv-Deployment:**
   - Frontend-Build nach `backend/static/`
   - Installer-Package erstellen
   - USB-Stick-Test (Rule #50)

## Kontakt bei Problemen

- Logs: `backend/logs/vera.log`
- Frontend Console: Browser DevTools
- Backend Status: `GET /api/system/status`
