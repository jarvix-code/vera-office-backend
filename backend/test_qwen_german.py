#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BONUS TEST: Qwen 2.5 1.5B German QM Performance
Vergleich zu Mistral 7B - ist Qwen besser für Deutsch?
"""

import json
import logging
from pathlib import Path
from llama_cpp import Llama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================

QWEN_MODEL_PATH = Path("C:/Jarvix/vera-office/models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
MISTRAL_REPORT = Path("C:/Jarvix/vera-office/backend/mistral_german_test_report.json")
QWEN_REPORT = Path("C:/Jarvix/vera-office/backend/qwen_german_test_report.json")

# ==================== TEST SAMPLES (gleich wie Mistral) ====================

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

# Deutsche Few-Shot Prompt (best performer bei Mistral)
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

# ==================== FUNCTIONS ====================

def load_qwen() -> Llama:
    """Load Qwen 2.5 1.5B model"""
    logger.info(f"Loading Qwen 2.5: {QWEN_MODEL_PATH.name}...")
    llm = Llama(
        model_path=str(QWEN_MODEL_PATH),
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    logger.info("✓ Model loaded")
    return llm


def classify_with_qwen(llm: Llama, text: str) -> str:
    """Classify text with Qwen"""
    prompt = PROMPT_DE_FEWSHOT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=30,
        temperature=0.1,
        stop=["\n", "Dokument", "BEISPIEL"]
    )
    return response["choices"][0]["text"].strip().lower()


def normalize_classification(raw: str) -> str:
    """Normalize LLM response to expected category"""
    raw = raw.lower().strip()
    
    if "checkliste" in raw or "checklist" in raw:
        return "checkliste"
    elif "arbeitsanweisung" in raw or "procedure" in raw or "anweisung" in raw:
        return "arbeitsanweisung"
    elif "sonstige" in raw or "other" in raw or "sonstiges" in raw:
        return "sonstige"
    else:
        return raw


def test_qwen_samples(llm: Llama):
    """Test Qwen on synthetic samples"""
    logger.info("\n" + "="*80)
    logger.info("QWEN 2.5 TEST: Synthetische deutsche QM-Samples")
    logger.info("="*80)
    
    results = []
    correct = 0
    total = len(SYNTHETIC_SAMPLES)
    
    for sample in SYNTHETIC_SAMPLES:
        raw = classify_with_qwen(llm, sample["text"])
        normalized = normalize_classification(raw)
        is_correct = normalized == sample["expected"]
        
        if is_correct:
            correct += 1
        
        status = "✓" if is_correct else "✗"
        logger.info(f"\n{sample['description']}:")
        logger.info(f"  Expected: {sample['expected']}")
        logger.info(f"  Qwen → '{raw}' (normalized: {normalized}) {status}")
        
        results.append({
            "description": sample["description"],
            "text_preview": sample["text"][:100],
            "expected": sample["expected"],
            "raw": raw,
            "normalized": normalized,
            "correct": is_correct
        })
    
    accuracy = (correct / total) * 100
    logger.info(f"\nQwen 2.5 Accuracy: {accuracy:.1f}% ({correct}/{total})")
    
    return {
        "test_name": "qwen_samples",
        "samples": results,
        "accuracy": {
            "correct": correct,
            "total": total,
            "accuracy": round(accuracy, 1)
        }
    }


def test_qwen_fachbegriffe(llm: Llama):
    """Test Qwen on German QM terms"""
    logger.info("\n" + "="*80)
    logger.info("QWEN 2.5 TEST: Deutsche QM-Fachbegriffe")
    logger.info("="*80)
    
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
        "test_name": "qwen_fachbegriffe",
        "terms": results,
        "relevance_rate": round(relevance_rate, 1)
    }


def compare_with_mistral():
    """Load Mistral report and compare"""
    logger.info("\n" + "="*80)
    logger.info("VERGLEICH: Qwen 2.5 vs Mistral 7B")
    logger.info("="*80)
    
    if not MISTRAL_REPORT.exists():
        logger.warning(f"Mistral report not found: {MISTRAL_REPORT}")
        return None
    
    with open(MISTRAL_REPORT, "r", encoding="utf-8") as f:
        mistral = json.load(f)
    
    # Compare accuracies
    mistral_acc = mistral["tests"]["synthetic_samples"]["accuracy"]["DE_FewShot"]["accuracy"]
    
    logger.info(f"\nClassification Accuracy (German Few-Shot):")
    logger.info(f"  Mistral 7B:  {mistral_acc:.1f}%")
    
    # Compare Fachbegriffe
    mistral_fach = mistral["tests"]["fachbegriffe"]["relevance_rate"]
    
    logger.info(f"\nFachbegriffe Relevance:")
    logger.info(f"  Mistral 7B:  {mistral_fach:.1f}%")
    
    return {
        "mistral_accuracy": mistral_acc,
        "mistral_fachbegriffe": mistral_fach
    }


def generate_report(qwen_samples, qwen_fachbegriffe, mistral_comparison):
    """Generate comparison report"""
    logger.info("\n" + "="*80)
    logger.info("FINAL REPORT: Qwen 2.5 vs Mistral 7B")
    logger.info("="*80)
    
    report = {
        "test_date": "2026-03-28",
        "model": "Qwen 2.5 1.5B Instruct (Q4_K_M)",
        "objective": "Vergleich zu Mistral 7B für deutsche QM-Dokumente",
        "tests": {
            "samples": qwen_samples,
            "fachbegriffe": qwen_fachbegriffe
        }
    }
    
    if mistral_comparison:
        qwen_acc = qwen_samples["accuracy"]["accuracy"]
        mistral_acc = mistral_comparison["mistral_accuracy"]
        
        qwen_fach = qwen_fachbegriffe["relevance_rate"]
        mistral_fach = mistral_comparison["mistral_fachbegriffe"]
        
        report["comparison"] = {
            "classification_accuracy": {
                "qwen": qwen_acc,
                "mistral": mistral_acc,
                "winner": "Qwen" if qwen_acc > mistral_acc else "Mistral",
                "delta": round(qwen_acc - mistral_acc, 1)
            },
            "fachbegriffe_relevance": {
                "qwen": qwen_fach,
                "mistral": mistral_fach,
                "winner": "Qwen" if qwen_fach > mistral_fach else "Mistral",
                "delta": round(qwen_fach - mistral_fach, 1)
            }
        }
        
        # Recommendation
        if qwen_acc >= mistral_acc and qwen_fach >= mistral_fach:
            recommendation = "✅ Qwen 2.5 ist BESSER oder GLEICHWERTIG zu Mistral 7B - und 5x schneller! EMPFEHLUNG: Qwen nutzen."
        elif qwen_acc >= 85.0:
            recommendation = "✅ Qwen 2.5 ist gut genug (>85% Accuracy). EMPFEHLUNG: Qwen nutzen (kleiner, schneller)."
        else:
            recommendation = "⚠️ Qwen 2.5 erreicht nicht 85% Accuracy. EMPFEHLUNG: Mistral 7B oder Fine-Tuning."
        
        report["recommendation"] = recommendation
        
        logger.info(f"\n{'='*80}")
        logger.info("COMPARISON RESULTS:")
        logger.info(f"  Classification Accuracy:")
        logger.info(f"    Qwen 2.5:    {qwen_acc:.1f}%")
        logger.info(f"    Mistral 7B:  {mistral_acc:.1f}%")
        logger.info(f"    Winner:      {report['comparison']['classification_accuracy']['winner']} ({report['comparison']['classification_accuracy']['delta']:+.1f}%)")
        logger.info(f"\n  Fachbegriffe Relevance:")
        logger.info(f"    Qwen 2.5:    {qwen_fach:.1f}%")
        logger.info(f"    Mistral 7B:  {mistral_fach:.1f}%")
        logger.info(f"    Winner:      {report['comparison']['fachbegriffe_relevance']['winner']} ({report['comparison']['fachbegriffe_relevance']['delta']:+.1f}%)")
        logger.info(f"\n{'='*80}")
        logger.info(recommendation)
        logger.info(f"{'='*80}\n")
    
    # Save report
    with open(QWEN_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Report saved: {QWEN_REPORT}")
    
    return report


def main():
    """Main test execution"""
    logger.info("="*80)
    logger.info("QWEN 2.5 GERMAN QM PERFORMANCE TEST")
    logger.info("="*80)
    
    # Load model
    llm = load_qwen()
    
    # Run tests
    qwen_samples = test_qwen_samples(llm)
    qwen_fachbegriffe = test_qwen_fachbegriffe(llm)
    
    # Compare with Mistral
    mistral_comparison = compare_with_mistral()
    
    # Generate report
    report = generate_report(qwen_samples, qwen_fachbegriffe, mistral_comparison)
    
    return report


if __name__ == "__main__":
    main()
