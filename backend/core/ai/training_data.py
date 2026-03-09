"""
VERA Training Data — Umfassendes Domänenwissen für deutsche KMUs
Wird beim ersten Start in brain.db geladen.

Quellen: GoBD, HGB, AO, BGB, DSGVO, branchenspezifische Vorschriften
"""


# ============================================================
# Aufbewahrungsfristen (GoBD-konform, vollständig)
# ============================================================
RETENTION_PERIODS = {
    # 10 Jahre (§147 AO, §257 HGB)
    "rechnung": {"years": 10, "basis": "§147 Abs.1 Nr.4 AO, §257 Abs.1 Nr.4 HGB", "note": "Eingangs- und Ausgangsrechnungen"},
    "rechnung_eingang": {"years": 10, "basis": "§147 AO", "note": "Eingangsrechnungen von Lieferanten"},
    "rechnung_ausgang": {"years": 10, "basis": "§147 AO", "note": "Ausgangsrechnungen an Kunden"},
    "jahresabschluss": {"years": 10, "basis": "§257 Abs.1 Nr.1 HGB", "note": "Bilanz, GuV, Anhang"},
    "buchungsbeleg": {"years": 10, "basis": "§147 Abs.1 Nr.4 AO", "note": "Alle Belege die Buchungen begründen"},
    "kontoauszug": {"years": 10, "basis": "§147 Abs.1 Nr.4 AO", "note": "Bank-/Girokontoauszüge"},
    "kassenbuch": {"years": 10, "basis": "§147 Abs.1 Nr.1 AO", "note": "Tägliche Kassenaufzeichnungen"},
    "steuerbescheid": {"years": 10, "basis": "§147 AO", "note": "Bis Bestandskraft + Verjährung"},
    "steuererklaerung": {"years": 10, "basis": "§147 AO", "note": "Einkommensteuer, Umsatzsteuer, Gewerbesteuer"},
    "umsatzsteuer_voranmeldung": {"years": 10, "basis": "§147 AO"},
    "inventur": {"years": 10, "basis": "§257 Abs.1 Nr.1 HGB"},
    "lagebericht": {"years": 10, "basis": "§257 Abs.1 Nr.1 HGB"},
    "grundbuch_auszug": {"years": 10, "basis": "§147 AO"},
    "darlehensvertrag": {"years": 10, "basis": "§147 AO", "note": "Ab Ende des Vertrags"},
    "mietvertrag": {"years": 10, "basis": "§147 AO", "note": "Ab Ende des Mietverhältnisses"},
    "leasingvertrag": {"years": 10, "basis": "§147 AO"},
    "versicherungspolice": {"years": 10, "basis": "§147 AO", "note": "Ab Vertragsende"},
    "gesellschaftsvertrag": {"years": 10, "basis": "§257 HGB", "note": "Dauerhaft empfohlen"},
    "handelsregister_auszug": {"years": 10, "basis": "§257 HGB"},
    "zollunterlagen": {"years": 10, "basis": "§147 AO"},
    
    # 6 Jahre (§257 Abs.1 Nr.2,3 HGB)
    "geschaeftsbrief": {"years": 6, "basis": "§257 Abs.1 Nr.2,3 HGB", "note": "Ein- und ausgehend"},
    "angebot": {"years": 6, "basis": "§257 HGB"},
    "auftragsbestaetigung": {"years": 6, "basis": "§257 HGB"},
    "lieferschein": {"years": 6, "basis": "§257 HGB"},
    "mahnung": {"years": 6, "basis": "§257 HGB"},
    "lohnabrechnung": {"years": 6, "basis": "§257 HGB, §41 EStG", "note": "Lohnsteuer-Unterlagen"},
    "lohnsteuerbescheinigung": {"years": 6, "basis": "§41 EStG"},
    "sozialversicherung_nachweis": {"years": 6, "basis": "§28f SGB IV"},
    "reisekostenabrechnung": {"years": 6, "basis": "§257 HGB"},
    "bewirtungsbeleg": {"years": 6, "basis": "§257 HGB, §4 Abs.5 EStG"},
    "protokoll": {"years": 6, "basis": "§257 HGB", "note": "Gesellschafter-/Vorstandsprotokolle"},
    "korrespondenz_geschaeftlich": {"years": 6, "basis": "§257 HGB"},
    
    # 3 Jahre (Verjährung §195 BGB)
    "personalakte": {"years": 3, "basis": "§195 BGB", "note": "Ab Austritt des Mitarbeiters"},
    "arbeitsvertrag": {"years": 3, "basis": "§195 BGB", "note": "Ab Vertragsende"},
    "kuendigung": {"years": 3, "basis": "§195 BGB"},
    "abmahnung": {"years": 3, "basis": "§195 BGB"},
    "arbeitszeugnis": {"years": 3, "basis": "§195 BGB"},
    "bewerbung_absage": {"years": 0.5, "basis": "AGG, §15 Abs.4", "note": "6 Monate, danach löschen (DSGVO)"},
    
    # Branchenspezifisch: Zahnarztpraxis / Arztpraxis
    "patientenakte": {"years": 10, "basis": "§630f BGB", "note": "Ab letzter Behandlung, 30 Jahre empfohlen"},
    "behandlungsvertrag": {"years": 10, "basis": "§630f BGB"},
    "roentgenbild": {"years": 10, "basis": "§28 Abs.3 RöV", "note": "Röntgenverordnung"},
    "roentgenbild_kind": {"years": 10, "basis": "§28 RöV", "note": "Ab dem 18. Lebensjahr des Kindes"},
    "arztbericht": {"years": 30, "basis": "Berufsordnung Ärzte §10", "note": "Empfehlung, mindestens 10 Jahre"},
    "laborbericht": {"years": 10, "basis": "§630f BGB"},
    "heil_kostenplan": {"years": 10, "basis": "§630f BGB, GOZ"},
    "einwilligung_patient": {"years": 10, "basis": "§630f BGB, DSGVO Art.7", "note": "Einwilligung Behandlung + Datenschutz"},
    "aufklaerungsbogen": {"years": 30, "basis": "§630e BGB", "note": "Beweislast bei Aufklärungspflicht"},
    "abrechnungsdaten_kzv": {"years": 10, "basis": "§147 AO, BEMA/GOZ"},
    "materialpass_zahntechnik": {"years": 10, "basis": "MPG §11", "note": "Medizinproduktegesetz"},
    "hygienedokumentation": {"years": 5, "basis": "RKI-Richtlinie, MPBetreibV"},
    "medizinprodukte_aufbereitung": {"years": 5, "basis": "§8 MPBetreibV"},
    "strahlenschutz_nachweis": {"years": 30, "basis": "StrlSchV", "note": "Strahlenschutzverordnung"},
    "betaeubungsmittel_buch": {"years": 3, "basis": "§13 BtMVV", "note": "Ab letzter Eintragung"},
    "qm_dokument": {"years": 10, "basis": "§135a SGB V, G-BA QM-RL"},
    "praxisbegehung_protokoll": {"years": 10, "basis": "Empfehlung"},
    
    # Dauerhaft
    "gesellschafterbeschluss": {"years": 99, "basis": "Empfehlung", "note": "Dauerhaft aufbewahren"},
    "patent": {"years": 99, "basis": "Dauerhaft"},
    "grundstueckskaufvertrag": {"years": 99, "basis": "Dauerhaft"},
    "notarvertrag": {"years": 99, "basis": "Dauerhaft"},
    
    # === BAUBRANCHE ===
    "bautagebuch": {"years": 5, "basis": "§13 HOAI, VOB/B §4", "note": "Nach Abnahme, Gewährleistung beachten"},
    "bauvertrag": {"years": 6, "basis": "§195 BGB, VOB/B", "note": "Ab Fertigstellung/Abnahme"},
    "abnahmeprotokoll": {"years": 5, "basis": "VOB/B §12", "note": "Gewährleistungsfrist (5 Jahre)"},
    "bauabnahme": {"years": 5, "basis": "VOB/B §13"},
    "gewaehrleistung_bau": {"years": 5, "basis": "§634a BGB", "note": "5 Jahre bei Bauwerken"},
    "aufmass": {"years": 6, "basis": "§257 HGB, VOB/C"},
    "bauplan": {"years": 5, "basis": "Empfehlung", "note": "Nach Projektabschluss"},
    "baugenehmigung": {"years": 99, "basis": "Dauerhaft", "note": "Solange Bauwerk besteht"},
    "statik_berechnung": {"years": 99, "basis": "Baurecht, Dauerhaft"},
    "pruefbericht_bau": {"years": 6, "basis": "LBO"},
    
    # === GASTRONOMIE ===
    "haccp_protokoll": {"years": 2, "basis": "LMHV §5, HACCP", "note": "Mindestens 2 Jahre"},
    "temperaturprotokoll": {"years": 2, "basis": "LMHV §5"},
    "reinigungsprotokoll_gastro": {"years": 2, "basis": "LMHV"},
    "wareneingang_protokoll": {"years": 2, "basis": "LMHV"},
    "lebensmittel_kontrolle": {"years": 5, "basis": "LFGB", "note": "Amtliche Kontrollen"},
    "schulungsnachweis_hygiene": {"years": 3, "basis": "§43 IfSG", "note": "Infektionsschutzgesetz"},
    "allergen_liste": {"years": 2, "basis": "LMIV Art.21"},
    "speisekarte": {"years": 1, "basis": "LMIV", "note": "Aktuelle + 1 Jahr alte"},
    "rueckstellprobe": {"years": 0.25, "basis": "DIN 10508", "note": "96 Stunden (4 Tage)"},
    
    # === HANDWERK ALLGEMEIN ===
    "aufmass_handwerk": {"years": 6, "basis": "§257 HGB"},
    "abnahme_handwerk": {"years": 5, "basis": "§634a BGB"},
    "gewaehrleistung_handwerk": {"years": 2, "basis": "§438 BGB", "note": "2 Jahre bei beweglichen Sachen"},
    "montagebericht": {"years": 5, "basis": "§195 BGB"},
    "wartungsprotokoll": {"years": 10, "basis": "§147 AO, Produkthaftung"},
    "pruefprotokoll_handwerk": {"years": 10, "basis": "Produkthaftung"},
    "meisterbrief": {"years": 99, "basis": "Dauerhaft"},
    "gesellenpruefung": {"years": 99, "basis": "Dauerhaft"},
    "fortbildungsnachweis": {"years": 99, "basis": "Empfehlung"},
    
    # === IT-BRANCHE ===
    "datenschutz_doku": {"years": 3, "basis": "DSGVO Art.5 Abs.2", "note": "Rechenschaftspflicht, nach Löschung"},
    "loeschkonzept": {"years": 3, "basis": "DSGVO Art.17"},
    "verarbeitungsverzeichnis": {"years": 3, "basis": "DSGVO Art.30", "note": "Aktiv halten, 3 Jahre nach Löschung"},
    "toms_dokumentation": {"years": 3, "basis": "DSGVO Art.32", "note": "Technische/Organisatorische Maßnahmen"},
    "auftragsverarbeitung_vertrag": {"years": 10, "basis": "DSGVO Art.28, §147 AO"},
    "datenschutz_folgenabschaetzung": {"years": 3, "basis": "DSGVO Art.35"},
    "datenpanne_dokumentation": {"years": 3, "basis": "DSGVO Art.33", "note": "72h Meldefrist"},
    "einwilligung_dsgvo": {"years": 3, "basis": "DSGVO Art.7", "note": "Nach Widerruf"},
    "softwarelizenz": {"years": 10, "basis": "§147 AO, Vertrag"},
    "quellcode_archiv": {"years": 10, "basis": "Empfehlung, Urheberrecht"},
    "it_sicherheitsaudit": {"years": 3, "basis": "ISO 27001"},
    
    # === IMMOBILIEN ===
    "nebenkostenabrechnung": {"years": 6, "basis": "§556 Abs.3 BGB", "note": "12 Monate Widerspruchsfrist"},
    "mietvertrag_wohnung": {"years": 10, "basis": "§147 AO", "note": "Ab Vertragsende"},
    "mietkaution_nachweis": {"years": 10, "basis": "§195 BGB"},
    "wohnungsuebergabe_protokoll": {"years": 10, "basis": "§195 BGB"},
    "betriebskostenabrechnung": {"years": 6, "basis": "§556 BGB"},
    "hausgeldabrechnung": {"years": 10, "basis": "WEG §28"},
    "mieterhohung_vereinbarung": {"years": 10, "basis": "§558 BGB"},
    "kuendigung_mietvertrag": {"years": 10, "basis": "§195 BGB", "note": "Ab Vertragsende"},
    "wohnungseigentum_teilungserklaerung": {"years": 99, "basis": "WEG, Dauerhaft"},
    "gemeinschaftsordnung": {"years": 99, "basis": "WEG, Dauerhaft"},
    "instandhaltungsruecklage": {"years": 10, "basis": "WEG §28"},
}


