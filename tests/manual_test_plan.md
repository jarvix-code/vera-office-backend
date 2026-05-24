# VERA Office – Manueller Testplan
**Version:** 1.0
**Datum:** 2026-04-08
**Ziel:** Vollständiger Abnahmetest vor dem Software-Freigabe

---

## Testumgebung

| Parameter | Wert |
|-----------|------|
| URL (HTTP) | http://192.168.178.44:8081 |
| URL (HTTPS) | https://192.168.178.44:8443 |
| Backend-Version | 1.0.0-alpha |
| Promo-Codes | VERA-DEMO-2026, SENZIVO-PRO, BASIC-FREE |

---

## Promo-Codes (API-Verifiziert ✅)

| Code | Module | Max. Uses | Beschreibung |
|------|--------|-----------|--------------|
| `VERA-DEMO-2026` | qm, erp, datev | 100 | Demo-Code für alle Module |
| `SENZIVO-PRO` | qm, erp, datev | 5 | Testkunde SENZIVO |
| `BASIC-FREE` | dms | 1000 | Basis DMS kostenlos |

Promo-Endpoint: `POST /api/promo/redeem` → öffentlich, kein Login erforderlich.

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ☐ | Nicht getestet |
| ✅ | Bestanden |
| ❌ | Fehlgeschlagen |
| ⚠️ | Teilweise / Anmerkung |

---

## T01–T09: Onboarding-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T01 | Frische Installation → App öffnen | Sprachauswahl-Screen erscheint | ☐ | |
| T02 | Deutsch wählen | VERA begrüßt auf Deutsch | ☐ | |
| T03 | English wählen | VERA begrüßt auf Englisch | ☐ | |
| T04 | Onboarding: Cert-Schritt | Cert-Installation wird angeboten | ☐ | |
| T05 | Namen eingeben | Name wird gespeichert, erscheint im Dashboard | ☐ | |
| T06 | Master-PW festlegen (8-stellig) | Validierung: <8 Zeichen wird abgelehnt | ☐ | |
| T07 | PIN festlegen (6-stellig) | Validierung: <4 Zeichen wird abgelehnt | ☐ | |
| T08 | Onboarding abschließen | Dashboard erscheint korrekt | ☐ | |
| T09 | Sidebar vor Onboarding | Sidebar ist NICHT sichtbar vor Abschluss | ☐ | |

---

## T10–T14: Dashboard-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T10 | Dashboard öffnen | Alle 6 Modul-Kacheln sichtbar (DMS, QM, ERP, DATEV, Suche, Chat) | ☐ | |
| T11 | Chat-Eingabefeld | Eingabefeld ist aktiv und bedienbar | ☐ | |
| T12 | VERA Logo im Header | Logo erscheint korrekt (kein Platzhalter) | ☐ | |
| T13 | Farben | Türkis/Blau – KEIN Violett sichtbar | ☐ | |
| T14 | Kein "Praxis"-Text | Keine alten "Praxis"-Begriffe mehr vorhanden | ☐ | |

---

## T15–T18: Chat-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T15 | Eingabe: "Hallo" | VERA antwortet freundlich und auf Deutsch | ☐ | |
| T16 | Eingabe: "Kannst du meine Dokumente verwalten?" | VERA erklärt ihre DMS-Fähigkeiten | ☐ | |
| T17 | Eingabe: "Was kannst du?" | VERA listet verfügbare Module auf | ☐ | |
| T18 | Chat bei Verbindungsfehler | Fehlermeldung wird angezeigt (kein leerer Screen) | ☐ | |

---

## T19–T26: Navigation-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T19 | Dokumente-Seite öffnen | Dokumentenliste lädt korrekt | ☐ | |
| T20 | Erfassung/Scan-Seite öffnen | Scan-Interface erscheint | ☐ | |
| T21 | Suche-Seite öffnen | Suchfeld aktiv und bedienbar | ☐ | |
| T22 | Aufgaben-Seite öffnen | Aufgabenliste erscheint | ☐ | |
| T23 | Export-Seite öffnen | Export-Optionen sichtbar | ☐ | |
| T24 | ERP-Bereich öffnen | PIN-Abfrage erscheint (gesicherter Bereich) | ☐ | |
| T25 | QM-Bereich öffnen | PIN-Abfrage erscheint (gesicherter Bereich) | ☐ | |
| T26 | Einstellungen öffnen | Einstellungen-Seite lädt | ☐ | |

---

## T27–T30: Auth-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T27 | QM ohne PIN aufrufen | PIN-Eingabe-Dialog erscheint | ☐ | |
| T28 | Falsche PIN eingeben | Fehlermeldung "Falsche PIN" erscheint | ☐ | |
| T29 | Richtige PIN eingeben | Zugang zu QM gewährt | ☐ | |
| T30 | Promo-Code `VERA-DEMO-2026` eingeben | Meldung: Module QM, ERP, DATEV freigeschaltet | ☐ | |

### API-Test für T30 (curl)
```bash
curl -X POST http://192.168.178.44:8081/api/promo/redeem \
  -H "Content-Type: application/json" \
  -d '{"code": "VERA-DEMO-2026"}'
# Erwartete Antwort: {"success":true,"modules":["qm","erp","datev"]}
```

---

## T31–T35: Funktions-Tests

| Nr | Test | Erwartetes Ergebnis | Status | Notiz |
|----|------|---------------------|--------|-------|
| T31 | Dokument hochladen (Foto oder PDF) | Upload erfolgreich, Dokument erscheint in Liste | ☐ | |
| T32 | OCR funktioniert | Hochgeladenes Dokument hat erkannten Text | ☐ | |
| T33 | Suche nach hochgeladenem Dokument | Dokument erscheint in Suchergebnissen | ☐ | |
| T34 | Dark Mode Toggle | Dunkles Theme wird korrekt angewendet | ☐ | |
| T35 | Feedback-Button | Feedback-Dialog öffnet, Absenden funktioniert | ☐ | |

---

## Bekannte Backend-Issues (Stand 2026-04-08)

| Endpoint | Status | Auswirkung |
|----------|--------|------------|
| `GET /api/active-learning/unclear-documents/count` | 500 (DB-Schema alt) | Badge-Zähler leer – kein Test-Blocker |
| `GET /api/agent/suggestions` | 500 | Proaktive Vorschläge fehlen – kein Test-Blocker |
| `GET /vera-logo.svg` | 404 → Fix deployed | Logo im Header |
| `GET /manifest.json` | 404 → Fix deployed | PWA-Funktion |
| `GET /api/promo/redeem` | ✅ Funktioniert | Promo-Code Test (T30) möglich |

---

## Checkliste vor Testbeginn

- [ ] Backend läuft: `curl http://192.168.178.44:8081/api/health`
- [ ] Frontend erreichbar: http://192.168.178.44:8081
- [ ] Promo-Codes verfügbar: `curl http://192.168.178.44:8081/api/promo/status`
- [ ] Browser-DevTools öffnen → Console-Tab auf Errors prüfen
- [ ] Onboarding zurücksetzen falls nötig (für T01–T09)
