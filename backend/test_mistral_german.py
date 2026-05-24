#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST: Mistral 7B German QM Performance
Prüft ob Mistral 7B gut genug für deutsche QM-Dokumente ist (ohne extra Training!)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import fitz  # PyMuPDF
from llama_cpp import Llama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================

MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")
REPORT_FILE = Path("C:/Jarvix/vera-office/backend/mistral_german_test_report.json")

# ==================== TEST SAMPLES ====================

# Synthetische deutsche QM-Text Samples
SYNTHETIC_SAMPLES = [
    {
        "text": "□ Datenschutzbeauftragter benannt? [Ja/Nein]\nVerantwortlich: Praxisinhaber",
        "expected": "checkliste",
        "description": "Simple Checkliste mit Checkbox"
    },
    {
        "text": "1. Vorbereitung\n■ Patient aufklären\n■ Schutzkleidung anlegen\n2. Durchführung",
        "expected": "arbeitsanweisung",
        "description": "Arbeitsanweisung mit nummerierten Schritten"
    },
    {
        "text": "BLZK Newsletter 02/2024 - Wichtige Infos zur GOZ...",
        "expected": "sonstige",
        "description": "Newsletter/Info-Dokument"
    },
    {
        "text": "Hygieneplan Desinfektion\n1. Händedesinfektion durchführen\n2. Flächen desinfizieren\n3. Dokumentation",
        "expected": "arbeitsanweisung",
        "description": "Prozess-Beschreibung mit Schritten"
    },
    {
        "text": "□ Erste-Hilfe-Material vollständig? [Ja/Nein]\n□ Ablaufdatum geprüft? [Ja/Nein]\nVerantwortlich: ZMF",
        "expected": "checkliste",
        "description": "Mehrere Checkboxen mit Verantwortlichem"
    },
    {
        "text": "Qualitätszirkel Protokoll 03/2024\nTeilnehmer: Dr. Müller, ZMF Schmidt\nThemen: Hygienekonzept, Gerätewartung",
        "expected": "sonstige",
        "description": "Protokoll/Meeting-Notes"
    },
]

# Deutsche QM-Fachbegriffe Test
FACHBEGRIFFE_TEST = [
    "Hygieneplan",
    "Medizinprodukteaufbereitung",
    "Qualitätszirkel",
    "Arbeitsschutzgesetz",
    "DSGVO-Compliance",
    "Sterilisation",
    "Dokumentationspflicht",
    "Geräteeinweisung",
    "Notfallmanagement",
    "Praxishygiene"
]

# ==================== PROMPT VARIANTS ====================

# Deutsche Few-Shot Prompts
PROMPT_DE_FEWSHOT = """Du bist ein QM-Dokument-Klassifikator für Zahnarztpraxen.

BEISPIEL 1 - Typ: checkliste
Dokument: "□ Datenschutzbeauftragter benannt? [Ja/Nein]\nVerantwortlich: Praxisinhaber"
Antwort: checkliste

BEISPIEL 2 - Typ: arbeitsanweisung
Dokument: "1. Vorbereitung ■ Patient aufklären\n2. Durchführung ■ Gerät einschalten"
Antwort: arbeitsanweisung

BEISPIEL 3 - Typ: sonstige
Dokument: "BLZK Newsletter 02/2024 - Wichtige Infos zur GOZ..."
Antwort: sonstige

JETZT DU:
Dokument: {text}
Antwort:"""

# Englische Few-Shot Prompts (zum Vergleich)
PROMPT_EN_FEWSHOT = """You are a QM document classifier for dental practices.

EXAMPLE 1 - Type: checklist
Document: "□ Data protection officer appointed? [Yes/No]\nResponsible: Practice owner"
Answer: checklist

EXAMPLE 2 - Type: procedure
Document: "1. Preparation ■ Inform patient\n2. Execution ■ Turn on device"
Answer: procedure

EXAMPLE 3 - Type: other
Document: "BLZK Newsletter 02/2024 - Important GOZ info..."
Answer: other

NOW YOU:
Document: {text}
Answer:"""

# Simple ohne Few-Shot (Baseline)
PROMPT_DE_SIMPLE = """Klassifiziere den Dokumenttyp. Antworte NUR mit: checkliste, arbeitsanweisung, oder sonstige.

Dokument: {text}

Typ:"""

PROMPT_EN_SIMPLE = """Classify document type. Answer ONLY with: checklist, procedure, or other.

Document: {text}

Type:"""

# ==================== FUNCTIONS ====================