# ============================================================
# Absender → Kategorie Mapping (deutsche KMU-Landschaft)
# ============================================================
SENDER_MAPPINGS = {
    # Krankenkassen / Sozialversicherung
    "aok": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "aok bayern": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "aok plus": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "tk": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "techniker krankenkasse": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "barmer": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "dak": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "dak gesundheit": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "ikk": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "knappschaft": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "bkk": {"category": "sozialversicherung", "doc_type": "SV-Nachweis"},
    "deutsche rentenversicherung": {"category": "sozialversicherung", "doc_type": "Rentenbescheid"},
    "drv bund": {"category": "sozialversicherung", "doc_type": "Rentenbescheid"},
    "bundesagentur für arbeit": {"category": "sozialversicherung", "doc_type": "Bescheid"},
    
    # Zahnärztliche Vereinigungen (für Senzivo)
    "kzv": {"category": "abrechnung", "doc_type": "KZV-Abrechnung"},
    "kzv bayern": {"category": "abrechnung", "doc_type": "KZV-Abrechnung"},
    "kassenzahnärztliche vereinigung": {"category": "abrechnung", "doc_type": "KZV-Abrechnung"},
    "bzäk": {"category": "berufliches", "doc_type": "Kammer-Mitteilung"},
    "zahnärztekammer": {"category": "berufliches", "doc_type": "Kammer-Mitteilung"},
    "zäk bayern": {"category": "berufliches", "doc_type": "Kammer-Mitteilung"},
    
    # Finanzen / Steuern
    "finanzamt": {"category": "steuern", "doc_type": "Steuerbescheid"},
    "finanzamt bamberg": {"category": "steuern", "doc_type": "Steuerbescheid"},
    "elster": {"category": "steuern", "doc_type": "Steuerunterlagen"},
    "datev": {"category": "buchhaltung", "doc_type": "Buchhaltungsbeleg"},
    
    # Kammern / Verbände
    "ihk": {"category": "geschaeftlich", "doc_type": "Kammer-Mitteilung"},
    "ihk oberfranken": {"category": "geschaeftlich", "doc_type": "Kammer-Mitteilung"},
    "hwk": {"category": "geschaeftlich", "doc_type": "Kammer-Mitteilung"},
    "berufsgenossenschaft": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bgw": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    
    # Versicherungen
    "allianz": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "ergo": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "huk coburg": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "huk-coburg": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "axa": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "generali": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "zurich": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "signal iduna": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "debeka": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "provinzial": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "lvm": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "vhv": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "r+v": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "gothaer": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "continentale": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "stuttgarter": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "nürnberger": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    
    # Telekommunikation
    "telekom": {"category": "rechnung", "doc_type": "Telefonrechnung"},
    "deutsche telekom": {"category": "rechnung", "doc_type": "Telefonrechnung"},
    "vodafone": {"category": "rechnung", "doc_type": "Telefonrechnung"},
    "o2": {"category": "rechnung", "doc_type": "Telefonrechnung"},
    "1&1": {"category": "rechnung", "doc_type": "Internetrechnung"},
    "unitymedia": {"category": "rechnung", "doc_type": "Internetrechnung"},
    
    # Energieversorger
    "stadtwerke": {"category": "rechnung", "doc_type": "Energierechnung"},
    "stadtwerke bamberg": {"category": "rechnung", "doc_type": "Energierechnung"},
    "eon": {"category": "rechnung", "doc_type": "Energierechnung"},
    "e.on": {"category": "rechnung", "doc_type": "Energierechnung"},
    "rwe": {"category": "rechnung", "doc_type": "Energierechnung"},
    "vattenfall": {"category": "rechnung", "doc_type": "Energierechnung"},
    "enbw": {"category": "rechnung", "doc_type": "Energierechnung"},
    
    # Banken
    "sparkasse": {"category": "bank", "doc_type": "Kontoauszug"},
    "sparkasse bamberg": {"category": "bank", "doc_type": "Kontoauszug"},
    "volksbank": {"category": "bank", "doc_type": "Kontoauszug"},
    "vr bank": {"category": "bank", "doc_type": "Kontoauszug"},
    "commerzbank": {"category": "bank", "doc_type": "Kontoauszug"},
    "deutsche bank": {"category": "bank", "doc_type": "Kontoauszug"},
    "postbank": {"category": "bank", "doc_type": "Kontoauszug"},
    "ing": {"category": "bank", "doc_type": "Kontoauszug"},
    "ing-diba": {"category": "bank", "doc_type": "Kontoauszug"},
    "hypo vereinsbank": {"category": "bank", "doc_type": "Kontoauszug"},
    "unicredit": {"category": "bank", "doc_type": "Kontoauszug"},
    
    # Online-Händler / Lieferanten
    "amazon": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    "amazon business": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    "ebay": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    "otto": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    "reichelt": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    "conrad": {"category": "rechnung", "doc_type": "Lieferantenrechnung"},
    
    # Dental-Lieferanten (Senzivo-spezifisch)
    "henry schein": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "dental union": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "amann girrbach": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "dentsply sirona": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "ivoclar": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "komet dental": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "kuraray noritake": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "voco": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "3m": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "gc europe": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "straumann": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "camlog": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "zirkonzahn": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "planmeca": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "sirona": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "kavo": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "w&h": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "nsk": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "dental labor": {"category": "rechnung", "doc_type": "Laborkostenrechnung"},
    
    # Software / IT
    "microsoft": {"category": "rechnung", "doc_type": "Software-Rechnung"},
    "google": {"category": "rechnung", "doc_type": "Software-Rechnung"},
    "apple": {"category": "rechnung", "doc_type": "Software-Rechnung"},
    "adobe": {"category": "rechnung", "doc_type": "Software-Rechnung"},
    "hetzner": {"category": "rechnung", "doc_type": "Hosting-Rechnung"},
    "strato": {"category": "rechnung", "doc_type": "Hosting-Rechnung"},
    "ionos": {"category": "rechnung", "doc_type": "Hosting-Rechnung"},
    
    # === PRAXISSOFTWARE (Zahnarzt/Arzt) ===
    "dampsoft": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "cgm": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "cgm dentalsysteme": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "charly": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "evident": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "red medical": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "tomedo": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "medatixx": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "zandura": {"category": "rechnung", "doc_type": "Praxissoftware-Rechnung"},
    "adg": {"category": "rechnung", "doc_type": "Abrechnungsdienstleister"},
    "pvs dental": {"category": "rechnung", "doc_type": "Abrechnungsdienstleister"},
    
    # === STEUERBERATER (typische Kanzleinamen) ===
    "steuerberatung": {"category": "buchhaltung", "doc_type": "Steuerberatung"},
    "stb": {"category": "buchhaltung", "doc_type": "Steuerberatung"},
    "steuerkanzlei": {"category": "buchhaltung", "doc_type": "Steuerberatung"},
    "wirtschaftsprüfung": {"category": "buchhaltung", "doc_type": "Wirtschaftsprüfung"},
    "rechtsanwalt": {"category": "geschaeftlich", "doc_type": "Rechtsanwalt"},
    "kanzlei": {"category": "geschaeftlich", "doc_type": "Kanzlei-Schreiben"},
    
    # === BEHÖRDEN ===
    "gewerbeamt": {"category": "behoerde", "doc_type": "Gewerbeanzeige"},
    "bauamt": {"category": "behoerde", "doc_type": "Baubescheid"},
    "gesundheitsamt": {"category": "behoerde", "doc_type": "Bescheid"},
    "veterinäramt": {"category": "behoerde", "doc_type": "Hygienekontrolle"},
    "ordnungsamt": {"category": "behoerde", "doc_type": "Bescheid"},
    "gewerbeaufsicht": {"category": "behoerde", "doc_type": "Prüfbericht"},
    "eichamt": {"category": "behoerde", "doc_type": "Eichprotokoll"},
    "arbeitsschutz": {"category": "behoerde", "doc_type": "Arbeitsschutz-Prüfung"},
    "kreisverwaltung": {"category": "behoerde", "doc_type": "Bescheid"},
    "landratsamt": {"category": "behoerde", "doc_type": "Bescheid"},
    "regierung": {"category": "behoerde", "doc_type": "Bescheid"},
    
    # === BERUFSGENOSSENSCHAFTEN ===
    "berufsgenossenschaft": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bgw": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg bau": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg etem": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg holz und metall": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg nahrungsmittel": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg verkehr": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bg energie": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bghm": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "bghw": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "vbg": {"category": "versicherung", "doc_type": "BG-Beitrag"},
    "ukh": {"category": "versicherung", "doc_type": "Unfallkasse"},
    
    # === WEITERE VERSICHERUNGEN ===
    "die bayerische": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "barmenia": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "hdı": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "itzehoer": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "die haftpflichtkasse": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "versicherungskammer bayern": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "vkb": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "wüstenrot": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "cosmos": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "ideal": {"category": "versicherung", "doc_type": "Versicherungspolice"},
    "hallesche": {"category": "versicherung", "doc_type": "Krankenversicherung"},
    "central": {"category": "versicherung", "doc_type": "Krankenversicherung"},
    "sdk": {"category": "versicherung", "doc_type": "Krankenversicherung"},
    "dkv": {"category": "versicherung", "doc_type": "Krankenversicherung"},
    
    # === WEITERE DENTAL-LIEFERANTEN UND LABORE ===
    "pluradent": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "orangedental": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "orangedent": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "kulzer": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "gebdi": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "schütz dental": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "bego": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "wieland dental": {"category": "rechnung", "doc_type": "Dental-Materialrechnung"},
    "exocad": {"category": "rechnung", "doc_type": "Dental-Software"},
    "medit": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "carestream": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "bien air": {"category": "rechnung", "doc_type": "Dental-Geräterechnung"},
    "dentallabor": {"category": "rechnung", "doc_type": "Laborkostenrechnung"},
    "zahntechnik": {"category": "rechnung", "doc_type": "Laborkostenrechnung"},
    
    # Post / Logistik
    "deutsche post": {"category": "rechnung", "doc_type": "Portorechnung"},
    "dhl": {"category": "rechnung", "doc_type": "Versandrechnung"},
    "ups": {"category": "rechnung", "doc_type": "Versandrechnung"},
    "dpd": {"category": "rechnung", "doc_type": "Versandrechnung"},
    "hermes": {"category": "rechnung", "doc_type": "Versandrechnung"},
    "gls": {"category": "rechnung", "doc_type": "Versandrechnung"},
}


