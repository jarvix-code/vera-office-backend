"""Check VERA Brain DB"""
import sqlite3

conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera_brain.db')
cur = conn.cursor()

cur.execute("SELECT title, ocr_preview FROM document_index LIMIT 5")

for row in cur.fetchall():
    print(f"Title: {row[0][:50]}")
    print(f"Preview: {row[1][:80]}...")
    print()

conn.close()
