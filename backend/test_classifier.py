#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Classifier - Analyze sample PDFs manually
"""

import json
from pathlib import Path
import fitz  # PyMuPDF
from llama_cpp import Llama

# ==================== CONFIG ====================

PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")
MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")

SAMPLE_FILES = [
    "dokument_103.pdf",
    "Aufklärungspflichten.pdf",
    "Datenschutz  IT-Sicherheit in der Zahnarztpraxis.pdf",
    "Ablaufdiagramm für die Zahnarztpraxis.pdf",
    "09102023GOZ ON TOUR-Materialien  Protesttag  F.pdf",
]

CLASSIFIER_PROMPT = """Klassifiziere dieses Dokument:

Typen:
- checkliste: Hat Ja/Nein-Fragen, Verantwortliche, Erledigungs-Status
- arbeitsanweisung: Hat nummerierte Schritte, Bullet-Points, Prozess-Beschreibung
- sonstige: Alles andere

Text:
{text}

Antworte NUR mit dem Typ (ohne Erklärung):"""

# ==================== FUNCTIONS ====================

def extract_text(pdf_path, max_chars=3000):
    """Extract text from PDF"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:max_chars]
    except Exception as e:
        return f"ERROR: {e}"

def classify_with_llm(text, llm):
    """Classify with LLM"""
    prompt = CLASSIFIER_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=50,
        temperature=0.1,
        stop=["\n", ".", "Text", "Typ"]
    )
    raw = response["choices"][0]["text"].strip()
    return raw

def main():
    print("=" * 80)
    print("CLASSIFIER TEST - Manual Analysis")
    print("=" * 80)
    
    # Load LLM
    print(f"\nLoading LLM: {MODEL_PATH.name}...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=4096,
        n_threads=4,
        verbose=False
    )
    print("OK LLM loaded\n")
    
    results = []
    
    for filename in SAMPLE_FILES:
        pdf_path = PDF_FOLDER / filename
        
        if not pdf_path.exists():
            print(f"SKIP: {filename} (not found)")
            continue
        
        print(f"\n{'='*80}")
        print(f"FILE: {filename}")
        print(f"{'='*80}")
        
        # Extract text
        text = extract_text(pdf_path)
        print(f"\nText Length: {len(text)} chars")
        print(f"\nFirst 500 chars:")
        print("-" * 80)
        print(text[:500])
        print("-" * 80)
        
        # Classify with LLM
        print(f"\nClassifying with LLM...")
        classification = classify_with_llm(text, llm)
        print(f"LLM Response: '{classification}'")
        
        # Manual analysis
        print(f"\nMANUAL ANALYSIS:")
        has_checkboxes = "□" in text or "☐" in text or "[  ]" in text or "[ ]" in text
        has_numbered_steps = any(f"{i}." in text for i in range(1, 20))
        has_bullet_points = "■" in text or "•" in text or "- " in text[:1000]
        has_questions = "?" in text
        
        print(f"  - Has checkboxes: {has_checkboxes}")
        print(f"  - Has numbered steps: {has_numbered_steps}")
        print(f"  - Has bullet points: {has_bullet_points}")
        print(f"  - Has questions: {has_questions}")
        
        # Guess type
        if has_checkboxes and has_questions:
            manual_type = "checkliste"
        elif has_numbered_steps or has_bullet_points:
            manual_type = "arbeitsanweisung"
        else:
            manual_type = "sonstige"
        
        print(f"\n  MANUAL GUESS: {manual_type}")
        print(f"  LLM SAID: {classification}")
        print(f"  MATCH: {'✅' if manual_type in classification.lower() else '❌'}")
        
        results.append({
            "file": filename,
            "text_length": len(text),
            "text_preview": text[:500],
            "llm_response": classification,
            "manual_guess": manual_type,
            "features": {
                "checkboxes": has_checkboxes,
                "numbered_steps": has_numbered_steps,
                "bullet_points": has_bullet_points,
                "questions": has_questions
            }
        })
    
    # Save results
    report_file = Path("C:/Jarvix/vera-office/backend/classifier_test_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"Report saved: {report_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
