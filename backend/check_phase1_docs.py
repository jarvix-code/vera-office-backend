#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Phase 1 documents (qmki.db)
"""

import sqlite3

qmki_db = "C:/Jarvix/QM/data/qmki.db"

conn = sqlite3.connect(qmki_db)

print("=" * 80)
print("PHASE 1 DOCUMENTS (qmki.db)")
print("=" * 80)

# Count by type
counts = conn.execute("""
    SELECT doc_type, COUNT(*) 
    FROM documents 
    GROUP BY doc_type
""").fetchall()

print("\nDocument Types:")
for doc_type, count in counts:
    print(f"  {doc_type}: {count}")

# Show checklisten
print("\n" + "=" * 80)
print("CHECKLISTEN:")
print("=" * 80)
checklists = conn.execute("""
    SELECT id, title, file_path 
    FROM documents 
    WHERE doc_type = 'checkliste'
    LIMIT 10
""").fetchall()

for doc_id, title, file_path in checklists:
    print(f"{doc_id:3}: {title[:60]}")
    if file_path:
        print(f"      File: {file_path}")

# Show arbeitsanweisungen
print("\n" + "=" * 80)
print("ARBEITSANWEISUNGEN:")
print("=" * 80)
procedures = conn.execute("""
    SELECT id, title, file_path 
    FROM documents 
    WHERE doc_type = 'arbeitsanweisung'
    LIMIT 10
""").fetchall()

for doc_id, title, file_path in procedures:
    print(f"{doc_id:3}: {title[:60]}")
    if file_path:
        print(f"      File: {file_path}")

conn.close()
