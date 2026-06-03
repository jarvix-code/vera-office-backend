#!/usr/bin/env python3
"""
VERA Office - Hotfolder Watcher Daemon
=======================================
Standalone-Daemon: Überwacht einen konfigurierten Hotfolder-Pfad und löst
bei neuen Dokumenten die VERA-Intake-Pipeline aus (POST /api/documents/upload).

Leitprinzip 1: Kein Dokument geht verloren. (Fact #27539 / Bug #1134)

Startoptionen:
  python hotfolder_watcher.py            # Vordergrund (für systemd/supervisord)
  python hotfolder_watcher.py --daemon   # Hintergrund (PID-File wird geschrieben)

Konfiguration via ENV:
  VERA_HOTFOLDER_DIR     Zu überwachender Ordner (default: /opt/vera-office/data/hotfolder)
  VERA_API_URL           Backend-URL             (default: http://127.0.0.1:8080)
  VERA_API_TOKEN         Bearer-Token falls Auth aktiv (optional)
  VERA_LOG_FILE          Log-Datei-Pfad          (default: /opt/vera-office/logs/hotfolder_watcher.log)
  VERA_PID_FILE          PID-Datei-Pfad          (default: /opt/vera-office/hotfolder_watcher.pid)
  VERA_RETRY_MAX         Max. Retry-Versuche     (default: 3)
  VERA_RETRY_DELAY       Sekunden zwischen Retries (default: 5)

Bug #1134 Fix — Hephaestus Codex (backend_dev), 2026-06-03
"""

import os
import sys
import time
import signal
import asyncio
import logging
import argparse
import atexit
from pathlib import Path
from datetime import datetime

import httpx

# ---------------------------------------------------------------------------
# Konfiguration (aus ENV lesen — nie hardcoden)
# ---------------------------------------------------------------------------

HOTFOLDER_DIR = Path(os.environ.get("VERA_HOTFOLDER_DIR", "/opt/vera-office/data/hotfolder"))
API_URL       = os.environ.get("VERA_API_URL",  "http://127.0.0.1:8080")
API_TOKEN     = os.environ.get("VERA_API_TOKEN", "")
LOG_FILE      = Path(os.environ.get("VERA_LOG_FILE",  "/opt/vera-office/logs/hotfolder_watcher.log"))
PID_FILE      = Path(os.environ.get("VERA_PID_FILE",  "/opt/vera-office/hotfolder_watcher.pid"))
RETRY_MAX     = int(os.environ.get("VERA_RETRY_MAX",   "3"))
RETRY_DELAY   = int(os.environ.get("VERA_RETRY_DELAY", "5"))

UPLOAD_ENDPOINT = f"{API_URL.rstrip('/')}/api/documents/upload"

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}

# ---------------------------------------------------------------------------
# Logging Setup (strukturiert, Datei + Konsole)
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log = logging.getLogger("hotfolder_watcher")
    log.setLevel(logging.DEBUG)

    # Datei-Handler (rotiert nicht — für supervisord/systemd log-rotation zuständig)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)

    # Konsole (für systemd journal / supervisord stdout)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    return log


log = setup_logging()

# ---------------------------------------------------------------------------
# PID-File Management
# ---------------------------------------------------------------------------

def write_pid_file():
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    log.info(f"PID {os.getpid()} → {PID_FILE}")

def remove_pid_file():
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)
        log.info(f"PID-File entfernt: {PID_FILE}")

atexit.register(remove_pid_file)

# ---------------------------------------------------------------------------
# Intake-Pipeline: POST an VERA API
# ---------------------------------------------------------------------------

async def post_to_intake(file_path: Path) -> bool:
    """
    Sendet Datei an POST /api/documents/upload.
    Gibt True bei Erfolg zurück, False bei Fehler.
    """
    headers = {}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, _mime_type(file_path))}
                resp = await client.post(UPLOAD_ENDPOINT, files=files, headers=headers)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("duplicate"):
                log.warning(f"[DUPLICATE] {file_path.name} → bereits vorhanden (ID {data.get('document_id')})")
            else:
                log.info(f"[OK] {file_path.name} → pipeline ausgelöst (ID {data.get('document_id')})")
            return True
        else:
            log.error(f"[HTTP {resp.status_code}] {file_path.name} → {resp.text[:200]}")
            return False

    except httpx.ConnectError as e:
        log.error(f"[CONNECT_ERROR] API nicht erreichbar ({UPLOAD_ENDPOINT}): {e}")
        return False
    except Exception as e:
        log.error(f"[ERROR] Unerwarteter Fehler beim POST für {file_path.name}: {e}")
        return False


