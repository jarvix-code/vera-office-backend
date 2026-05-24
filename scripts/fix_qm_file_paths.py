"""Extract file_path from content field"""
import sqlite3

conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db')
cur = conn.cursor()

# Get all docs with KIQM-Datei in content
cur.execute("SELECT id, content FROM qm_documents WHERE content LIKE 'KIQM-Datei:%'")

updated = 0

for doc_id, content in cur.fetchall():
    # Extract path from "KIQM-Datei: <path>"
    lines = content.split('\n')
    if lines[0].startswith('KIQM-Datei:'):
        file_path = lines[0].replace('KIQM-Datei: ', '').strip()
        
        # Update file_path
        cur.execute("UPDATE qm_documents SET file_path=? WHERE id=?", (file_path, doc_id))
        updated += 1

conn.commit()
conn.close()

print(f"OK: {updated} file_paths aktualisiert")