# ============================================================
# Keyword-Patterns für Klassifizierung
# ============================================================
KEYWORD_PATTERNS = {
    "rechnung": {
        "keywords": ["rechnung", "invoice", "rechnungsnr", "rechnungsdatum", "netto", "brutto", 
                     "mwst", "umsatzsteuer", "zahlungsziel", "bankverbindung", "iban",
                     "rechnungsbetrag", "gesamtbetrag", "steuernummer"],
        "category": "rechnung",
        "confidence": 0.7
    },
    "lohnabrechnung": {
        "keywords": ["lohnabrechnung", "gehaltsabrechnung", "bruttolohn", "nettolohn",
                     "sozialversicherung", "lohnsteuer", "kirchensteuer", "solidaritätszuschlag",
                     "arbeitgeber", "arbeitnehmer", "personalnummer", "steuerklasse"],
        "category": "lohnabrechnung",
        "confidence": 0.8
    },
    "vertrag": {
        "keywords": ["vertrag", "vereinbarung", "vertragspartner", "laufzeit", "kündigung",
                     "kündigungsfrist", "vertragsgegenstand", "unterschrift"],
        "category": "vertrag",
        "confidence": 0.6
    },
    "mahnung": {
        "keywords": ["mahnung", "zahlungserinnerung", "fällig", "überfällig", "mahngebühr",
                     "letzte mahnung", "inkasso", "verzugszinsen"],
        "category": "mahnung",
        "confidence": 0.8
    },
    "kontoauszug": {
        "keywords": ["kontoauszug", "kontobewegungen", "saldo", "haben", "soll",
                     "buchungstag", "wertstellung", "verwendungszweck"],
        "category": "bank",
        "confidence": 0.8
    },
    "steuerbescheid": {
        "keywords": ["steuerbescheid", "einkommensteuerbescheid", "festsetzung", "finanzamt",
                     "zu versteuerndes einkommen", "vorauszahlung", "steuerschuld"],
        "category": "steuern",
        "confidence": 0.85
    },
    "versicherung": {
        "keywords": ["versicherungsschein", "police", "versicherungsnehmer", "prämie",
                     "deckungssumme", "selbstbeteiligung", "versicherungsfall"],
        "category": "versicherung",
        "confidence": 0.7
    },
    # === PERSONAL ===
    "arbeitsvertrag": {
        "keywords": ["arbeitsvertrag", "anstellungsvertrag", "beschäftigungsverhältnis",
                     "arbeitsbeginn", "probezeit", "vergütung", "arbeitszeit", "urlaub",
                     "tarifvertrag", "arbeitnehmer", "arbeitgeber", "einstellung"],
        "category": "personal",
        "confidence": 0.85
    },
    "kuendigung": {
        "keywords": ["kündigung", "kündigungsschreiben", "kündigungsfrist", "beendigung",
                     "arbeitsverhältnis beenden", "fristgemäß", "außerordentlich",
                     "kündigungsgrund", "arbeitgeber kündigt", "arbeitnehmer kündigt"],
        "category": "personal",
        "confidence": 0.9
    },
    "abmahnung": {
        "keywords": ["abmahnung", "pflichtverletzung", "vertragsverstoß", "fehlverhalten",
                     "verwarnung", "rüge", "arbeitsrechtlich"],
        "category": "personal",
        "confidence": 0.85
    },
    "zeugnis": {
        "keywords": ["arbeitszeugnis", "zeugnis", "qualifiziertes zeugnis", "einfaches zeugnis",
                     "beurteilung", "leistungsbeurteilung", "verhaltensbeurteilung"],
        "category": "personal",
        "confidence": 0.8
    },
    
    # === GUTACHTEN / PROTOKOLLE ===
    "gutachten": {
        "keywords": ["gutachten", "sachverständigengutachten", "bewertung", "expertise",
                     "fachgutachten", "beurteilung", "feststellung", "sachverständiger"],
        "category": "gutachten",
        "confidence": 0.8
    },
    "protokoll_versammlung": {
        "keywords": ["protokoll", "gesellschafterversammlung", "hauptversammlung",
                     "aufsichtsratssitzung", "vorstandssitzung", "betriebsrat",
                     "beschlussfassung", "tagesordnung", "abstimmung"],
        "category": "protokoll",
        "confidence": 0.8
    },
    "betriebsrat_protokoll": {
        "keywords": ["betriebsrat", "betriebsversammlung", "br-sitzung",
                     "betriebsvereinbarung", "arbeitnehmervertretung"],
        "category": "personal",
        "confidence": 0.8
    },
    
    # === DATENSCHUTZ (DSGVO) ===
    "dsgvo_dokument": {
        "keywords": ["dsgvo", "datenschutz", "datenschutzerklärung", "verarbeitungsverzeichnis",
                     "auftragsverarbeitung", "toms", "datenschutzfolgenabschätzung",
                     "einwilligung", "betroffenenrechte", "löschkonzept"],
        "category": "datenschutz",
        "confidence": 0.85
    },
    "einwilligung_dsgvo": {
        "keywords": ["einwilligung", "einverständniserklärung", "zustimmung",
                     "datenverarbeitung", "einwilligungserklärung", "widerruf"],
        "category": "datenschutz",
        "confidence": 0.8
    },
    
    # === BEHÖRDEN / BESCHEIDE ===
    "bescheid": {
        "keywords": ["bescheid", "verwaltungsakt", "behörde", "rechtsbehelfsbelehrung",
                     "widerspruch", "einspruch", "festsetzung", "verfügung",
                     "genehmigung", "ablehnung", "behördlich"],
        "category": "behoerde",
        "confidence": 0.8
    },
    "baugenehmigung": {
        "keywords": ["baugenehmigung", "bauantrag", "baubewilligung", "baufreigabe",
                     "bauaufsicht", "bauordnung", "baurecht"],
        "category": "behoerde",
        "confidence": 0.85
    },
    "betriebserlaubnis": {
        "keywords": ["betriebserlaubnis", "gewerbeerlaubnis", "konzession", "zulassung",
                     "gewerbeanzeige", "erlaubnis nach", "gaststättenerlaubnis"],
        "category": "behoerde",
        "confidence": 0.85
    },
    
    # === ZAHNARZT-SPEZIFISCH ===
    "heil_kostenplan": {
        "keywords": ["heil- und kostenplan", "hkp", "zahnersatz", "befund", "therapie",
                     "regelversorgung", "festzuschuss", "eigenanteil", "bonusheft"],
        "category": "behandlung",
        "confidence": 0.85
    },
    "laborbericht": {
        "keywords": ["laborbericht", "laborergebnis", "befund", "blutbild", "analyse",
                     "referenzwert", "normalwert"],
        "category": "labor",
        "confidence": 0.75
    },
    "roentgen": {
        "keywords": ["röntgen", "röntgenbild", "orthopantomogramm", "opg", "zahnfilm",
                     "dvt", "cbct", "panoramaschichtaufnahme"],
        "category": "roentgen",
        "confidence": 0.9
    },
}


