import sqlite3
conn = sqlite3.connect('C:/Jarvix/QM/data/qmki.db')
tables = conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
print('Tables:', [t[0] for t in tables])

for table in [t[0] for t in tables]:
    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'  {table}: {count} rows')
