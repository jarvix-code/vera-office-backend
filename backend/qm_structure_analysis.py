#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QM Struktur-Analyse für VERA Office
Analysiert 750 QM-Dokumente aus vera_functions.db
"""

import sqlite3
import json
import os
from collections import defaultdict
import re

DB_PATH = "data/vera_functions.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB nicht gefunden: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Tables: {tables}\n")
    
    # 2. Wenn documents table existiert
    if ('documents',) in tables:
        analyze_documents(cursor)
    else:
        print("⚠️ 'documents' table nicht gefunden - suche alternative tables...")
        analyze_alternative_tables(cursor)
    
    conn.close()

def analyze_documents(cursor):
    """Analysiere documents table"""
    print("=" * 80)
    print("ANALYSE: documents table")
    print("=" * 80)
    
    # Spalten anzeigen
    cursor.execute("PRAGMA table_info(documents)")
    columns = cursor.fetchall()
    print(f"\n📋 Spalten: {[col[1] for col in columns]}\n")
    
    # Total count
    cursor.execute("SELECT COUNT(*) FROM documents")
    total = cursor.fetchone()[0]
    print(f"📄 Gesamt Dokumente: {total}\n")
    
    # 1. Dateinamen-Pattern
    print("-" * 80)
    print("1. DATEINAMEN-PATTERN (Top 30)")
    print("-" * 80)
    cursor.execute("""
        SELECT SUBSTR(filename, 1, 15) as prefix, COUNT(*) as count
        FROM documents
        WHERE filename IS NOT NULL
        GROUP BY prefix
        ORDER BY count DESC
        LIMIT 30
    """)
    prefixes = cursor.fetchall()
    for prefix, count in prefixes:
        print(f"  {prefix:<20} → {count:>3}x")
    
    # 2. Kapitel-Struktur
    print("\n" + "-" * 80)
    print("2. KAPITEL-STRUKTUR")
    print("-" * 80)
    cursor.execute("""
        SELECT 
          CASE
            WHEN filename LIKE '%AS-A%' THEN 'AS-A: Arbeitsschutz A'
            WHEN filename LIKE '%AS-B%' THEN 'AS-B: Arbeitsschutz B'
            WHEN filename LIKE '%AS-C%' THEN 'AS-C: Arbeitsschutz C'
            WHEN filename LIKE '%AS-D%' THEN 'AS-D: Arbeitsschutz D'
            WHEN filename LIKE '%Q-%' THEN 'Q: Qualitätsmanagement'
            WHEN filename LIKE '%6-%' THEN '6: Kapitel 6'
            ELSE 'Sonstige'
          END as kapitel,
          COUNT(*) as anzahl
        FROM documents
        WHERE filename IS NOT NULL
        GROUP BY kapitel
        ORDER BY anzahl DESC
    """)
    kapiteln = cursor.fetchall()
    for kapitel, anzahl in kapiteln:
        print(f"  {kapitel:<30} → {anzahl:>3} Dokumente")
    
    # 3. Dokumenttypen
    print("\n" + "-" * 80)
    print("3. DOKUMENTTYPEN")
    print("-" * 80)
    cursor.execute("""
        SELECT type, COUNT(*) as count
        FROM documents
        WHERE type IS NOT NULL
        GROUP BY type
        ORDER BY count DESC
    """)
    types = cursor.fetchall()
    for doc_type, count in types:
        print(f"  {doc_type:<30} → {count:>3} Dokumente")
    
    # 4. Sample Dokumente (je Typ)
    print("\n" + "-" * 80)
    print("4. SAMPLE DOKUMENTE (je Top 3 Typen)")
    print("-" * 80)
    for doc_type, _ in types[:3]:
        cursor.execute("""
            SELECT id, filename, type
            FROM documents
            WHERE type = ?
            LIMIT 5
        """, (doc_type,))
        samples = cursor.fetchall()
        print(f"\n  📁 {doc_type}:")
        for doc_id, filename, dtype in samples:
            print(f"    • {filename} (ID: {doc_id})")
    
    # 5. Text-Pattern-Analyse (Sample-based)
    print("\n" + "-" * 80)
    print("5. TEXT-PATTERN ANALYSE (Sample-based)")
    print("-" * 80)
    
    # Check ob text_content Spalte existiert
    if any(col[1] == 'text_content' for col in columns):
        analyze_text_patterns(cursor)
    else:
        print("  ⚠️ Keine text_content Spalte gefunden")

def analyze_text_patterns(cursor):
    """Analysiere Text-Pattern in Dokumenten"""
    
    # Hole 20 zufällige Samples mit Text
    cursor.execute("""
        SELECT id, filename, type, text_content
        FROM documents
        WHERE text_content IS NOT NULL AND LENGTH(text_content) > 100
        ORDER BY RANDOM()
        LIMIT 20
    """)
    samples = cursor.fetchall()
    
    patterns = {
        'ja_nein': r'(□|☐|\[ \])\s*(Ja|Nein)',
        'steps': r'^\d+\.\s+(.+)$',
        'bullets': r'^■\s+(.+)$',
        'verantwortlich': r'(Verantwortlich|Zuständig|Bearbeiter)',
        'datum': r'\d{2}\.\d{2}\.\d{4}',
        'paragraph': r'§\s*\d+',
        'checkbox': r'(□|☐|\[x\]|\[ \])',
    }
    
    pattern_counts = defaultdict(int)
    
    for doc_id, filename, doc_type, text in samples:
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                pattern_counts[pattern_name] += 1
    
    print("\n  Pattern-Häufigkeit (aus 20 Samples):")
    for pattern_name, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {pattern_name:<20} → {count:>2}/20 Dokumente")

def analyze_alternative_tables(cursor):
    """Analysiere alternative table structures"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table_name, in tables:
        print(f"\n📊 Table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"   Spalten: {[col[1] for col in columns]}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   Rows: {count}")

if __name__ == "__main__":
    main()
