"""
VERA Few-Shot Examples — Konkrete Beispiele für Classifier-Training

Diese Beispiele werden vom Classifier genutzt um bessere Entscheidungen zu treffen.
Format: {ocr_snippet, metadata, category, doc_type, reasoning}
"""

FEW_SHOT_EXAMPLES = [
    # === RECHNUNGEN (verschiedene Absender) ===
    {
        "ocr_snippet": "Henry Schein Dental Depot GmbH\nRechnung RE-2024-4711\nRechnungsdatum: 15.03.2024\nArtikel: Handschuhe Latex S, 100 Stück\nNetto: 45,80 EUR\nMwSt 19%: 8,70 EUR\nBrutto: 54,50 EUR",
        "sender": "Henry Schein",
        "keywords": ["rechnung", "dental", "netto", "brutto"],
        "category": "rechnung",
        "doc_type": "Dental-Materialrechnung",
        "reasoning": "Rechnung von Dental-Lieferant, erkennbar an Absender + Artikel (Handschuhe)"
    },
    {
        "ocr_snippet": "Deutsche Telekom AG\nRechnung Nr. 2024-03-001234\nVertragsnummer: 1234567890\nIhre Telefonrechnung für März 2024\nGrundgebühr: 29,95 EUR\nGespräche: 12,34 EUR\nGesamt brutto: 50,32 EUR",
        "sender": "Deutsche Telekom",
        "keywords": ["rechnung", "telekom", "telefon", "grundgebühr"],
        "category": "rechnung",
        "doc_type": "Telefonrechnung",
        "reasoning": "Rechnung Telekommunikation, erkennbar an Absender + Grundgebühr + Vertragsnummer"
    },
    {
        "ocr_snippet": "Stadtwerke Bamberg\nKundennummer: 123456\nStromrechnung 2024\nVerbrauch: 2.450 kWh\nGrundpreis: 89,40 EUR\nArbeitspreis: 612,50 EUR\nGesamt: 701,90 EUR",
        "sender": "Stadtwerke Bamberg",
        "keywords": ["rechnung", "strom", "kwh", "verbrauch"],
        "category": "rechnung",
        "doc_type": "Energierechnung",
        "reasoning": "Energierechnung, erkennbar an kWh-Verbrauch + Stadtwerke"
    },
    
    # === STEUERN / FINANZAMT ===
    {
        "ocr_snippet": "Finanzamt Bamberg\nSteuernummer: 123/456/78901\nEinkommensteuerbescheid 2023\nFestsetzung der Einkommensteuer\nZu versteuerndes Einkommen: 45.000 EUR\nSteuerschuld: 8.234 EUR\nErstattung: 1.234 EUR",
        "sender": "Finanzamt Bamberg",
        "keywords": ["steuerbescheid", "einkommensteuer", "festsetzung", "finanzamt"],
        "category": "steuern",
        "doc_type": "Steuerbescheid",
        "reasoning": "Steuerbescheid vom Finanzamt, erkennbar an Festsetzung + Steuernummer"
    },
    {
        "ocr_snippet": "Umsatzsteuer-Voranmeldung März 2024\nSteuernummer: 123/456/78901\nUmsatzsteuer 19%: 1.234,56 EUR\nVorsteuer 19%: 987,65 EUR\nZahllast: 246,91 EUR\nFällig: 10.04.2024",
        "sender": "ELSTER",
        "keywords": ["umsatzsteuer", "voranmeldung", "vorsteuer", "zahllast"],
        "category": "steuern",
        "doc_type": "USt-Voranmeldung",
        "reasoning": "Umsatzsteuer-Voranmeldung, erkennbar an Vorsteuer + Zahllast"
    },
    
    # === SOZIALVERSICHERUNG ===
    {
        "ocr_snippet": "AOK Bayern\nSozialversicherungsnachweis\nVersichertennummer: 12345678901\nBeitragssatz: 14,6%\nArbeitgeberanteil: 7,3%\nArbeitnehmeranteil: 7,3%\nBemessungsgrundlage: 3.500 EUR",
        "sender": "AOK Bayern",
        "keywords": ["sozialversicherung", "aok", "beitragssatz", "versichertennummer"],
        "category": "sozialversicherung",
        "doc_type": "SV-Nachweis",
        "reasoning": "Sozialversicherungsnachweis von Krankenkasse (AOK)"
    },
    {
        "ocr_snippet": "Deutsche Rentenversicherung Bund\nVersicherungsnummer: 12 345678 A 123\nRentenbescheid\nRentenbeginn: 01.04.2024\nMonatliche Rente: 1.234,56 EUR",
        "sender": "Deutsche Rentenversicherung",
        "keywords": ["rentenbescheid", "rentenversicherung", "rente"],
        "category": "sozialversicherung",
        "doc_type": "Rentenbescheid",
        "reasoning": "Rentenbescheid von DRV, erkennbar an Versicherungsnummer + Rentenbeginn"
    },
    
    # === LOHN ===
    {
        "ocr_snippet": "Lohnabrechnung März 2024\nName: Müller, Anna\nPersonalnummer: 12345\nBruttolohn: 3.500,00 EUR\nLohnsteuer: 456,78 EUR\nSolidaritätszuschlag: 25,12 EUR\nKirchensteuer: 41,11 EUR\nSozialversicherung gesamt: 700,00 EUR\nNettolohn: 2.276,99 EUR",
        "sender": "Personalabteilung",
        "keywords": ["lohnabrechnung", "bruttolohn", "nettolohn", "lohnsteuer", "sozialversicherung"],
        "category": "lohnabrechnung",
        "doc_type": "Gehaltsabrechnung",
        "reasoning": "Lohnabrechnung, erkennbar an Brutto/Netto + Lohnsteuer + SV"
    },
    
    # === VERSICHERUNG ===
    {
        "ocr_snippet": "Allianz Versicherungs-AG\nVersicherungsschein Nr. 123456789\nBetriebshaftpflichtversicherung\nVersicherungsnehmer: Zahnarztpraxis Dr. Mustermann\nDeckungssumme: 5.000.000 EUR\nJahresbeitrag: 1.234,00 EUR",
        "sender": "Allianz",
        "keywords": ["versicherung", "police", "deckungssumme", "haftpflicht"],
        "category": "versicherung",
        "doc_type": "Versicherungspolice",
        "reasoning": "Versicherungspolice, erkennbar an Deckungssumme + Versicherungsschein"
    },
    {
        "ocr_snippet": "Berufsgenossenschaft für Gesundheitsdienst und Wohlfahrtspflege (BGW)\nBeitragsbescheid 2024\nMitgliedsnummer: 12345678\nBeitrag: 456,78 EUR\nFällig: 15.04.2024",
        "sender": "BGW",
        "keywords": ["berufsgenossenschaft", "bgw", "beitrag"],
        "category": "versicherung",
        "doc_type": "BG-Beitrag",
        "reasoning": "BG-Beitrag, erkennbar an BGW + Beitragsbescheid"
    },
    
    # === VERTRÄGE ===
    {
        "ocr_snippet": "Arbeitsvertrag\nzwischen Zahnarztpraxis Dr. Mustermann (Arbeitgeber)\nund Frau Anna Müller (Arbeitnehmerin)\nBeginn: 01.04.2024\nProbezeit: 6 Monate\nVergütung: 3.500 EUR brutto\nArbeitszeit: 40 Std/Woche\nUrlaub: 30 Tage/Jahr",
        "sender": None,
        "keywords": ["arbeitsvertrag", "arbeitgeber", "arbeitnehmer", "probezeit", "vergütung"],
        "category": "personal",
        "doc_type": "Arbeitsvertrag",
        "reasoning": "Arbeitsvertrag, erkennbar an Arbeitgeber/Arbeitnehmer + Vergütung + Probezeit"
    },
    {
        "ocr_snippet": "Mietvertrag\nVermieter: Mustermann GmbH\nMieter: Dr. Klaus Müller\nMietobjekt: Praxisräume Hauptstraße 1\nMietbeginn: 01.05.2024\nKaltmiete: 1.500 EUR\nNebenkosten: 350 EUR\nKaution: 4.500 EUR",
        "sender": None,
        "keywords": ["mietvertrag", "vermieter", "mieter", "kaltmiete", "nebenkosten", "kaution"],
        "category": "geschaeftlich",
        "doc_type": "Mietvertrag",
        "reasoning": "Mietvertrag, erkennbar an Vermieter/Mieter + Kaltmiete + Kaution"
    },
    
    # === BANK ===
    {
        "ocr_snippet": "Sparkasse Bamberg\nKontoauszug Nr. 123/2024\nKonto: DE12 3456 7890 1234 5678 90\nBuchungstag | Verwendungszweck | Betrag\n15.03.2024 | Überweisung Müller | -123,45 EUR\n16.03.2024 | Gehalt März | +3.500,00 EUR\nSaldo: 5.678,90 EUR",
        "sender": "Sparkasse Bamberg",
        "keywords": ["kontoauszug", "sparkasse", "buchung", "saldo"],
        "category": "bank",
        "doc_type": "Kontoauszug",
        "reasoning": "Kontoauszug, erkennbar an Buchungstag + IBAN + Saldo"
    },
    
    # === ZAHNARZTPRAXIS-SPEZIFISCH ===
    {
        "ocr_snippet": "Heil- und Kostenplan\nPatient: Müller, Anna\nGeburtsdatum: 01.01.1980\nKrankenkasse: AOK Bayern\nBefund: Zahn 16 fehlt, Brücke erforderlich\nTherapie: Brücke 15-17\nRegelversorgung: 456,78 EUR\nFestzuschuss (60%): 274,07 EUR\nEigenanteil: 182,71 EUR",
        "sender": "Zahnarztpraxis Dr. Mustermann",
        "keywords": ["heil- und kostenplan", "hkp", "befund", "therapie", "festzuschuss", "eigenanteil"],
        "category": "behandlung",
        "doc_type": "HKP",
        "reasoning": "Heil- und Kostenplan (HKP), erkennbar an Befund + Therapie + Festzuschuss"
    },
    {
        "ocr_snippet": "KZV Bayern\nQuartalsabrechnung Q1/2024\nPraxis Dr. Mustermann\nVertragszahnärztliche Leistungen\nHonorarsumme: 12.345,67 EUR\nAbzüge: 234,56 EUR\nAuszahlungsbetrag: 12.111,11 EUR",
        "sender": "KZV Bayern",
        "keywords": ["kzv", "quartalsabrechnung", "honorar", "kassenärztliche"],
        "category": "abrechnung",
        "doc_type": "KZV-Abrechnung",
        "reasoning": "KZV-Abrechnung, erkennbar an KZV Bayern + Quartal + Honorar"
    },
    {
        "ocr_snippet": "Röntgenbild\nPatient: Müller, Anna\nGeburtsdatum: 01.01.1980\nAufnahmedatum: 15.03.2024\nTyp: Orthopantomogramm (OPG)\nIndikation: Routinekontrolle, V.a. Karies\nBelichtungsparameter: 70 kV, 8 mA, 14s\nDurchführender Arzt: Dr. Mustermann",
        "sender": None,
        "keywords": ["röntgen", "opg", "indikation", "belichtung"],
        "category": "roentgen",
        "doc_type": "Röntgenbild",
        "reasoning": "Röntgendokumentation, erkennbar an OPG + Indikation + Belichtungsparameter"
    },
    
    # === MAHNUNGEN ===
    {
        "ocr_snippet": "1. Mahnung\nRechnungsnummer: RE-2024-123\nRechnungsdatum: 15.02.2024\nFälligkeit: 15.03.2024\nOffener Betrag: 456,78 EUR\nBitte überweisen Sie innerhalb 7 Tagen\nMahngebühr: 5,00 EUR",
        "sender": "Dental Union",
        "keywords": ["mahnung", "fälligkeit", "offener betrag", "mahngebühr"],
        "category": "mahnung",
        "doc_type": "Zahlungserinnerung",
        "reasoning": "Mahnung, erkennbar an offener Betrag + Fälligkeit + Mahngebühr"
    },
    
    # === GUTACHTEN ===
    {
        "ocr_snippet": "Sachverständigengutachten\nAuftraggeber: Versicherung XY\nGutachter: Dr. med. dent. Mustermann\nGutachtennummer: 2024-001\nBeurteilung: Zahnstatus nach Verkehrsunfall\nFeststellung: Frontzahn 11 frakturiert, Restauration erforderlich\nKosten: 1.234,56 EUR",
        "sender": None,
        "keywords": ["gutachten", "sachverständiger", "beurteilung", "feststellung"],
        "category": "gutachten",
        "doc_type": "Zahngutachten",
        "reasoning": "Gutachten, erkennbar an Sachverständiger + Beurteilung + Feststellung"
    },
    
    # === PROTOKOLLE ===
    {
        "ocr_snippet": "Protokoll der Gesellschafterversammlung\nDatum: 15.03.2024\nOrt: Praxisräume Hauptstraße 1\nAnwesend: Dr. Müller, Dr. Schmidt\nTagesordnung:\n1. Jahresabschluss 2023\n2. Gewinnverteilung\n3. Investitionen 2024\nBeschluss: Jahresabschluss einstimmig genehmigt",
        "sender": None,
        "keywords": ["protokoll", "gesellschafterversammlung", "tagesordnung", "beschluss"],
        "category": "protokoll",
        "doc_type": "Gesellschafterprotokoll",
        "reasoning": "Protokoll Gesellschafterversammlung, erkennbar an Tagesordnung + Beschluss"
    },
    {
        "ocr_snippet": "Betriebsratssitzung vom 15.03.2024\nAnwesend: 5 Betriebsratsmitglieder\nThemen: Arbeitszeitregelung, Urlaubsplanung\nBeschluss: Flexibilisierung Arbeitszeiten ab 01.05.2024",
        "sender": None,
        "keywords": ["betriebsrat", "sitzung", "beschluss", "arbeitszeit"],
        "category": "personal",
        "doc_type": "Betriebsratsprotokoll",
        "reasoning": "Betriebsratsprotokoll, erkennbar an Betriebsrat + Themen + Beschluss"
    },
    
    # === DATENSCHUTZ ===
    {
        "ocr_snippet": "Verarbeitungsverzeichnis gem. Art. 30 DSGVO\nVerantwortlicher: Zahnarztpraxis Dr. Mustermann\nZweck: Patientenverwaltung\nKategorien betroffener Personen: Patienten\nKategorien personenbezogener Daten: Name, Adresse, Gesundheitsdaten\nEmpfänger: Zahntechnische Labore, Krankenkassen\nLöschfrist: 10 Jahre nach letzter Behandlung",
        "sender": None,
        "keywords": ["verarbeitungsverzeichnis", "dsgvo", "personenbezogen", "löschfrist"],
        "category": "datenschutz",
        "doc_type": "Verarbeitungsverzeichnis",
        "reasoning": "DSGVO-Verarbeitungsverzeichnis, erkennbar an Art.30 + Zweck + Kategorien"
    },
    {
        "ocr_snippet": "Auftragsverarbeitungsvertrag gem. Art. 28 DSGVO\nVerantwortlicher: Zahnarztpraxis Dr. Mustermann\nAuftragsverarbeiter: Dampsoft GmbH (Praxissoftware)\nGegenstand: Patientendatenverwaltung\nLaufzeit: unbefristet\nTechnisch-organisatorische Maßnahmen (TOMs): Verschlüsselung, Zugangskontrolle",
        "sender": "Dampsoft",
        "keywords": ["auftragsverarbeitung", "dsgvo", "toms", "verantwortlicher"],
        "category": "datenschutz",
        "doc_type": "AV-Vertrag",
        "reasoning": "Auftragsverarbeitungsvertrag (DSGVO), erkennbar an Art.28 + TOMs"
    },
    
    # === BEHÖRDEN / BESCHEIDE ===
    {
        "ocr_snippet": "Gesundheitsamt Bamberg\nBescheid\nBetriebserlaubnis für Zahnarztpraxis\nInhaber: Dr. Klaus Müller\nStandort: Hauptstraße 1, 96047 Bamberg\nGültig ab: 01.04.2024\nAuflagen: Hygieneplan vorlegen, Begehung 2025",
        "sender": "Gesundheitsamt",
        "keywords": ["bescheid", "betriebserlaubnis", "gesundheitsamt", "auflagen"],
        "category": "behoerde",
        "doc_type": "Betriebserlaubnis",
        "reasoning": "Behördenbescheid (Betriebserlaubnis), erkennbar an Gesundheitsamt + Auflagen"
    },
    {
        "ocr_snippet": "Baugenehmigung\nBauamt Stadt Bamberg\nAktenzeichen: BA-2024-123\nBauvorhaben: Praxiserweiterung Hauptstraße 1\nBauherr: Dr. Mustermann\nGenehmigt unter Auflagen: Stellplätze, Brandschutz\nGültig bis: 31.12.2026",
        "sender": "Bauamt",
        "keywords": ["baugenehmigung", "bauamt", "bauvorhaben", "bauherr"],
        "category": "behoerde",
        "doc_type": "Baugenehmigung",
        "reasoning": "Baugenehmigung, erkennbar an Bauamt + Bauvorhaben + Gültigkeit"
    },
    
    # === KÜNDIGUNG ===
    {
        "ocr_snippet": "Kündigung des Arbeitsverhältnisses\nArbeitgeber: Zahnarztpraxis Dr. Mustermann\nArbeitnehmer: Frau Anna Müller\nPersonalnummer: 12345\nKündigungsfrist: 4 Wochen zum Monatsende\nEnde des Arbeitsverhältnisses: 30.04.2024\nGrund: Betriebsbedingte Kündigung",
        "sender": None,
        "keywords": ["kündigung", "arbeitsverhältnis", "kündigungsfrist", "arbeitgeber"],
        "category": "personal",
        "doc_type": "Kündigung",
        "reasoning": "Kündigungsschreiben, erkennbar an Kündigungsfrist + Ende Arbeitsverhältnis"
    },
    
    # === GASTRONOMIE (neue Beispiele) ===
    {
        "ocr_snippet": "HACCP-Protokoll\nRestaurant Mustermann\nDatum: 15.03.2024\nTemperaturprotokoll Kühlschrank: 4°C (Soll: 2-6°C)\nReinigungsprotokoll: Arbeitsflächen desinfiziert\nWareneingang: Fleisch Metzgerei Schmidt, Charge 2024-03-15\nKontrolliert durch: Koch Müller",
        "sender": None,
        "keywords": ["haccp", "temperatur", "reinigung", "wareneingang"],
        "category": "hygiene",
        "doc_type": "HACCP-Protokoll",
        "reasoning": "HACCP-Protokoll Gastronomie, erkennbar an Temperatur + Reinigung + Wareneingang"
    },
    
    # === HANDWERK (neue Beispiele) ===
    {
        "ocr_snippet": "Abnahmeprotokoll\nProjekt: Badezimmer-Sanierung Müller\nAuftraggeber: Familie Müller\nAuftragnehmer: Sanitär Schmidt GmbH\nDatum: 15.03.2024\nMängel: keine\nAbnahme erfolgt ohne Vorbehalt\nGewährleistungsfrist: 5 Jahre",
        "sender": "Sanitär Schmidt",
        "keywords": ["abnahme", "protokoll", "gewährleistung", "mängel"],
        "category": "projekt",
        "doc_type": "Abnahmeprotokoll",
        "reasoning": "Abnahmeprotokoll Handwerk, erkennbar an Mängel + Gewährleistung"
    },
    
    # === IT-BRANCHE (neue Beispiele) ===
    {
        "ocr_snippet": "Technisch-organisatorische Maßnahmen (TOMs)\nUnternehmen: IT-Beratung Mustermann GmbH\nDatenschutz-Management-System\nZugangskontrolle: 2FA, Passwort-Policy\nVerschlüsselung: AES-256 für Daten at rest\nBackup: täglich, 30 Tage Aufbewahrung\nZutrittsschutz: Alarmanlagen, Videoüberwachung",
        "sender": None,
        "keywords": ["toms", "zugangskontrolle", "verschlüsselung", "datenschutz"],
        "category": "datenschutz",
        "doc_type": "TOMs",
        "reasoning": "Technisch-organisatorische Maßnahmen (DSGVO), erkennbar an Zugangskontrolle + Verschlüsselung"
    },
]


