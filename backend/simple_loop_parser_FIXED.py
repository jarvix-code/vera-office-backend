#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMPLE LOOP PARSER - FIXED VERSION
Process PDFs ONE BY ONE with IMPROVED CLASSIFIER
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
from llama_cpp import Llama

# ==================== CONFIG ====================

PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")
VERA_DB = Path("C:/Jarvix/vera-office/data/vera.db")
MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instral-v0.2.Q4_K_M.gguf")
REPORT_FILE = Path("C:/Jarvix/vera-office/backend/extraction_report_fixed.json")

# ==================== PROMPTS ====================

# FIXED: Few-Shot Prompt (V2_FEWSHOT)
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

PROCEDURE_PROMPT = """Extrahiere Prozess-Schritte aus dieser Arbeitsanweisung:

{text}

Gib JSON zurück:
{{
  "steps": [
    {{"step_number": 1, "title": "...", "actions": ["...", "..."]}},
    ...
  ]
}}

NUR JSON, keine Erklärung:"""

# ==================== FUNCTIONS ====================

def extract_text(pdf_path):
    """Extract text from PDF"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text[:3000]  # First 3000 chars

def classify_document(text, llm):
    """Classify document type - FIXED VERSION"""
    prompt = CLASSIFIER_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=30,  # FIXED: Increased from 20
        temperature=0.1,
        stop=["Dokument", "BEISPIEL"]  # FIXED: Better stop tokens (not "\n"!)
    )
    typ = response["choices"][0]["text"].strip().lower()
    
    # FIXED: Remove trailing punctuation
    typ = typ.rstrip('.,:;')
    
    if "checkliste" in typ:
        return "checkliste"
    elif "arbeitsanweisung" in typ or "procedure" in typ:
        return "arbeitsanweisung"
    else:
        return "sonstige"

def extract_procedure(text, llm):
    """Extract steps from procedure"""
    prompt = PROCEDURE_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=500,
        temperature=0.1
    )
    
    try:
        data = json.loads(response["choices"][0]["text"])
        return data.get("steps", [])
    except:
        return []

def create_tables(conn):
    """Create DB tables if not exist"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qm_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            process_name VARCHAR(256),
            steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qm_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            question_text TEXT,
            question_type VARCHAR(20),
            responsible VARCHAR(128),
            compliance_ref VARCHAR(256),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()

def save_to_db(conn, pdf_name, doc_type, data):
    """Save result to database"""
    if doc_type == "arbeitsanweisung" and data:
        steps_json = json.dumps(data, ensure_ascii=False)
        conn.execute("""
            INSERT INTO qm_processes (process_name, steps)
            VALUES (?, ?)
        """, (pdf_name, steps_json))
        conn.commit()

# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("SIMPLE LOOP PARSER - FIXED VERSION")
    print("=" * 60)
    
    # Check paths
    if not PDF_FOLDER.exists():
        print(f"ERR: PDF folder not found: {PDF_FOLDER}")
        return
    
    if not MODEL_PATH.exists():
        print(f"ERR: Model not found: {MODEL_PATH}")
        return
    
    # Get PDFs
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDFs")
    
    if not pdf_files:
        return
    
    # Load LLM
    print(f"Loading LLM: {MODEL_PATH.name}...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=4096,
        n_threads=4,
        verbose=False
    )
    print("OK LLM loaded\n")
    
    # Connect DB
    conn = sqlite3.connect(VERA_DB)
    create_tables(conn)
    
    # Process ONE BY ONE
    results = []
    stats = {
        "total": len(pdf_files),
        "checkliste": 0,
        "arbeitsanweisung": 0,
        "sonstige": 0,
        "error": 0,
        "steps": 0
    }
    
    for i, pdf in enumerate(pdf_files, 1):
        try:
            print(f"[{i}/{len(pdf_files)}] {pdf.name}...", end=" ", flush=True)
            
            # Extract text
            text = extract_text(pdf)
            
            # Classify
            doc_type = classify_document(text, llm)
            
            # Extract data
            data = None
            if doc_type == "arbeitsanweisung":
                data = extract_procedure(text, llm)
                if data:
                    stats["steps"] += len(data)
                    save_to_db(conn, pdf.name, doc_type, data)
            
            # Save result
            result = {
                "file": pdf.name,
                "type": doc_type,
                "data": data,
                "error": None
            }
            results.append(result)
            stats[doc_type] += 1
            
            print(f"OK ({doc_type})")
            
        except Exception as e:
            print(f"ERR: {e}")
            results.append({
                "file": pdf.name,
                "type": "error",
                "data": None,
                "error": str(e)
            })
            stats["error"] += 1
    
    # Close DB
    conn.close()
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "results": results
    }
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print stats
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total:          {stats['total']}")
    print(f"Checklisten:    {stats['checkliste']}")
    print(f"Arbeitsanw.:    {stats['arbeitsanweisung']} ({stats['steps']} steps)")
    print(f"Sonstige:       {stats['sonstige']}")
    print(f"Errors:         {stats['error']}")
    print(f"\nReport: {REPORT_FILE}")

if __name__ == "__main__":
    main()