def _mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".tiff": "image/tiff",
        ".tif":  "image/tiff",
    }.get(ext, "application/octet-stream")


async def process_file_with_retry(file_path: Path):
    """
    Versucht max. RETRY_MAX Mal, die Datei an die Pipeline zu senden.
    Bei persistentem Fehler: brain_submit_bug via API (best-effort).
    """
    # Kurz warten damit Datei vollständig geschrieben ist (z.B. bei rsync/cp)
    await asyncio.sleep(0.8)

    if not file_path.exists():
        log.warning(f"[SKIP] {file_path.name} nicht mehr vorhanden (wurde bereits verarbeitet?)")
        return

    for attempt in range(1, RETRY_MAX + 1):
        log.info(f"[ATTEMPT {attempt}/{RETRY_MAX}] {file_path.name}")
        success = await post_to_intake(file_path)

        if success:
            # Datei aus Hotfolder entfernen (Pipeline hat Kopie übernommen)
            try:
                file_path.unlink(missing_ok=True)
                log.info(f"[CLEANUP] {file_path.name} aus Hotfolder entfernt")
            except Exception as e:
                log.warning(f"[CLEANUP_WARN] Konnte {file_path.name} nicht löschen: {e}")
            return

        if attempt < RETRY_MAX:
            log.warning(f"[RETRY] Warte {RETRY_DELAY}s vor Versuch {attempt + 1}...")
            await asyncio.sleep(RETRY_DELAY)

    # Alle Versuche fehlgeschlagen
    log.error(
        f"[PERSISTENT_FAILURE] {file_path.name} nach {RETRY_MAX} Versuchen nicht verarbeitet. "
        f"Datei bleibt im Hotfolder für manuelle Prüfung."
    )
    # best-effort: Fehler in brain_submit_bug melden (via API falls vorhanden)
    await _submit_bug_to_brain(file_path)


async def _submit_bug_to_brain(file_path: Path):
    """
    Best-effort: Meldet persistenten Fehler an Brain-API.
    Schlägt diese Meldung fehl, wird sie geloggt aber nicht erneut versucht.
    """
    try:
        brain_url = os.environ.get("VERA_BRAIN_URL", "http://127.0.0.1:8080")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{brain_url.rstrip('/')}/api/system/report-error",
                json={
                    "source": "hotfolder_watcher",
                    "severity": "HIGH",
                    "message": f"Hotfolder-Datei nach {RETRY_MAX} Versuchen nicht verarbeitet: {file_path.name}",
                    "file": str(file_path),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            log.info(f"[BRAIN_BUG] Fehler für {file_path.name} an Brain gemeldet")
    except Exception as e:
        log.warning(f"[BRAIN_BUG_FAILED] Konnte Fehler nicht an Brain melden: {e}")

# ---------------------------------------------------------------------------
# Hotfolder Watch-Loop (watchfiles — Rust-basiert, async)
# ---------------------------------------------------------------------------

async def watch_with_watchfiles():
    """
    Hauptschleife mit watchfiles (bevorzugt: Rust-Performance, async-native).
    """
    try:
        from watchfiles import awatch, Change
    except ImportError:
        log.warning("[WATCHFILES] watchfiles nicht installiert. Falle auf Poll-Loop zurück.")
        await watch_with_poll()
        return

    HOTFOLDER_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"[WATCH] watchfiles-Daemon aktiv. Überwache: {HOTFOLDER_DIR}")

    # Bereits vorhandene Dateien verarbeiten (Backlog beim Start)
    await process_existing_files()

    async for changes in awatch(HOTFOLDER_DIR):
        for change_type, path_str in changes:
            path = Path(path_str)
            # Nur neue/geänderte Dateien (kein Löschen)
            if change_type not in (Change.added, Change.modified):
                continue
            if not _is_processable(path):
                continue
            log.info(f"[EVENT] {change_type.name}: {path.name}")
            asyncio.create_task(process_file_with_retry(path))


