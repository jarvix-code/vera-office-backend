# Chat Authentication Fix - Test Plan

**Bug:** #11 - Chat komplett kaputt weil Frontend kein JWT Token sendet

## ✅ Implementierte Fixes

### 1. Backend: AuthMiddleware (auth_middleware.py)
- **Problem:** `/api/auth/chat` war NICHT in PUBLIC_ROUTES
- **Fix:** `/api/auth/chat` zu PUBLIC_ROUTES hinzugefügt
- **Grund:** Auth-Flow braucht public Endpoint um zu funktionieren
- **Zusatz:** Debug-Logging bei fehlenden Auth-Headern

### 2. Frontend: API Interceptor (services/api.ts)
- **Problem:** Interceptor hatte kein Debug-Logging
- **Fix:** 
  - Debug-Logging wenn Token vorhanden ist
  - Warning wenn Token fehlt
  - Explizites Löschen von Authorization-Header wenn kein Token
- **Zweck:** Diagnostik warum Token nicht ankommt

### 3. Frontend: Auth Store (stores/auth.ts)
- **Problem:** Kein Logging ob Token gespeichert wird
- **Fix:**
  - Logging beim Login (Token gespeichert)
  - Logging beim Init (Token aus localStorage geladen)
  - Zusätzliche Null-Checks
- **Zweck:** Diagnostik der Token-Speicherung

## 📋 Test Flow

### Szenario 1: Nicht-eingeloggter User (Auth-Flow)
**Erwartung:** Conversational Auth funktioniert

1. Öffne VERA Office im Browser
2. **NICHT** einloggen (kein Token in localStorage)
3. Öffne Chat-View
4. **Erwartet:**
   - ChatView.vue erkennt: `!authStore.isAuthenticated`
   - `chatStore.startAuthFlow()` wird aufgerufen
   - `authMode = true`
   - Leere Message wird gesendet
5. **Backend:**
   - Request: `POST /api/auth/chat` (kein Auth-Header)
   - Middleware: Route ist in PUBLIC_ROUTES → durchlassen ✅
   - Response: "Mit wem habe ich heute das Vergnügen?" + Vorschläge
6. **Frontend:**
   - VERA-Message wird angezeigt
   - User kann Username eingeben
7. **Weiter:**
   - User gibt Username ein
   - VERA fragt nach Passwort
   - User gibt Passwort ein
   - VERA antwortet mit Token + User-Info
   - authStore speichert Token
   - authMode wird beendet
   - Normaler Chat startet

### Szenario 2: Eingeloggter User (Normaler Chat)
**Erwartung:** Chat funktioniert mit Auth-Token

1. Login mit admin / VERAtest2024!
2. **Console checken:**
   ```
   [Auth] Token gespeichert: eyJhbGciOiJIUzI1NiIsI...
   ```
3. localStorage checken:
   ```javascript
   localStorage.getItem('auth_token') // sollte Token enthalten
   ```
4. Öffne Chat-View
5. **Erwartet:**
   - ChatView.vue erkennt: `authStore.isAuthenticated === true`
   - Normaler Onboarding/Chat-Flow startet (KEIN Auth-Flow)
   - chatStore.sendMessage() wird aufgerufen
6. **DevTools Network Tab:**
   - Request: `POST /api/agent/chat`
   - **WICHTIG: Request Headers prüfen!**
   - Sollte enthalten: `Authorization: Bearer <token>`
7. **Console checken:**
   ```
   [API] Request mit Auth Token: POST /agent/chat
   ```
8. **Backend:**
   - Middleware checkt Token
   - Sollte KEIN 401 werfen
   - Response: VERA's Antwort
9. **Frontend:**
   - VERA's Message wird angezeigt
   - Keine Fehler in Console

## 🔍 Debug-Checkliste

### Wenn Auth-Flow NICHT funktioniert:
1. **Backend Log checken:**
   ```
   🔒 Auth failed for POST /api/auth/chat: Missing authorization header
   ```
   → Falls das kommt: Middleware-Fix hat NICHT gegriffen!
   → Backend neu starten!

2. **Frontend Console checken:**
   - Sollte KEIN Auth-Warning kommen (Auth-Endpoint ist public)
   - Response sollte 200 sein

### Wenn Normaler Chat NICHT funktioniert:
1. **localStorage checken:**
   ```javascript
   localStorage.getItem('auth_token')
   ```
   → Wenn NULL: Login-Flow kaputt!

2. **Frontend Console checken:**
   ```
   [Auth] Initialisiere mit gespeichertem Token: eyJhbGciOiJIUzI1NiIsI...
   [API] Request mit Auth Token: POST /agent/chat
   ```
   → Wenn "[API] Kein Auth Token gefunden...": Interceptor kriegt keinen Token!

3. **DevTools Network Tab → Request Headers:**
   - Sollte enthalten: `Authorization: Bearer <token>`
   - Wenn NICHT: Interceptor funktioniert nicht!

4. **Backend Log checken:**
   ```
   🔒 Auth failed for POST /api/agent/chat: Missing authorization header
   ```
   → Token kommt nicht an!
   → Frontend-Interceptor Problem!

## 🚀 Start Backend mit neuem Fix

```powershell
cd C:\Jarvix\vera-office\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## ✅ Success Criteria

**Auth-Flow (nicht-eingeloggt):**
- [ ] VERA zeigt Greeting-Message
- [ ] User kann Username eingeben
- [ ] VERA fragt nach Passwort
- [ ] User kann Passwort eingeben
- [ ] Token wird gespeichert
- [ ] Normaler Chat startet

**Normaler Chat (eingeloggt):**
- [ ] Token in localStorage vorhanden
- [ ] Console zeigt: "[API] Request mit Auth Token..."
- [ ] DevTools zeigt: "Authorization: Bearer <token>"
- [ ] Backend antwortet mit 200 (KEIN 401!)
- [ ] VERA's Message wird angezeigt
- [ ] Keine Error-Message

## 📝 Nach erfolgreichem Test

1. Bug-Status updaten: `bug_0011_20260308_105454.json` → status: "resolved"
2. BRAIN.md dokumentieren
3. Commit & Push
4. Boris Bescheid geben

## 🔥 Known Issues

**Wenn Token abgelaufen ist:**
- Backend antwortet: 401 - "Invalid or expired token"
- Frontend Interceptor (response) redirected zu `/login`
- User muss sich neu einloggen

**Wenn Backend nicht läuft:**
- Frontend: Network Error
- Chat zeigt: "Entschuldigung, es ist ein Fehler aufgetreten"

**Wenn PUBLIC_ROUTES Fix nicht greift:**
- Backend neu starten (reload manchmal nicht ausreichend!)
