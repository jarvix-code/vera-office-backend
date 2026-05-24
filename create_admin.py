"""Create Admin User for VERA Office"""
import sys
sys.path.insert(0, r"C:\Jarvix\vera-office")

from backend.db.database import SessionLocal
from backend.models.user import User
from backend.api.auth import hash_password

# Admin Credentials
USERNAME = "boris"
PASSWORD = "vera2024!"

db = SessionLocal()

# Check if user exists
existing = db.query(User).filter(User.username == USERNAME).first()
if existing:
    print(f"✅ User '{USERNAME}' existiert bereits")
    # Update password
    existing.password_hash = hash_password(PASSWORD)
    db.commit()
    print(f"✅ Passwort für '{USERNAME}' wurde aktualisiert")
else:
    # Create new admin
    admin = User(
        username=USERNAME,
        password_hash=hash_password(PASSWORD),
        full_name="Boris Reimers",
        is_active=True,
        is_admin=True
    )
    db.add(admin)
    db.commit()
    print(f"✅ Admin '{USERNAME}' erstellt")

db.close()

print(f"\n📋 Login:")
print(f"   Username: {USERNAME}")
print(f"   Password: {PASSWORD}")
print(f"   URL: http://192.168.178.44:8001")
