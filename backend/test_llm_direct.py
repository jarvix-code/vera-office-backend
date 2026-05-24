#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LLM directly - check if model responds at all
"""

from pathlib import Path
from llama_cpp import Llama

MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")

def test_simple_prompts():
    print("=" * 80)
    print("LLM DIRECT TEST")
    print("=" * 80)
    
    # Load LLM
    print(f"\nLoading: {MODEL_PATH.name}...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    print("OK loaded\n")
    
    tests = [
        {
            "name": "Simple Math",
            "prompt": "What is 2+2? Answer with just the number:",
            "max_tokens": 10
        },
        {
            "name": "Simple Classification",
            "prompt": "Classify this as 'positive' or 'negative': I love this! Answer:",
            "max_tokens": 10
        },
        {
            "name": "Document Type (Simple)",
            "prompt": """Classify this document type. Answer ONLY with: checklist, procedure, or other.

Document: This is a step-by-step guide for cleaning.

Type:""",
            "max_tokens": 10
        },
        {
            "name": "Document Type (German)",
            "prompt": """Klassifiziere den Typ. Antworte NUR mit: checkliste, arbeitsanweisung, oder sonstige.

Dokument: Dies ist eine Anleitung mit Schritten.

Typ:""",
            "max_tokens": 20
        }
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*80}")
        print(f"Prompt:\n{test['prompt']}")
        print(f"\n{'-'*80}")
        
        response = llm.create_completion(
            prompt=test["prompt"],
            max_tokens=test["max_tokens"],
            temperature=0.1,
            stop=["\n"]
        )
        
        raw_text = response["choices"][0]["text"]
        print(f"Raw Response: '{raw_text}'")
        print(f"Stripped: '{raw_text.strip()}'")
        print(f"Length: {len(raw_text)} chars")
        
        if not raw_text.strip():
            print("⚠️  EMPTY RESPONSE!")
        else:
            print("✅ Got response")

if __name__ == "__main__":
    test_simple_prompts()