async def watch_with_poll():
    """
    Fallback-Watch-Loop via Polling (kein watchfiles/watchdog nötig).
    Verwendet config.HOTFOLDER_POLL_INTERVAL (default 2s).
    """
    poll_interval = int(os.environ.get("VERA_POLL_INTERVAL", "2"))
    HOTFOLDER_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"[POLL] Polling-Daemon aktiv (Interval: {poll_interval}s). Überwache: {HOTFOLDER_DIR}")

    seen: set[str] = set()

    # Backlog beim Start
    await process_existing_files(seen)

    while True:
        try:
            current = {
                str(p) for p in HOTFOLDER_DIR.iterdir()
                if p.is_file() and _is_processable(p)
            }
            new_files = current - seen
            for path_str in new_files:
                path = Path(path_str)
                seen.add(path_str)
                log.info(f"[POLL] Neue Datei: {path.name}")
                asyncio.create_task(process_file_with_retry(path))

            # Entferne verarbeitete Dateien aus seen (damit gelöschte nicht ewig drin bleiben)
            seen = seen & current

        except Exception as e:
            log.error(f"[POLL_ERROR] {e}")

        await asyncio.sleep(poll_interval)


async def process_existing_files(seen: set = None):
    """Verarbeitet beim Start bereits vorhandene Dateien im Hotfolder (Backlog)."""
    backlog = [p for p in HOTFOLDER_DIR.iterdir() if p.is_file() and _is_processable(p)]
    if backlog:
        log.info(f"[BACKLOG] {len(backlog)} Datei(en) beim Start gefunden — verarbeite...")
        for f in backlog:
            if seen is not None:
                seen.add(str(f))
            asyncio.create_task(process_file_with_retry(f))


def _is_processable(path: Path) -> bool:
    """Prüft ob Datei verarbeitet werden soll (Typ, temp-Filter)."""
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    if path.name.startswith(".") or path.name.startswith("~"):
        return False
    if path.name.endswith(".tmp") or path.name.endswith(".part"):
        return False
    return True

# ---------------------------------------------------------------------------
# Graceful Shutdown
# ---------------------------------------------------------------------------

_shutdown_event: asyncio.Event | None = None


def _handle_signal(signum, frame):
    sig_name = signal.Signals(signum).name
    log.info(f"[SIGNAL] {sig_name} empfangen — fahre herunter...")
    if _shutdown_event:
        _shutdown_event.set()


async def main():
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Signal-Handler registrieren
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    log.info("=" * 60)
    log.info("VERA Hotfolder Watcher Daemon gestartet")
    log.info(f"  Hotfolder : {HOTFOLDER_DIR}")
    log.info(f"  API       : {UPLOAD_ENDPOINT}")
    log.info(f"  Max Retry : {RETRY_MAX}")
    log.info(f"  Log       : {LOG_FILE}")
    log.info(f"  PID       : {PID_FILE}")
    log.info("=" * 60)

    write_pid_file()

    # Starte Watch-Schleife als Task
    watch_task = asyncio.create_task(watch_with_watchfiles())

    # Warte auf Shutdown-Signal
    await _shutdown_event.wait()

    log.info("[SHUTDOWN] Stoppe Watch-Task...")
    watch_task.cancel()
    try:
        await watch_task
    except asyncio.CancelledError:
        pass

    log.info("[SHUTDOWN] Hotfolder Watcher sauber beendet.")

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERA Hotfolder Watcher Daemon")
    parser.add_argument(
        "--daemon", action="store_true",
        help="Als Hintergrundprozess starten (doppelter Fork, Unix only)"
    )
    args = parser.parse_args()

    if args.daemon:
        # Doppelter Fork für echten Unix-Daemon
        if sys.platform == "win32":
            log.error("--daemon nicht auf Windows unterstützt. Starte im Vordergrund.")
        else:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Elternprozess beendet
            os.setsid()
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Zweiter Elternprozess beendet
            # Umleiten von stdin/stdout/stderr
            sys.stdin = open(os.devnull, "r")
            # stdout/stderr landen im Log (File-Handler aktiv)

    asyncio.run(main())