# ============================================================
# Dokumenten-Benennungsregeln
# ============================================================
NAMING_RULES = {
    "rechnung": "{datum}_{absender}_RE-{rechnungsnr}",
    "lohnabrechnung": "{datum}_{mitarbeiter}_Lohnabrechnung_{monat}",
    "vertrag": "{datum}_{vertragspartner}_{vertragsart}",
    "kontoauszug": "{datum}_{bank}_Kontoauszug_{nummer}",
    "steuerbescheid": "{jahr}_{steuerart}_Bescheid",
    "mahnung": "{datum}_{absender}_Mahnung_{stufe}",
    "heil_kostenplan": "{datum}_{patient}_HKP",
    "patientenakte": "{patient}_{behandlung}_{datum}",
    "roentgen": "{datum}_{patient}_Röntgen_{typ}",
    "arbeitsvertrag": "{datum}_{mitarbeiter}_Arbeitsvertrag",
    "kuendigung": "{datum}_{mitarbeiter}_Kündigung",
    "protokoll": "{datum}_{typ}_Protokoll",
    "gutachten": "{datum}_{auftraggeber}_Gutachten",
    "bescheid": "{datum}_{behoerde}_{typ}_Bescheid",
    "bauvertrag": "{datum}_{auftraggeber}_Bauvertrag",
    "abnahme": "{datum}_{projekt}_Abnahme",
}


