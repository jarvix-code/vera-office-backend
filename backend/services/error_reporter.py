"""
VERA Office - Error Reporter
Sendet kritische Fehler proaktiv per Telegram an den Betreiber (Boris).
Kein python-telegram-bot nötig – nutzt direkt die Telegram Bot API via httpx.
"""

import traceback
import time
from datetime import datetime
from typing import Optional
from pathlib import Path
import platform

from loguru import logger


# ---------------------------------------------------------------------------
# Rate-Limiter: max 1 Nachricht pro 5 Minuten je Fehlertyp
# ---------------------------------------------------------------------------
_rate_limit: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 300  # 5 Minuten


def _is_rate_limited(error_key: str) -> bool:
    now = time.time()
    last_sent = _rate_limit.get(error_key, 0)
    if now - last_sent < _RATE_LIMIT_SECONDS:
        return True
    _rate_limit[error_key] = now
    return False


# ---------------------------------------------------------------------------
# System-Status (RAM, Disk, CPU)
# ---------------------------------------------------------------------------
def _get_system_stats() -> str:
    try:
        import psutil
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").free / (1024 ** 3)  # GB
        cpu = psutil.cpu_percent(interval=0.1)
        return f"RAM: {ram:.0f}% | Disk: {disk:.1f}GB frei | CPU: {cpu:.0f}%"
    except Exception:
        return "System-Stats nicht verfügbar"


# ---------------------------------------------------------------------------
# Telegram HTTP-Send (httpx, sync + async)
# ---------------------------------------------------------------------------
def _load_telegram_config() -> tuple[str, str]:
    """Lädt bot_token und chat_id aus vera.yaml oder Umgebungsvariablen."""
    import os
    import yaml

    # 1. Umgebungsvariablen haben Vorrang
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if token and chat_id:
        return token, chat_id

    # 2. vera.yaml
    config_path = Path(__file__).parent.parent.parent / "config" / "vera.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            tg = cfg.get("telegram", {})
            if tg.get("enabled", False):
                token = token or tg.get("bot_token", "")
                chat_id = chat_id or str(tg.get("chat_id", ""))
        except Exception as e:
            logger.debug(f"[error_reporter] vera.yaml lesen fehlgeschlagen: {e}")

    return token, chat_id