def get_examples_for_category(category: str, limit: int = 5) -> list:
    """
    Gibt Few-Shot-Beispiele für eine bestimmte Kategorie zurück.
    
    Args:
        category: Kategorie (z.B. "rechnung", "steuern", "personal")
        limit: Max. Anzahl Beispiele
    
    Returns:
        Liste von Beispiel-Dicts
    """
    examples = [ex for ex in FEW_SHOT_EXAMPLES if ex["category"] == category]
    return examples[:limit]


def get_examples_by_keywords(keywords: list, limit: int = 3) -> list:
    """
    Gibt Beispiele zurück die am besten zu den Keywords passen.
    
    Args:
        keywords: Liste von Keywords aus dem OCR-Text
        limit: Max. Anzahl Beispiele
    
    Returns:
        Liste von Beispiel-Dicts, sortiert nach Relevanz
    """
    scored = []
    for ex in FEW_SHOT_EXAMPLES:
        score = sum(1 for kw in ex["keywords"] if kw in [k.lower() for k in keywords])
        if score > 0:
            scored.append((score, ex))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ex for score, ex in scored[:limit]]


# ============================================================
# Konversations-Beispiele für Chat-Training
# ============================================================

CONVERSATION_EXAMPLES = [
    # === BEGRÜSSUNG & SMALLTALK ===
    {"user": "Morgen VERA", "vera": "Morgen! ☀️ 3 neue Dokumente seit gestern. Soll ich die durchgehen?"},
    {"user": "Hey", "vera": "Hey! Was kann ich für dich tun?"},
    {"user": "Hallo VERA", "vera": "Hallo! Schön, dass du da bist. Was steht an?"},
    {"user": "Guten Tag", "vera": "Tag! Alles klar bei dir? Ich hab hier 2 unkategorisierte Dokumente liegen."},
    {"user": "Servus", "vera": "Servus! Was brauchst du?"},
    {"user": "Wie geht's?", "vera": "Läuft! Hab heute schon 5 Dokumente einsortiert. Was kann ich für dich tun?"},
    {"user": "Schönen Feierabend", "vera": "Dir auch! 👋 Alles erledigt für heute — 0 offene Dokumente."},
    {"user": "Tschüss", "vera": "Tschüss! Bis morgen 👋"},

    # === DOKUMENT-SUCHE ===
    {"user": "Wo ist die Rechnung von Müller?", "vera": "Schau mal: Ich hab 2 Rechnungen mit 'Müller' gefunden. 📄 Meinst du die vom 12.02. oder die vom 03.01.?"},
    {"user": "Zeig mir alle HKPs von heute", "vera": "Hab 3 HKPs von heute gefunden. Soll ich die nach Patient sortieren?"},
    {"user": "Ich brauch den Kostenvoranschlag für Frau Schmidt", "vera": "Hab einen KV für Schmidt, Petra vom 15.01. gefunden. 📄 Ist es der?"},
    {"user": "Gibt's was von Henry Schein?", "vera": "Ja, 2 Rechnungen von Henry Schein diesen Monat. Die letzte vom 20.02. über 234,50 €."},
    {"user": "Such mal nach Röntgenbilder Meier", "vera": "Gefunden: 1 OPG von Meier, Thomas vom 05.03. Soll ich das öffnen?"},
    {"user": "Wo sind die Laborabrechnungen?", "vera": "Unter Labor/Abrechnungen — 12 Einträge dieses Quartal. Filter eingrenzen?"},

    # === DOKUMENT-ABLAGE ===
    {"user": "Leg das unter Rechnungen ab", "vera": "Erledigt. ✅ Liegt jetzt unter Rechnungen/2026/03. Aufbewahrungsfrist: 10 Jahre."},
    {"user": "Das ist eine Mahnung von Henry Schein", "vera": "Hab ich als Mahnung abgelegt. ⚠️ Fällig seit 14 Tagen — willst du die auf die Wiedervorlage?"},
    {"user": "Falscher Ordner, das gehört zu Labor", "vera": "Klar, verschoben nach Labor. Ich merk mir das für nächstes Mal. 🧠"},
    {"user": "Das ist eine Rechnung von Dental Union", "vera": "Erledigt. ✅ Abgelegt als Dental-Materialrechnung unter Rechnungen. Netto: 189,50 €."},
    {"user": "Sortier das mal ein", "vera": "Hmm, sieht aus wie ein Laborbericht. Stimmt das? Dann leg ich's unter Labor ab."},
    {"user": "Verschieb das zu Personal", "vera": "Erledigt. ✅ Liegt jetzt unter Personal."},

    # === HILFE & ERKLÄRUNG ===
    {"user": "Wie lang muss ich das aufbewahren?", "vera": "Kommt drauf an — Rechnungen 10 Jahre, Personalakten 3 Jahre nach Austritt, Patientenakten mindestens 10 Jahre. Um welches Dokument geht's?"},
    {"user": "Was ist GoBD?", "vera": "GoBD = Grundsätze ordnungsmäßiger Buchführung. Heißt: Belege müssen unveränderbar, vollständig und nachvollziehbar sein. Betrifft dich v.a. bei Rechnungen und Kassenbuch."},
    {"user": "Welche Dokumente fehlen noch?", "vera": "Hmm, mir fehlt die Lohnabrechnung Februar und der KZV-Nachweis Q4/2025. Soll ich eine Erinnerung setzen?"},
    {"user": "Was muss ich bei Röntgenbildern beachten?", "vera": "Röntgenbilder 10 Jahre aufbewahren (RöV). Bei Kindern: ab dem 18. Geburtstag nochmal 10 Jahre. Immer die Indikation dokumentieren!"},
    {"user": "Wie funktioniert die Suche?", "vera": "Einfach tippen was du suchst — Name, Datum, Dokumenttyp. Ich durchsuche OCR-Text und Metadaten. Beispiel: 'Rechnung Müller März'"},
    {"user": "Hilfe", "vera": "Klar! Ich kann: 🔍 Dokumente suchen, 🗂️ Ablegen & sortieren, 📊 Statistiken zeigen, ⚠️ An Fristen erinnern. Was brauchst du?"},

    # === FEHLER & KORREKTUREN ===
    {"user": "Das war falsch einsortiert", "vera": "Sorry! Wo soll es stattdessen hin? Ich lern draus. 🧠"},
    {"user": "Nein, das ist keine Rechnung", "vera": "Alles klar, hab ich korrigiert. Was ist es denn? Dann merk ich mir das fürs nächste Mal."},
    {"user": "Kannst du das umbenennen?", "vera": "Klar. Wie soll es heißen?"},
    {"user": "Stimmt nicht, das ist von Dental Union, nicht Henry Schein", "vera": "Korrigiert! ✅ Absender jetzt Dental Union. Danke für den Hinweis."},

    # === PROAKTIVE HINWEISE (VERA initiiert) ===
    {"user": "[proaktiv]", "vera": "Hey, die Röntgenbilder von Müller, Anna sind bald 10 Jahre alt. Aufbewahrungsfrist endet 2026. Willst du die archivieren? 📄"},
    {"user": "[proaktiv]", "vera": "⚠️ Seit 3 Wochen keine Lohnabrechnung eingegangen. Fehlt die für Februar?"},
    {"user": "[proaktiv]", "vera": "3 unkategorisierte Dokumente warten auf dich. Soll ich die mal durchgehen?"},
    {"user": "[proaktiv]", "vera": "Die Mahnung von Henry Schein ist seit 14 Tagen überfällig. Willst du die auf Wiedervorlage?"},

    # === DANKE / BITTE ===
    {"user": "Danke VERA", "vera": "Kein Ding! 👍"},
    {"user": "Super, danke!", "vera": "Immer gern. Noch was?"},
    {"user": "Bitte", "vera": "Erledigt. Was steht als nächstes an?"},

    # === STATUS & STATISTIK ===
    {"user": "Was gibt's Neues?", "vera": "Heute: 5 neue Dokumente, 2 davon noch unkategorisiert. Keine offenen Mahnungen. Alles im grünen Bereich! ✅"},
    {"user": "Wie viele Dokumente hab ich?", "vera": "Insgesamt 342 Dokumente, davon 338 kategorisiert. 4 warten noch auf dich."},
]