# ============================================================
# Zahnarztpraxis-spezifisches Wissen (UMFASSEND)
# ============================================================
DENTAL_KNOWLEDGE = {
    "abrechnungssysteme": {
        "bema": "Bewertungsmaßstab für zahnärztliche Leistungen (Kassenpatienten)",
        "goz": "Gebührenordnung für Zahnärzte (Privatpatienten)",
        "bel": "Bundeseinheitliches Leistungsverzeichnis (Zahntechnik)",
        "beb": "Bundeseinheitliche Benennungsliste (Zahntechnik-Material)",
    },
    "goz_struktur": {
        "abschnitt_a": "A — Allgemeine zahnärztliche Leistungen (GOZ 0010-0100)",
        "abschnitt_b": "B — Prophylaktische Leistungen (GOZ 1000-1040)",
        "abschnitt_k": "K — Konservierende Leistungen (GOZ 2000-2420)",
        "abschnitt_ch": "CH — Chirurgische Leistungen (GOZ 3000-3360)",
        "abschnitt_p": "P — Leistungen bei Erkrankungen der Mundschleimhaut (GOZ 4000-4090)",
        "abschnitt_par": "PAR — Parodontologie (GOZ 4020-4100)",
        "abschnitt_ip": "IP — Kieferbruch (GOZ 5000-5280)",
        "abschnitt_kfo": "KFO — Kieferorthopädie (GOZ 6000-6100)",
        "abschnitt_i": "I — Implantologie (Analog-GOZ)",
        "abschnitt_z": "Z — Zahnersatz (GOZ 5000-5320)",
    },
    "goz_haeufig": {
        "0010": "Beratung (mindestens 10 Min)",
        "0040": "Histologische Untersuchung",
        "1000": "Professionelle Zahnreinigung (PZR)",
        "2000": "Adhäsive Rekonstruktion (Füllung)",
        "2060": "Wurzelkanalfüllung",
        "2197": "Aufbaufüllung",
        "3000": "Einfache Extraktion",
        "3030": "Operative Entfernung (Osteotomie)",
        "4000": "Mundschleimhaut-Behandlung",
        "4050": "Geschlossene Parodontalbehandlung",
        "4060": "Offene Parodontalbehandlung",
        "5000": "Vollkrone",
        "5100": "Suprakonstruktion (Implantat)",
        "analog_9000": "Implantation (nach §6 Abs.1 GOZ analog)",
    },
    "bema_struktur": {
        "untersuchung": "01, 02, 04 — Untersuchungen",
        "konservierend": "13, 15, 17 — Füllungen",
        "zahnersatz": "40-80 — Zahnersatz (Regelversorgung + Brücken)",
        "parodontologie": "P200-P203 — PAR-Behandlung",
        "chirurgie": "X, Xn — Extraktionen, Osteotomien",
        "roentgen": "0020, 0030, 5000-5004 — Röntgen",
        "prophylaxe": "IP1-IP5, FU — Individualprophylaxe",
    },
    "bema_haeufig": {
        "01": "Untersuchung zur Feststellung von Zahn-, Mund- und Kieferkrankheiten",
        "13a": "Exkavieren (einflächig)",
        "13b": "Exkavieren (zweiflächig)",
        "13c": "Exkavieren (dreiflächig)",
        "13d": "Exkavieren (mehrflächig)",
        "15": "Adhäsive Rekonstruktion (einflächig)",
        "17": "Adhäsive Rekonstruktion (zweiflächig)",
        "X": "Extraktion",
        "Xn": "Operative Entfernung",
        "0020": "Intraorales Röntgenbild (Zahnfilm)",
        "0030": "Panorama-Röntgenaufnahme (OPG)",
        "P200": "Geschlossene PAR-Behandlung (je Zahn)",
        "P201": "Offene PAR-Behandlung (je Zahn)",
    },
    "dokumentationspflichten": {
        "behandlungsdoku": "Jede Behandlung dokumentieren (§630f BGB) — Diagnose, Therapie, Aufklärung",
        "roentgen_indikation": "Rechtfertigende Indikation vor jeder Röntgenaufnahme dokumentieren",
        "hygiene_validierung": "Sterilisator-Validierung dokumentieren, Chargenkontrolle",
        "medizinprodukte": "Aufbereitung dokumentieren nach MPBetreibV",
        "qm": "QM-Handbuch führen (§135a SGB V), jährlich reviewen",
        "hkp_aufbewahrung": "HKP 10 Jahre aufbewahren (§630f BGB)",
        "implantologie": "Implantatpass ausstellen, Chargendoku, 10 Jahre Aufbewahrung",
        "kfo": "Modelle vor/nach KFO-Behandlung aufbewahren (Beweissicherung)",
    },
    "fristen_praxis": {
        "quartalsabrechnung": "Quartalsweise an KZV übermitteln",
        "hkp_genehmigung": "HKP VOR Behandlungsbeginn von Kasse genehmigen lassen",
        "nachsorge": "Nachsorge-Dokumentation nach Implantation/Chirurgie",
        "recall": "Recall nach PAR-Behandlung (3-6 Monate)",
    },
    "haeufige_diagnosen": {
        "c02": "Karies (ICD-10)",
        "k05": "Gingivitis",
        "k08": "Zahnverlust",
        "k10": "Kieferzyste",
        "z01.2": "Zahnärztliche Vorsorgeuntersuchung",
    }
}


