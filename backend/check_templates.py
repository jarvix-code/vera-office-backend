import sqlite3
conn = sqlite3.connect('C:/Jarvix/QM/data/qmki.db')

# Get schema
schema = conn.execute('PRAGMA table_info(document_templates)').fetchall()
print("Schema:")
for col in schema:
    print(f"  {col[1]} ({col[2]})")

print("\n" + "=" * 80)

# Sample rows
rows = conn.execute('SELECT * FROM document_templates LIMIT 5').fetchall()
for row in rows:
    print(row)

print("\n" + "=" * 80)

# Check for doc_type or category
columns = [col[1] for col in schema]
if 'doc_type' in columns:
    types = conn.execute('SELECT doc_type, COUNT(*) FROM document_templates GROUP BY doc_type').fetchall()
    print("\nDoc Types:")
    for t, c in types:
        print(f"  {t}: {c}")
elif 'category' in columns:
    cats = conn.execute('SELECT category, COUNT(*) FROM document_templates GROUP BY category').fetchall()
    print("\nCategories:")
    for cat, c in cats:
        print(f"  {cat}: {c}")