def get_conversation_examples(category: str = None, limit: int = 5) -> list:
    """
    Gibt Konversations-Beispiele zurück, optional nach Kategorie gefiltert.
    Kategorien: greeting, search, filing, help, correction, proactive, thanks, status
    """
    if not category:
        return CONVERSATION_EXAMPLES[:limit]
    
    category_keywords = {
        "greeting": ["morgen", "hey", "hallo", "tag", "servus", "tschüss", "feierabend", "geht's"],
        "search": ["wo ist", "zeig", "such", "brauch", "gibt's", "find"],
        "filing": ["leg", "sortier", "verschieb", "ablage", "ordner", "einsortiern"],
        "help": ["wie lang", "was ist", "welche", "hilfe", "wie funktioniert", "beachten"],
        "correction": ["falsch", "nein", "stimmt nicht", "umbenennen", "korrigier"],
        "proactive": ["proaktiv"],
        "thanks": ["danke", "super", "bitte"],
        "status": ["neues", "wie viele", "statistik"],
    }
    
    keywords = category_keywords.get(category, [])
    filtered = [ex for ex in CONVERSATION_EXAMPLES 
                if any(kw in ex["user"].lower() for kw in keywords)]
    return filtered[:limit]


def format_conversation_for_prompt(examples: list) -> str:
    """Formatiert Konversations-Beispiele für den System-Prompt."""
    lines = []
    for ex in examples:
        if ex["user"] == "[proaktiv]":
            continue
        lines.append(f"User: {ex['user']}\nVERA: {ex['vera']}")
    return "\n\n".join(lines)


def format_example_for_prompt(example: dict) -> str:
    """
    Formatiert ein Beispiel für die LLM-Prompt.
    
    Returns:
        String im Format "OCR: ... → Kategorie: ... (Begründung: ...)"
    """
    return (
        f"OCR: {example['ocr_snippet'][:200]}...\n"
        f"→ Kategorie: {example['category']}, Typ: {example['doc_type']}\n"
        f"Begründung: {example['reasoning']}"
    )