# ============================================================
# HANDWERK-spezifisches Wissen
# ============================================================
HANDWERK_KNOWLEDGE = {
    "gewaehrleistung": {
        "werkvertrag": "5 Jahre für Bauwerke (§634a BGB)",
        "kaufvertrag": "2 Jahre für bewegliche Sachen (§438 BGB)",
        "vob_b": "VOB/B §13: 4 Jahre für Mängel",
    },
    "dokumentation": {
        "aufmass": "Aufmaße dokumentieren (Grundlage Abrechnung)",
        "abnahme": "Abnahmeprotokoll erstellen (Beweissicherung)",
        "wartung": "Wartungsprotokolle 10 Jahre aufbewahren (Produkthaftung)",
    },
    "vorschriften": {
        "pruefpflicht": "Prüfpflichtige Geräte dokumentieren (BetrSichV)",
        "meisterpflicht": "Meisterbrief bei zulassungspflichtigen Handwerken",
    }
}


# ============================================================
# GASTRONOMIE-spezifisches Wissen
# ============================================================
GASTRO_KNOWLEDGE = {
    "haccp": {
        "grundlage": "LMHV §5 — Eigenkontrollen dokumentieren",
        "temperatur": "Kühl-/Warmhaltung dokumentieren (täglich)",
        "reinigung": "Reinigungspläne erstellen und dokumentieren",
        "wareneingang": "Wareneingang prüfen und dokumentieren",
    },
    "schulungen": {
        "infektionsschutz": "§43 IfSG — Erstbelehrung + alle 2 Jahre",
        "lebensmittelhygiene": "Regelmäßige Schulungen (Nachweis 3 Jahre)",
    },
    "kontrollen": {
        "amtlich": "Amtliche Kontrollen durch Lebensmittelüberwachung (5 Jahre aufbewahren)",
        "eigenkontrollen": "HACCP-Protokolle mindestens 2 Jahre",
    },
    "allergene": {
        "kennzeichnung": "LMIV Art.21 — Allergene kennzeichnen",
        "dokumentation": "Allergenliste aktuell halten + 2 Jahre alte",
    }
}


