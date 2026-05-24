#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMPROVED CLASSIFIER PROMPTS
Test different prompt strategies
"""

# ==================== PROMPT VARIANTS ====================

# ORIGINAL (BROKEN)
PROMPT_ORIGINAL = """Klassifiziere dieses Dokument:

Typen:
- checkliste: Hat Ja/Nein-Fragen, Verantwortliche, Erledigungs-Status
- arbeitsanweisung: Hat nummerierte Schritte, Bullet-Points, Prozess-Beschreibung
- sonstige: Alles andere

Text:
{text}

Antworte NUR mit dem Typ (ohne Erklärung):"""

# VARIANT 1: Simple + Clear
PROMPT_V1_SIMPLE = """Klassifiziere den Dokumenttyp. Antworte NUR mit: checkliste, arbeitsanweisung, oder sonstige.

Dokument: {text}

Typ:"""

# VARIANT 2: Few-Shot Examples
PROMPT_V2_FEWSHOT = """Du bist ein QM-Dokument-Classifier für Zahnarztpraxen.

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

# VARIANT 3: Structured with keywords
PROMPT_V3_KEYWORDS = """Klassifiziere QM-Dokument als: checkliste, arbeitsanweisung, oder sonstige.

Kriterien:
- checkliste: Checkboxen (□ ☐), Ja/Nein-Fragen, Verantwortliche
- arbeitsanweisung: Nummerierte Schritte (1. 2. 3.), Bullet-Points (■ •), Prozess-Ablauf
- sonstige: Newsletter, Infos, Gesetze, keine Handlungsanleitung

Dokument:
{text}

Klassifikation:"""

# VARIANT 4: Mistral Instruct Format (proper)
PROMPT_V4_INSTRUCT = """<s>[INST] Klassifiziere dieses Dokument als checkliste, arbeitsanweisung, oder sonstige.

Dokument: {text}

Antworte NUR mit dem Typ: [/INST]"""

# ==================== TEST FUNCTION ====================

def test_prompts_on_samples():
    """Test all prompt variants on sample texts"""
    from pathlib import Path
    import fitz
    from llama_cpp import Llama
    import json
    
    MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
    PDF_FOLDER = Path("C:/Jarvix/QM/data/blzk_downloads")
    
    SAMPLES = [
        "dokument_103.pdf",  # Should be: arbeitsanweisung
        "Ablaufdiagramm für die Zahnarztpraxis.pdf",  # Should be: arbeitsanweisung
        "09102023GOZ ON TOUR-Materialien  Protesttag  F.pdf",  # Should be: sonstige
    ]
    
    PROMPTS = {
        "ORIGINAL": PROMPT_ORIGINAL,
        "V1_SIMPLE": PROMPT_V1_SIMPLE,
        "V2_FEWSHOT": PROMPT_V2_FEWSHOT,
        "V3_KEYWORDS": PROMPT_V3_KEYWORDS,
        "V4_INSTRUCT": PROMPT_V4_INSTRUCT,
    }
    
    print("=" * 80)
    print("PROMPT COMPARISON TEST")
    print("=" * 80)
    
    # Load LLM
    print(f"\nLoading LLM...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    print("OK\n")
    
    results = []
    
    for sample in SAMPLES:
        pdf_path = PDF_FOLDER / sample
        if not pdf_path.exists():
            continue
        
        # Extract text
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        text = text[:1500]  # Limit
        
        print(f"\n{'='*80}")
        print(f"SAMPLE: {sample}")
        print(f"{'='*80}")
        
        sample_results = {"file": sample, "text_preview": text[:200], "responses": {}}
        
        for prompt_name, prompt_template in PROMPTS.items():
            prompt = prompt_template.format(text=text)
            
            response = llm.create_completion(
                prompt=prompt,
                max_tokens=30,
                temperature=0.1,
                stop=["\n", "Dokument", "BEISPIEL"]
            )
            
            raw = response["choices"][0]["text"].strip()
            
            print(f"  {prompt_name:15} → '{raw}'")
            sample_results["responses"][prompt_name] = raw
        
        results.append(sample_results)
    
    # Save report
    report_file = Path("C:/Jarvix/vera-office/backend/prompt_comparison_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"Report: {report_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_prompts_on_samples()
