"""Reset Boris Password - Simple"""
import sqlite3
import hashlib

# Simple hash (NOT bcrypt, aber funktioniert)
password = "boris"
hashed = hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db')
cur = conn.cursor()

# Update boris password
cur.execute("UPDATE users SET hashed_password=? WHERE username='boris'", (hashed,))
conn.commit()

print("Password reset: boris / boris")

conn.close()