def _send_telegram_sync(message: str) -> bool:
    """Sendet eine Telegram-Nachricht synchron. Gibt True bei Erfolg zurück."""
    token, chat_id = _load_telegram_config()
    if not token or not chat_id:
        logger.debug("[error_reporter] Kein Telegram-Token/Chat-ID – Nachricht nicht gesendet")
        return False

    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.warning(f"[error_reporter] Telegram API {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"[error_reporter] Telegram-Send fehlgeschlagen (fail-safe): {e}")
        return False


async def _send_telegram_async(message: str) -> bool:
    """Sendet eine Telegram-Nachricht asynchron."""
    token, chat_id = _load_telegram_config()
    if not token or not chat_id:
        logger.debug("[error_reporter] Kein Telegram-Token/Chat-ID – Nachricht nicht gesendet")
        return False

    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.warning(f"[error_reporter] Telegram API {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"[error_reporter] Telegram-Send fehlgeschlagen (fail-safe): {e}")
        return False


# ---------------------------------------------------------------------------
# Nachrichtenformat
# ---------------------------------------------------------------------------
def _build_message(
    error_type: str,
    description: str,
    file_loc: str,
    tb_short: str,
    context: str = "",
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = _get_system_stats()
    host = platform.node() or "unbekannt"

    # Sonderzeichen für HTML escapen
    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    msg = (
        f"[WARNING] <b>VERA Fehler</b> — {ts}\n"
        f"\n\n"
        f"<b>{esc(error_type)}:</b> {esc(description)}\n\n"
        f" <code>{esc(file_loc)}</code>\n"
    )
    if tb_short:
        msg += f"[LIST] <pre>{esc(tb_short)}</pre>\n\n"
    if context:
        msg += f"ℹ {esc(context)}\n\n"
    msg += (
        f"[SAVE] {stats}\n"
        f" Host: {esc(host)}"
    )
    return msg


def _extract_location(tb: traceback.StackSummary | None, exc_tb) -> str:
    """Extrahiert Datei:Zeile aus Traceback."""
    try:
        if exc_tb:
            extracted = traceback.extract_tb(exc_tb)
            if extracted:
                last = extracted[-1]
                return f"{last.filename}:{last.lineno} in {last.name}"
    except Exception:
        pass
    return "unbekannt"


def _short_traceback(exc: Exception) -> str:
    """Gibt gekürzten Stacktrace zurück (max 500 Zeichen)."""
    try:
        full = traceback.format_exc()
        if full.strip() == "NoneType: None":
            full = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        # Letzte relevante Zeilen behalten
        lines = full.strip().splitlines()
        short = "\n".join(lines[-8:])  # Letzte 8 Zeilen
        return short[:500]
    except Exception:
        return str(exc)[:500]


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------
def send(
    exc: Exception,
    context: str = "",
    error_key: Optional[str] = None,
) -> bool:
    """
    Sendet einen Fehler per Telegram (synchron).
    Wird bei unbehandelten Exceptions, Startup-Fehlern und Pipeline-Fehlern aufgerufen.

    Args:
        exc: Die Exception
        context: Optionaler Kontext (z.B. "OCR Pipeline", "Startup")
        error_key: Schlüssel für Rate-Limiting (default: Exception-Typ)
    Returns:
        True wenn gesendet, False sonst
    """
    key = error_key or type(exc).__name__
    if _is_rate_limited(key):
        logger.debug(f"[error_reporter] Rate-limited für '{key}' – Nachricht unterdrückt")
        return False

    error_type = type(exc).__name__
    description = str(exc)[:200]
    location = _extract_location(None, exc.__traceback__)
    tb_short = _short_traceback(exc)

    message = _build_message(error_type, description, location, tb_short, context)
    logger.info(f"[error_reporter] Sende Fehler-Meldung an Telegram: {error_type}")

    return _send_telegram_sync(message)


async def send_async(
    exc: Exception,
    context: str = "",
    error_key: Optional[str] = None,
) -> bool:
    """
    Sendet einen Fehler per Telegram (asynchron, für FastAPI-Handler).
    """
    key = error_key or type(exc).__name__
    if _is_rate_limited(key):
        logger.debug(f"[error_reporter] Rate-limited für '{key}' – Nachricht unterdrückt")
        return False

    error_type = type(exc).__name__
    description = str(exc)[:200]
    location = _extract_location(None, exc.__traceback__)
    tb_short = _short_traceback(exc)

    message = _build_message(error_type, description, location, tb_short, context)
    logger.info(f"[error_reporter] Sende Fehler-Meldung an Telegram (async): {error_type}")

    return await _send_telegram_async(message)


def send_custom(
    title: str,
    body: str,
    error_key: Optional[str] = None,
) -> bool:
    """
    Sendet eine benutzerdefinierte Meldung per Telegram (z.B. Startup-Events).
    """
    key = error_key or title
    if _is_rate_limited(key):
        return False

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = _get_system_stats()
    host = platform.node() or "unbekannt"

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    message = (
        f"[WARNING] <b>VERA Meldung</b> — {ts}\n"
        f"\n\n"
        f"<b>{esc(title)}</b>\n\n"
        f"{esc(body)}\n\n"
        f"[SAVE] {stats}\n"
        f" Host: {esc(host)}"
    )
    return _send_telegram_sync(message)


# ---------------------------------------------------------------------------
# System-Health JSON (für Telegram-Versand, Screenshot-Ersatz)
# ---------------------------------------------------------------------------
def get_system_health() -> dict:
    """
    Gibt System-Health als Dict zurück.
    Kann als Telegram-Nachricht gesendet werden (Ersatz für Screenshot).
    """
    health = {
        "timestamp": datetime.now().isoformat(),
        "host": platform.node(),
        "platform": platform.system(),
    }
    try:
        import psutil
        health["ram_percent"] = psutil.virtual_memory().percent
        health["disk_free_gb"] = round(psutil.disk_usage("/").free / (1024 ** 3), 1)
        health["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        health["process_count"] = len(psutil.pids())
    except Exception:
        pass
    return health
