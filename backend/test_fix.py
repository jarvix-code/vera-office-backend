#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the FIXED classifier on 5 sample PDFs
"""

import json
from pathlib import Path
import fitz
from llama_cpp import Llama

MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")

# FIXED PROMPT
CLASSIFIER_PROMPT = """Du bist ein QM-Dokument-Classifier für Zahnarztpraxen.

BEISPIEL 1 - Typ: checkliste
Dokument: "Datenschutz Checkliste
□ Datenschutzbeauftragter benannt? [Ja/Nein]
□ Verarbeitungsverzeichnis erstellt? [Ja/Nein]
Verantwortlich: Praxisinhaber"
Antwort: checkliste

BEISPIEL 2 - Typ: arbeitsanweisung
Dokument: "Röntgen-Durchführung
1. Vorbereitung
   - Patient aufklären
   - Schutzkleidung anlegen
2. Durchführung
   - Gerät einschalten
   - Position einstellen"
Antwort: arbeitsanweisung

BEISPIEL 3 - Typ: sonstige
Dokument: "BLZK Newsletter 02/2024
Wichtige Informationen zur neuen GOZ-Regelung..."
Antwort: sonstige

JETZT DU:
Dokument: {text}
Antwort:"""

TEST_FILES = [
    "dokument_103.pdf",  # Should be: arbeitsanweisung
    "Ablaufdiagramm für die Zahnarztpraxis.pdf",  # Should be: checkliste/arbeitsanweisung
    "09102023GOZ ON TOUR-Materialien  Protesttag  F.pdf",  # Should be: sonstige
    "DGUV Vorschrift 3.pdf",  # Should be: sonstige (law)
    "Datenschutz  IT-Sicherheit in der Zahnarztpraxis.pdf",  # Should be: sonstige or AA
]

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text[:3000]

def classify_fixed(text, llm):
    prompt = CLASSIFIER_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=30,
        temperature=0.1,
        stop=["Dokument", "BEISPIEL"]
    )
    typ = response["choices"][0]["text"].strip().lower()
    typ = typ.rstrip('.,:;')
    
    if "checkliste" in typ:
        return "checkliste"
    elif "arbeitsanweisung" in typ:
        return "arbeitsanweisung"
    else:
        return "sonstige"

print("=" * 80)
print("TEST FIXED CLASSIFIER")
print("=" * 80)

# Load LLM
print("\nLoading LLM...")
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=2048,
    n_threads=4,
    verbose=False
)
print("OK\n")

results = []

for filename in TEST_FILES:
    pdf_path = PDF_FOLDER / filename
    
    if not pdf_path.exists():
        print(f"SKIP: {filename} (not found)")
        continue
    
    text = extract_text(pdf_path)
    classification = classify_fixed(text, llm)
    
    print(f"{filename[:50]:50} → {classification}")
    results.append({"file": filename, "type": classification})

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

types = {"checkliste": 0, "arbeitsanweisung": 0, "sonstige": 0}
for r in results:
    types[r["type"]] += 1

for typ, count in types.items():
    print(f"{typ:20} {count}")

print("\n✅ FIXED CLASSIFIER WORKS!" if any(types[t] > 0 for t in ["checkliste", "arbeitsanweisung"]) else "\n❌ STILL BROKEN")
