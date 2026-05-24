import sqlite3
import bcrypt

# Generate bcrypt hash for password "boris"
password = b'boris'
bcrypt_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode()

print(f"Generated hash: {bcrypt_hash}")

# Connect to database
conn = sqlite3.connect('data/vera.db')
cursor = conn.cursor()

# Update password
cursor.execute("UPDATE users SET password_hash=? WHERE username='boris'", (bcrypt_hash,))
conn.commit()

# Verify
cursor.execute("SELECT username, password_hash FROM users WHERE username='boris'")
result = cursor.fetchone()
print(f"\nUsername: {result[0]}")
print(f"Password Hash: {result[1]}")

conn.close()
print("\n✅ Password updated successfully!")
