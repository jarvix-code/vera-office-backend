import sqlite3

conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db')
cur = conn.cursor()

cur.execute('SELECT username, is_admin FROM users')

print('VERA Users:')
for row in cur.fetchall():
    print(f'  Username: {row[0]} (Admin: {row[1]})')

conn.close()