def load_llm() -> Llama:
    """Load Mistral 7B model"""
    logger.info(f"Loading Mistral 7B: {MODEL_PATH.name}...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    logger.info("✓ Model loaded")
    return llm


def classify_with_prompt(llm: Llama, text: str, prompt_template: str) -> str:
    """Classify text with given prompt template"""
    prompt = prompt_template.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=30,
        temperature=0.1,
        stop=["\n", "Dokument", "BEISPIEL", "Document", "EXAMPLE"]
    )
    return response["choices"][0]["text"].strip().lower()


def normalize_classification(raw: str) -> str:
    """Normalize LLM response to expected category"""
    raw = raw.lower().strip()
    
    # Map German -> English (for comparison)
    if "checkliste" in raw or "checklist" in raw:
        return "checkliste"
    elif "arbeitsanweisung" in raw or "procedure" in raw or "anweisung" in raw:
        return "arbeitsanweisung"
    elif "sonstige" in raw or "other" in raw or "sonstiges" in raw:
        return "sonstige"
    else:
        return raw  # Return as-is if unclear


def test_synthetic_samples(llm: Llama) -> Dict:
    """Test on synthetic German QM samples"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Synthetische deutsche QM-Samples")
    logger.info("="*80)
    
    prompts = {
        "DE_FewShot": PROMPT_DE_FEWSHOT,
        "EN_FewShot": PROMPT_EN_FEWSHOT,
        "DE_Simple": PROMPT_DE_SIMPLE,
        "EN_Simple": PROMPT_EN_SIMPLE,
    }
    
    results = []
    accuracy_by_prompt = {name: {"correct": 0, "total": 0} for name in prompts.keys()}
    
    for sample in SYNTHETIC_SAMPLES:
        sample_result = {
            "description": sample["description"],
            "text_preview": sample["text"][:100],
            "expected": sample["expected"],
            "responses": {}
        }
        
        logger.info(f"\n{sample['description']}:")
        logger.info(f"  Expected: {sample['expected']}")
        
        for prompt_name, prompt_template in prompts.items():
            raw = classify_with_prompt(llm, sample["text"], prompt_template)
            normalized = normalize_classification(raw)
            
            is_correct = normalized == sample["expected"]
            accuracy_by_prompt[prompt_name]["total"] += 1
            if is_correct:
                accuracy_by_prompt[prompt_name]["correct"] += 1
            
            status = "✓" if is_correct else "✗"
            logger.info(f"  {prompt_name:15} → '{raw}' (normalized: {normalized}) {status}")
            
            sample_result["responses"][prompt_name] = {
                "raw": raw,
                "normalized": normalized,
                "correct": is_correct
            }
        
        results.append(sample_result)
    
    # Calculate accuracy
    accuracy_summary = {}
    for prompt_name, stats in accuracy_by_prompt.items():
        acc = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        accuracy_summary[prompt_name] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": round(acc, 1)
        }
        logger.info(f"\n{prompt_name}: {acc:.1f}% ({stats['correct']}/{stats['total']})")
    
    return {
        "test_name": "synthetic_samples",
        "samples": results,
        "accuracy": accuracy_summary
    }


def test_fachbegriffe(llm: Llama) -> Dict:
    """Test understanding of German QM technical terms"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Deutsche QM-Fachbegriffe")
    logger.info("="*80)
    
    # Prompt: Erkläre Fachbegriff in einem Satz
    prompt_template = """Erkläre den Begriff in einem Satz (max 20 Wörter):

Begriff: {term}

Erklärung:"""
    
    results = []
    
    for term in FACHBEGRIFFE_TEST:
        prompt = prompt_template.format(term=term)
        response = llm.create_completion(
            prompt=prompt,
            max_tokens=50,
            temperature=0.3,
            stop=["\n\n", "Begriff:"]
        )
        
        explanation = response["choices"][0]["text"].strip()
        
        # Simple check: Does explanation contain key concepts?
        is_relevant = any(keyword in explanation.lower() for keyword in [
            "praxis", "patient", "zahnarzt", "hygiene", "qualität", 
            "dokumentation", "recht", "gesetz", "schutz", "medizin", "dental"
        ])
        
        logger.info(f"\n{term}:")
        logger.info(f"  → {explanation}")
        logger.info(f"  Relevant: {'✓' if is_relevant else '✗'}")
        
        results.append({
            "term": term,
            "explanation": explanation,
            "is_relevant": is_relevant
        })
    
    relevance_rate = (sum(1 for r in results if r["is_relevant"]) / len(results)) * 100
    logger.info(f"\nRelevanz-Rate: {relevance_rate:.1f}%")
    
    return {
        "test_name": "fachbegriffe",
        "terms": results,
        "relevance_rate": round(relevance_rate, 1)
    }


