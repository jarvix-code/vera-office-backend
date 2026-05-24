"""Reset Boris Password"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from backend.db.database import SessionLocal
from backend.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

# Find boris
boris = db.query(User).filter(User.username == "boris").first()

if boris:
    # Reset password to "boris"
    boris.hashed_password = pwd_context.hash("boris")
    db.commit()
    print(f"Password reset for user: boris")
    print(f"New password: boris")
else:
    # Create boris
    new_user = User(
        username="boris",
        email="boris@vera-office.local",
        hashed_password=pwd_context.hash("boris"),
        is_admin=True,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    print(f"Created user: boris")
    print(f"Password: boris")

db.close()
