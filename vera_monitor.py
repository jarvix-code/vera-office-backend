#!/usr/bin/env python3
"""
VERA Backend Monitor - Auto-Restart nach Updates
Läuft im Hintergrund, prüft alle 30s:
- Ob Backend läuft
- Ob .restart_pending Flag existiert (nach Update)

Bei Update: Startet Backend automatisch neu.
Für iPad-Nutzung: Kein manueller Eingriff nötig!
"""
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "vera_monitor.log"
RESTART_FLAG = DATA_DIR / ".restart_pending"
PYTHON_EXE = r"C:\Users\jarvi\AppData\Local\Programs\Python\Python311\python.exe"

LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def is_backend_running():
    """Prüft ob VERA Backend läuft."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                """
                $backend = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
                    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                    $cmd -like "*uvicorn*backend.main*" -or $cmd -like "*backend*main.py*"
                }
                if ($backend) { Write-Output "1" } else { Write-Output "0" }
                """
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() == "1"
    except Exception as e:
        logger.error(f"Failed to check backend: {e}")
        return False


def kill_backend():
    """Stoppt VERA Backend."""
    try:
        logger.info("Stopping VERA Backend...")
        subprocess.run(
            [
                "powershell",
                "-Command",
                """
                Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
                    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                    $cmd -like "*uvicorn*" -or $cmd -like "*backend*main*"
                } | Stop-Process -Force
                """
            ],
            timeout=10
        )
        time.sleep(2)
        logger.info("Backend stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to stop backend: {e}")
        return False


def start_backend():
    """Startet VERA Backend."""
    try:
        logger.info("Starting VERA Backend...")
        subprocess.Popen(
            [
                PYTHON_EXE,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload"
            ],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        time.sleep(5)
        
        if is_backend_running():
            logger.success("✅ Backend started successfully")
            return True
        else:
            logger.error("❌ Backend failed to start")
            return False
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        return False


def restart_backend():
    """Stoppt und startet Backend neu."""
    logger.warning("🔄 Restarting Backend...")
    
    # 1. Stop
    kill_backend()
    
    # 2. Start
    return start_backend()


def main():
    """Haupt-Loop: Überwache Backend + Restart-Flag."""
    logger.info("=" * 60)
    logger.info("VERA Backend Monitor STARTED")
    logger.info(f"Check interval: 30s")
    logger.info(f"Restart flag: {RESTART_FLAG}")
    logger.info("=" * 60)
    
    while True:
        try:
            # 1. Check Restart Flag (nach Update)
            if RESTART_FLAG.exists():
                logger.warning("⚠️ RESTART FLAG DETECTED (Update installiert)")
                RESTART_FLAG.unlink()  # Lösche Flag
                
                if restart_backend():
                    logger.success("✅ Backend neu gestartet nach Update")
                else:
                    logger.error("❌ Backend-Restart fehlgeschlagen")
            
            # 2. Check ob Backend läuft
            elif not is_backend_running():
                logger.warning("⚠️ Backend ist DOWN - starte neu...")
                if restart_backend():
                    logger.success("✅ Backend wiederhergestellt")
                else:
                    logger.error("❌ Backend-Start fehlgeschlagen")
            
            else:
                # Alles OK
                logger.debug("Backend: OK")
            
            # Warte 30s
            time.sleep(30)
        
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
