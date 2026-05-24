#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERA QM Template Parser - Phase 2

Extrahiert Fragen + Prozesse aus 447 BLZK-QM-PDFs.
Nutzt LLM (Mistral 7B lokal) für strukturierte Extraktion.

Input:  C:/Jarvix/QM/data/blzk_downloads/*.pdf
Output: vera.db (qm_questions, qm_processes) + extraction_report.json
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import hashlib
import pickle
from datetime import datetime

# PDF Text Extraction
import fitz  # PyMuPDF

# LLM
from llama_cpp import Llama

# Progress Bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("WARN  tqdm not installed, no progress bar")


# ==================== CONFIG ====================

PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")  # 447 BLZK PDFs
VERA_DB = Path("C:/Jarvix/vera-office/backend/data/vera.db")
MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
CACHE_DIR = Path("C:/Jarvix/vera-office/backend/cache/qm_parsed")
REPORT_FILE = Path("C:/Jarvix/vera-office/backend/extraction_report.json")

MAX_WORKERS = 1  # Parallel processing (MUST be 1 - LLM is not thread-safe!)
TEST_MODE = False  # Set to False for full batch
TEST_LIMIT = 10  # Only process first N PDFs in test mode
LLM_CONTEXT_SIZE = 4096
LLM_THREADS = 4
TEMPERATURE = 0.1  # Deterministisch


# ==================== LLM PROMPTS ====================

DOCUMENT_TYPE_CLASSIFIER = """Du bist ein Experte für Qualitäts- und Arbeitsschutzmanagement.

AUFGABE: Klassifiziere ein QM-Dokument in eine der 3 Kategorien.

INPUT:
- Title: {title}
- First 500 chars: {text_preview}

OUTPUT (NUR VALID JSON):
{{
  "document_category": "checkliste|arbeitsanweisung|sonstige",
  "confidence": "high|medium|low",
  "reasoning": "..."
}}

KATEGORIEN:
- checkliste: Ja/Nein-Fragen, Checkboxen, □ ☐ [x]
- arbeitsanweisung: Nummerierte Schritte, Bullets, Prozess
- sonstige: Konzepte, Formulare, Zertifikate

OUTPUT NUR JSON (kein anderer Text!):"""

CHECKLIST_EXTRACTION_PROMPT = """Du bist ein Experte für Qualitätsmanagement in Zahnarztpraxen.

AUFGABE: Extrahiere alle Fragen aus dieser Checkliste.

INPUT-TEXT:
{pdf_text}

OUTPUT (NUR VALID JSON):
{{
  "items": [
    {{
      "question": "...",
      "type": "ja_nein|text|datum",
      "responsible": "...",
      "reference": "..."
    }}
  ]
}}

REGELN:
- Suche nach: □, ☐, [x], [ ], ☑, ☒
- Extrahiere Frage nach Checkbox
- Verantwortlich: "Verantwortlich:", "Zuständig:"
- Referenzen: § X, Formular Y, DGUV

OUTPUT NUR JSON (kein anderer Text!):"""

PROCEDURE_EXTRACTION_PROMPT = """Du bist ein Experte für Arbeitsschutz in Zahnarztpraxen.

AUFGABE: Extrahiere Schritt-für-Schritt Prozess.

INPUT-TEXT:
{pdf_text}

OUTPUT (NUR VALID JSON):
{{
  "steps": [
    {{
      "step_number": 1,
      "title": "...",
      "actions": ["...", "..."]
    }}
  ]
}}

REGELN:
- Suche nach: "1.", "2.", "3." oder ■, •, *
- Extrahiere Haupt-Schritte + Actions
- Nummerierung muss logisch sein

OUTPUT NUR JSON (kein anderer Text!):"""


# ==================== LLM MANAGER ====================

class QMLLMManager:
    """Singleton LLM Manager für QM-Parsing"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print(f" Loading LLM: {MODEL_PATH.name}")
        
        self.llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=LLM_CONTEXT_SIZE,
            n_threads=LLM_THREADS,
            verbose=False
        )
        
        self._initialized = True
        print("OK LLM loaded")
    
    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate completion"""
        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            stop=["</s>", "\n\n\n"]  # Stop sequences
        )
        
        return response["choices"][0]["text"].strip()


# ==================== PDF PARSER ====================

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrahiere Text aus PDF mit PyMuPDF"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        return text
    
    except Exception as e:
        print(f"ERR PDF read error: {pdf_path.name}: {e}")
        return ""


# ==================== CACHE ====================

def get_cache_key(pdf_path: Path) -> str:
    """Generate SHA256 hash of PDF file"""
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_from_cache(pdf_path: Path) -> Optional[Dict]:
    """Load parsed data from cache"""
    cache_key = get_cache_key(pdf_path)
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    
    return None


def save_to_cache(pdf_path: Path, data: Dict):
    """Save parsed data to cache"""
    cache_key = get_cache_key(pdf_path)
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)


# ==================== DOCUMENT PARSER ====================

def parse_qm_document(pdf_path: Path, llm: QMLLMManager) -> Dict:
    """
    Parse ein QM-PDF und extrahiere strukturierte Daten
    
    Returns:
        {
            "file": str,
            "type": "checklist|procedure|other",
            "data": {...},
            "error": str | None
        }
    """
    
    # 1. Check Cache
    cached = load_from_cache(pdf_path)
    if cached:
        return cached
    
    result = {
        "file": pdf_path.name,
        "type": "unknown",
        "data": {},
        "error": None
    }
    
    try:
        # 2. Extract Text
        text = extract_text_from_pdf(pdf_path)
        
        if not text or len(text) < 50:
            result["error"] = "Empty or too short"
            return result
        
        # 3. Classify Document Type
        classifier_prompt = DOCUMENT_TYPE_CLASSIFIER.format(
            title=pdf_path.stem,
            text_preview=text[:500]
        )
        
        classification_text = llm.complete(classifier_prompt, max_tokens=200)
        
        # Parse JSON (robust)
        try:
            # Extrahiere JSON aus Response (manchmal kommt extra Text)
            json_start = classification_text.find("{")
            json_end = classification_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                classification = json.loads(classification_text[json_start:json_end])
            else:
                raise ValueError("No JSON in response")
        
        except Exception as e:
            # Fallback: Keyword-basiert
            text_lower = text.lower()
            if "checkliste" in text_lower or "□" in text:
                classification = {"document_category": "checkliste"}
            elif "arbeitsanweisung" in text_lower or "schritt" in text_lower:
                classification = {"document_category": "arbeitsanweisung"}
            else:
                classification = {"document_category": "sonstige"}
        
        doc_type = classification.get("document_category", "sonstige")
        result["type"] = doc_type
        
        # 4. Extract based on type
        if doc_type == "checkliste":
            prompt = CHECKLIST_EXTRACTION_PROMPT.format(pdf_text=text[:3000])
            extraction = llm.complete(prompt, max_tokens=2000)
            
            # Parse JSON
            try:
                json_start = extraction.find("{")
                json_end = extraction.rfind("}") + 1
                result["data"] = json.loads(extraction[json_start:json_end])
            except:
                result["data"] = {"items": []}
                result["error"] = "JSON parse failed"
        
        elif doc_type == "arbeitsanweisung":
            prompt = PROCEDURE_EXTRACTION_PROMPT.format(pdf_text=text[:3000])
            extraction = llm.complete(prompt, max_tokens=2000)
            
            # Parse JSON
            try:
                json_start = extraction.find("{")
                json_end = extraction.rfind("}") + 1
                result["data"] = json.loads(extraction[json_start:json_end])
            except:
                result["data"] = {"steps": []}
                result["error"] = "JSON parse failed"
        
        else:
            result["data"] = {"text": text[:1000]}
        
        # 5. Cache result
        save_to_cache(pdf_path, result)
    
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ==================== DATABASE ====================

def create_qm_tables(conn: sqlite3.Connection):
    """Erstelle qm_questions + qm_processes Tabellen"""
    
    cursor = conn.cursor()
    
    # qm_questions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qm_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            chapter VARCHAR(128),
            question_text TEXT NOT NULL,
            question_type VARCHAR(20),
            responsible VARCHAR(128),
            compliance_ref VARCHAR(256),
            required BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    # qm_processes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qm_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            process_name VARCHAR(256) NOT NULL,
            steps JSON,
            reference_images JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    conn.commit()
    print("OK DB tables created")


def save_to_database(results: List[Dict], conn: sqlite3.Connection):
    """Speichere Extraction-Results in DB"""
    
    cursor = conn.cursor()
    
    stats = {"questions": 0, "processes": 0, "errors": 0}
    
    for result in results:
        if result.get("error"):
            stats["errors"] += 1
            continue
        
        # Get or create document_id (stub - würde normalerweise in documents table schauen)
        doc_id = None  # TODO: Lookup in documents table by filename
        
        if result["type"] == "checkliste":
            for item in result["data"].get("items", []):
                cursor.execute("""
                    INSERT INTO qm_questions 
                    (document_id, question_text, question_type, responsible, compliance_ref)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    item.get("question", ""),
                    item.get("type", "ja_nein"),
                    item.get("responsible", "nicht definiert"),
                    item.get("reference", "")
                ))
                stats["questions"] += 1
        
        elif result["type"] == "arbeitsanweisung":
            steps_json = json.dumps(result["data"].get("steps", []))
            
            cursor.execute("""
                INSERT INTO qm_processes 
                (document_id, process_name, steps)
                VALUES (?, ?, ?)
            """, (
                doc_id,
                result["file"],
                steps_json
            ))
            stats["processes"] += 1
    
    conn.commit()
    
    print(f"OK Saved to DB: {stats['questions']} questions, {stats['processes']} processes")
    return stats


# ==================== BATCH PROCESSING ====================

def batch_process_pdfs(pdf_folder: Path, max_workers: int = 4, limit: int = None) -> List[Dict]:
    """
    Process all PDFs in parallel
    """
    
    # Get all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if limit:
        pdf_files = pdf_files[:limit]
        print(f"TEST MODE: Processing {len(pdf_files)} PDFs")
    else:
        print(f"Found {len(pdf_files)} PDFs")
    
    if not pdf_files:
        return []
    
    # Initialize LLM (once!)
    llm = QMLLMManager()
    
    # Process in parallel
    results = []
    
    if HAS_TQDM:
        progress = tqdm(total=len(pdf_files), desc="Processing PDFs")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(parse_qm_document, pdf, llm): pdf
            for pdf in pdf_files
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            if HAS_TQDM:
                progress.update(1)
    
    if HAS_TQDM:
        progress.close()
    
    return results


# ==================== REPORTING ====================

def generate_report(results: List[Dict]) -> Dict:
    """Generate extraction report"""
    
    stats = {
        "total_pdfs": len(results),
        "checklists": 0,
        "procedures": 0,
        "other": 0,
        "errors": 0,
        "total_questions": 0,
        "total_steps": 0
    }
    
    for result in results:
        if result.get("error"):
            stats["errors"] += 1
            continue
        
        doc_type = result["type"]
        
        if doc_type == "checkliste":
            stats["checklists"] += 1
            stats["total_questions"] += len(result["data"].get("items", []))
        
        elif doc_type == "arbeitsanweisung":
            stats["procedures"] += 1
            stats["total_steps"] += len(result["data"].get("steps", []))
        
        else:
            stats["other"] += 1
    
    return stats


def save_report(results: List[Dict], stats: Dict, report_file: Path):
    """Save full report to JSON"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "results": results
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Report saved: {report_file}")


# ==================== MAIN ====================

def main():
    """Main execution"""
    
    print("=" * 60)
    print("VERA QM Template Parser - Phase 2")
    print("=" * 60)
    
    # 1. Check Paths
    if not PDF_FOLDER.exists():
        print(f"ERR PDF folder not found: {PDF_FOLDER}")
        return
    
    if not MODEL_PATH.exists():
        print(f"ERR LLM model not found: {MODEL_PATH}")
        return
    
    if not VERA_DB.exists():
        print(f"ERR VERA DB not found: {VERA_DB}")
        return
    
    # 2. Process PDFs
    print(f"\n Processing PDFs from: {PDF_FOLDER}")
    test_limit = TEST_LIMIT if TEST_MODE else None; results = batch_process_pdfs(PDF_FOLDER, max_workers=MAX_WORKERS, limit=test_limit)
    
    # 3. Generate Stats
    stats = generate_report(results)
    
    print("\n" + "=" * 60)
    print("EXTRACTION STATS")
    print("=" * 60)
    print(f"Total PDFs:       {stats['total_pdfs']}")
    print(f"OK Checklists:     {stats['checklists']} ({stats['total_questions']} questions)")
    print(f"OK Procedures:     {stats['procedures']} ({stats['total_steps']} steps)")
    print(f"--  Other:          {stats['other']}")
    print(f"ERR Errors:         {stats['errors']}")
    
    # 4. Save to Database
    print("\n Saving to database...")
    conn = sqlite3.connect(VERA_DB)
    create_qm_tables(conn)
    db_stats = save_to_database(results, conn)
    conn.close()
    
    # 5. Save Report
    save_report(results, stats, REPORT_FILE)
    
    print("\nOK PHASE 2 COMPLETE!")
    print(f"   Questions extracted: {stats['total_questions']}")
    print(f"   Processes extracted: {stats['total_steps']}")
    print(f"   Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()

