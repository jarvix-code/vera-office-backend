import sqlite3
conn = sqlite3.connect('C:/Jarvix/vera-office/data/feedback.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
print('Tables:', [t[0] for t in cursor.fetchall()])
cursor.execute('SELECT COUNT(*) FROM feedback')
print('Total entries:', cursor.fetchone()[0])
cursor.execute('SELECT type, message, created_at FROM feedback ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'{row[2]}: [{row[0]}] {row[1][:100]}')
