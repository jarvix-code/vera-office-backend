"""
VERA Office - Promo Code API
POST /api/promo/redeem    -> Promo-Code einloesen
POST /api/promo/validate  -> Code pruefen ohne einloesen
GET  /api/promo/status    -> Status aller Codes (Admin)
"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/promo", tags=["Promo"])

PROMO_DB = Path(__file__).parent.parent.parent / "data" / "promo_codes.json"


def _load() -> dict:
    if not PROMO_DB.exists():
        return {}
    with open(PROMO_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    PROMO_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMO_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class RedeemRequest(BaseModel):
    code: str


class RedeemResponse(BaseModel):
    success: bool
    message: str
    modules: list[str] = []
    remaining_uses: int = 0


@router.post("/redeem", response_model=RedeemResponse)
async def redeem_promo(req: RedeemRequest):
    """Loest einen Promo-Code ein. Gibt freigeschaltete Module zurueck."""
    code = req.code.strip().upper()
    codes = _load()
    if code not in codes:
        logger.warning(f"Promo-Code ungueltig: {code}")
        raise HTTPException(status_code=404, detail="Ungueltiger Promo-Code")
    entry = codes[code]
    if not entry.get("active", True):
        raise HTTPException(status_code=410, detail="Dieser Promo-Code ist deaktiviert")
    used = entry.get("used", 0)
    max_uses = entry.get("max_uses", 1)
    if used >= max_uses:
        raise HTTPException(status_code=410, detail="Promo-Code bereits vollstaendig eingeloest")
    entry["used"] = used + 1
    _save(codes)
    modules = entry.get("modules", [])
    remaining = max_uses - entry["used"]
    logger.success(f"Promo-Code eingeloest: {code} -> Module: {modules} (noch {remaining} Uses)")

    # BUGFIX F42: Module in users.modules_unlocked persistieren
    try:
        import json as _json
        from backend.db.database import SessionLocal
        from backend.models.user import User as UserModel
        _db = SessionLocal()
        try:
            _user = (_db.query(UserModel).filter(UserModel.pin_hash.isnot(None)).first()
                     or _db.query(UserModel).filter(UserModel.is_admin.is_(True)).first())
            if _user:
                existing = _json.loads(_user.modules_unlocked or "[]")
                for m in modules:
                    if m not in existing:
                        existing.append(m)
                _user.modules_unlocked = _json.dumps(existing)
                _db.commit()
                logger.info(f"Module in DB persistiert: {existing}")
        finally:
            _db.close()
    except Exception as _e:
        logger.warning(f"Fehler beim Persistieren der Module: {_e}")

    return RedeemResponse(
        success=True,
        message=f"Code eingeloest! Freigeschaltete Module: {', '.join(modules).upper()}",
        modules=modules,
        remaining_uses=remaining,
    )


class ValidateResponse(BaseModel):
    valid: bool
    message: str
    modules: list[str] = []
    remaining_uses: int = 0


@router.post("/validate", response_model=ValidateResponse)
async def validate_promo(req: RedeemRequest):
    """Prueft einen Promo-Code auf Gueltigkeit ohne ihn einzuloesen."""
    code = req.code.strip().upper()
    codes = _load()
    if code not in codes:
        return ValidateResponse(valid=False, message="Ungueltiger Promo-Code")
    entry = codes[code]
    if not entry.get("active", True):
        return ValidateResponse(valid=False, message="Dieser Promo-Code ist deaktiviert")
    used = entry.get("used", 0)
    max_uses = entry.get("max_uses", 1)
    if used >= max_uses:
        return ValidateResponse(valid=False, message="Promo-Code bereits vollstaendig eingeloest")
    modules = entry.get("modules", [])
    remaining = max_uses - used
    return ValidateResponse(
        valid=True,
        message=f"Code gueltig - Module: {', '.join(modules).upper()}",
        modules=modules,
        remaining_uses=remaining,
    )


@router.get("/status")
async def promo_status():
    """Gibt Status aller Promo-Codes zurueck (fuer Admin-Uebersicht)."""
    codes = _load()
    result = []
    for code, entry in codes.items():
        result.append({
            "code": code,
            "modules": entry.get("modules", []),
            "description": entry.get("description", ""),
            "used": entry.get("used", 0),
            "max_uses": entry.get("max_uses", 0),
            "remaining": entry.get("max_uses", 0) - entry.get("used", 0),
            "active": entry.get("active", True),
        })
    return result
