"""Test LLM classification with real model."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Jarvix\vera-office")

import time

# Test LLM classification
from backend.core.ai.classifier import classifier

test_text = """
Rechnung Nr. 2026-0042
Datum: 15.02.2026

An: Dr. med. Schmidt Zahnarztpraxis
    Hauptstr. 12
    80331 München

Von: Dental-Depot Müller GmbH
     Industriestr. 45
     90402 Nürnberg

Pos.  Beschreibung               Menge   Einzelpreis   Gesamt
1     Komposit-Füllungsmaterial   5 Pkg   45,00 EUR     225,00 EUR
2     Einmalhandschuhe Nitril     10 Box  12,50 EUR     125,00 EUR
3     Absaugkanülen               100 St   0,85 EUR      85,00 EUR

                                         Netto:        435,00 EUR
                                         MwSt 19%:      82,65 EUR
                                         Brutto:       517,65 EUR

Zahlungsziel: 30 Tage netto
IBAN: DE89 3704 0044 0532 0130 00
"""

print("Testing LLM classification...")
start = time.time()
result = classifier.classify(test_text)
elapsed = time.time() - start

print(f"\nResult:")
print(f"  Category: {result['category']}")
print(f"  Confidence: {result['confidence']:.0%}")
print(f"  Reasoning: {result['reasoning']}")
print(f"  Available: {result['available']}")
print(f"  Time: {elapsed:.1f}s")

# Test namer
print("\nTesting Document Namer...")
from backend.core.ai.namer import namer
start = time.time()
filename = namer.generate_filename(test_text, result['category'], "scan_001.pdf")
elapsed = time.time() - start
print(f"  Filename: {filename}")
print(f"  Time: {elapsed:.1f}s")

print("\nDone!")
