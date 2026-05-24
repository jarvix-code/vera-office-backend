import sqlite3

conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db')
cur = conn.cursor()

cur.execute('SELECT id, title, file_path, SUBSTR(content, 1, 100) FROM qm_documents LIMIT 5')

for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]}")
    print(f"  file_path: {row[2]}")
    print(f"  content: {row[3][:80] if row[3] else 'None'}...")
    print()

conn.close()