# ============================================================
# IT-Branche-spezifisches Wissen
# ============================================================
IT_KNOWLEDGE = {
    "dsgvo_basics": {
        "rechenschaftspflicht": "Art.5 Abs.2 DSGVO — Nachweispflicht für Compliance",
        "verarbeitungsverzeichnis": "Art.30 DSGVO — VVT führen (ab 250 MA, sonst wenn risikoreich)",
        "toms": "Art.32 DSGVO — Technische/Organisatorische Maßnahmen dokumentieren",
        "auftragsverarbeitung": "Art.28 DSGVO — AV-Verträge schriftlich + Kontrolle",
    },
    "datenpannen": {
        "meldefrist": "72 Stunden an Aufsichtsbehörde (Art.33 DSGVO)",
        "dokumentation": "Jede Datenpanne dokumentieren (auch nicht-meldepflichtige)",
    },
    "loeschung": {
        "loeschkonzept": "Löschfristen definieren und einhalten (Art.17 DSGVO)",
        "aufbewahrungsfristen": "Gesetzliche Aufbewahrungsfristen beachten (nicht vorzeitig löschen!)",
    },
    "betroffenenrechte": {
        "auskunft": "Art.15 DSGVO — Auskunft innerhalb 1 Monat",
        "widerruf": "Einwilligung jederzeit widerrufbar (Art.7 Abs.3)",
    }
}