def test_real_pdfs(llm: Llama, max_files: int = 5) -> Dict:
    """Test on real QM PDFs from BLZK"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Real-World PDFs (BLZK)")
    logger.info("="*80)
    
    if not PDF_FOLDER.exists():
        logger.warning(f"PDF folder not found: {PDF_FOLDER}")
        return {"test_name": "real_pdfs", "skipped": True, "reason": "folder_not_found"}
    
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))[:max_files]
    
    if not pdf_files:
        logger.warning("No PDF files found")
        return {"test_name": "real_pdfs", "skipped": True, "reason": "no_files"}
    
    logger.info(f"Testing {len(pdf_files)} PDFs...")
    
    results = []
    
    for pdf_path in pdf_files:
        # Extract text
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            text = text[:2000]  # Limit
        except Exception as e:
            logger.warning(f"Skipping {pdf_path.name}: {e}")
            continue
        
        # Classify with DE FewShot (best performer expected)
        raw = classify_with_prompt(llm, text, PROMPT_DE_FEWSHOT)
        normalized = normalize_classification(raw)
        
        # Analyze features
        has_checkboxes = "□" in text or "☐" in text
        has_steps = any(f"{i}." in text for i in range(1, 10))
        
        logger.info(f"\n{pdf_path.name}:")
        logger.info(f"  Classified: {normalized}")
        logger.info(f"  Features: checkboxes={has_checkboxes}, steps={has_steps}")
        
        results.append({
            "file": pdf_path.name,
            "classified_as": normalized,
            "text_preview": text[:200],
            "features": {
                "has_checkboxes": has_checkboxes,
                "has_steps": has_steps
            }
        })
    
    return {
        "test_name": "real_pdfs",
        "files_tested": len(results),
        "results": results
    }


def generate_report(synthetic_results: Dict, fachbegriffe_results: Dict, pdf_results: Dict):
    """Generate final test report"""
    logger.info("\n" + "="*80)
    logger.info("FINAL REPORT")
    logger.info("="*80)
    
    report = {
        "test_date": "2026-03-28",
        "model": "Mistral 7B Instruct v0.2 (Q4_K_M)",
        "objective": "Prüfe ob Mistral 7B gut genug für deutsche QM-Dokumente ist",
        "tests": {
            "synthetic_samples": synthetic_results,
            "fachbegriffe": fachbegriffe_results,
            "real_pdfs": pdf_results
        }
    }
    
    # Success Criteria Check
    best_accuracy = max(
        synthetic_results["accuracy"].values(),
        key=lambda x: x["accuracy"]
    )["accuracy"]
    
    success_criteria = {
        "accuracy_over_85": best_accuracy >= 85.0,
        "german_better_than_english": (
            synthetic_results["accuracy"]["DE_FewShot"]["accuracy"] >
            synthetic_results["accuracy"]["EN_FewShot"]["accuracy"]
        ),
        "fachbegriffe_understood": fachbegriffe_results["relevance_rate"] >= 70.0
    }
    
    report["success_criteria"] = success_criteria
    report["passed"] = all(success_criteria.values())
    
    # Recommendation
    if report["passed"]:
        recommendation = "✅ Mistral 7B reicht für deutsche QM-Dokumente! Kein multilingual Fine-Tuning nötig."
    else:
        recommendation = "⚠️ Mistral 7B Performance unter Erwartung. Empfehle multilingual Fine-Tuning oder alternatives Modell."
    
    report["recommendation"] = recommendation
    
    logger.info(f"\n{'='*80}")
    logger.info("SUCCESS CRITERIA:")
    logger.info(f"  Accuracy >85%: {success_criteria['accuracy_over_85']} ({best_accuracy:.1f}%)")
    logger.info(f"  Deutsch > Englisch: {success_criteria['german_better_than_english']}")
    logger.info(f"  Fachbegriffe verstanden: {success_criteria['fachbegriffe_understood']} ({fachbegriffe_results['relevance_rate']:.1f}%)")
    logger.info(f"\n{'='*80}")
    logger.info(recommendation)
    logger.info(f"{'='*80}\n")
    
    # Save report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Report saved: {REPORT_FILE}")
    
    return report


def main():
    """Main test execution"""
    logger.info("="*80)
    logger.info("MISTRAL 7B GERMAN QM PERFORMANCE TEST")
    logger.info("="*80)
    
    # Load model
    llm = load_llm()
    
    # Run tests
    synthetic_results = test_synthetic_samples(llm)
    fachbegriffe_results = test_fachbegriffe(llm)
    pdf_results = test_real_pdfs(llm, max_files=5)
    
    # Generate report
    report = generate_report(synthetic_results, fachbegriffe_results, pdf_results)
    
    return report


if __name__ == "__main__":
    main()
