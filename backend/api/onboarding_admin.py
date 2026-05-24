"""
VERA Office Onboarding — Admin-Account Creation
Extends the onboarding process with admin user creation (Step 0).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from loguru import logger

from backend.db.database import get_db
from backend.models.user import User
from backend.api.auth import hash_password, create_access_token

router = APIRouter(prefix="/api/onboarding/admin", tags=["onboarding"])


class CreateAdminRequest(BaseModel):
    username: str
    password: str
    password_confirm: str
    full_name: str | None = None
    email: str | None = None

    @field_validator("username")
    @classmethod
    def username_min_length(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Username muss mindestens 3 Zeichen lang sein")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Passwort muss mindestens 8 Zeichen lang sein")
        return v


@router.post("/create")
async def create_admin_user(
    request: CreateAdminRequest,
    db: Session = Depends(get_db)
):
    """
    Create admin user during onboarding.
    Only works when no users exist yet. Returns JWT token for auto-login.
    """
    # Check: passwords must match
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwoerter stimmen nicht ueberein"
        )

    # Check: no users must exist
    existing_users = db.query(User).count()
    if existing_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin-User wurde bereits erstellt"
        )

    # Hash password and create user
    password_hash = hash_password(request.password)

    admin_user = User(
        username=request.username,
        password_hash=password_hash,
        full_name=request.full_name,
        email=request.email,
        is_active=True,
        is_admin=True
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    logger.success(f"Admin user created: {admin_user.username}")

    # Auto-login: generate JWT token
    from datetime import timedelta
    access_token = create_access_token(
        data={"sub": admin_user.username},
        expires_delta=timedelta(hours=24)
    )

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": admin_user.id,
            "username": admin_user.username,
            "full_name": admin_user.full_name,
            "email": admin_user.email,
            "is_admin": admin_user.is_admin
        }
    }


@router.get("/exists")
async def check_admin_exists(db: Session = Depends(get_db)):
    """Check if any user/admin exists."""
    user_count = db.query(User).count()
    return {"exists": user_count > 0}
