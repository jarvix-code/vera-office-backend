"""
VERA Office - VPN Update Client
Verbindet sich periodisch mit VERA Admin Server und zieht Updates.
KEIN USB — nur Netzwerk/VPN.
"""
import json
import shutil
import threading
import time
import zipfile
from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class UpdateClient:
    """
    Periodischer Update-Client für VERA Office.
    Prüft alle 24h beim Admin Server auf neue Versionen.
    """
    
    def __init__(self, config):
        self.config = config
        self.base_dir = config.BASE_DIR
        self.data_dir = config.DATA_DIR
        self.update_dir = self.data_dir / "updates"
        self.backup_dir = self.data_dir / "backups"
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Update server URL from config
        self.server_url = getattr(config, 'UPDATE_SERVER', None) or "https://updates.vera-office.de"
        self.check_interval = 24 * 60 * 60  # 24 hours
        self.current_version = config.APP_VERSION
        
        self._thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Startet den Update-Check-Thread."""
        if not HAS_REQUESTS:
            logger.warning("[WARNING] 'requests' nicht installiert — Update-Client deaktiviert")
            return
        
        self._thread = threading.Thread(target=self._run, daemon=True, name="vera-update-client")
        self._thread.start()
        logger.info(f" Update-Client gestartet (Server: {self.server_url})")
    
    def stop(self):
        """Stoppt den Update-Check-Thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run(self):
        """Hauptschleife: Prüft periodisch auf Updates."""
        # Warte 60 Sekunden nach Start, bevor erster Check
        self._stop_event.wait(60)
        
        while not self._stop_event.is_set():
            try:
                self._check_and_apply()
            except Exception as e:
                logger.error(f"Update-Check fehlgeschlagen: {e}")
            
            # Warte bis zum nächsten Check
            self._stop_event.wait(self.check_interval)
    
    def _check_and_apply(self):
        """Prüft auf Updates und wendet sie an."""
        logger.info("[SEARCH] Prüfe auf Updates...")
        
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/updates/check",
                params={"version": self.current_version},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.debug(f"Update-Server returned {response.status_code}")
                return
            
            update_info = response.json()
            
            if not update_info.get("available"):
                logger.info("[OK] Keine Updates verfügbar — System ist aktuell")
                return
            
            new_version = update_info.get("version", "unknown")
            download_url = update_info.get("download_url")
            checksum = update_info.get("checksum_sha256")
            
            logger.info(f" Update verfügbar: {self.current_version} -> {new_version}")
            
            if not download_url:
                logger.warning("Kein Download-URL im Update — überspringe")
                return
            
            # Download
            update_file = self._download_update(download_url, new_version, checksum)
            if not update_file:
                return
            
            # Backup erstellen
            self._create_backup()
            
            # Update anwenden
            success = self._apply_update(update_file, new_version)
            
            if success:
                logger.success(f"[OK] Update auf {new_version} erfolgreich angewendet")
                logger.info("   Neustart erforderlich um Änderungen zu aktivieren")
                # Update state file
                state_file = self.data_dir / "update_state.json"
                state_file.write_text(json.dumps({
                    "last_update": datetime.now().isoformat(),
                    "version": new_version,
                    "status": "applied_pending_restart"
                }), encoding='utf-8')
            else:
                logger.error("[ERROR] Update fehlgeschlagen — führe Rollback durch")
                self._rollback()
                
        except requests.ConnectionError:
            logger.debug("Update-Server nicht erreichbar (offline?)")
        except requests.Timeout:
            logger.debug("Update-Server Timeout")
        except Exception as e:
            logger.error(f"Update-Check Fehler: {e}")
    
    def _download_update(self, url: str, version: str, expected_checksum: str = None) -> Path | None:
        """Lädt Update-Paket herunter."""
        update_file = self.update_dir / f"vera-update-{version}.zip"
        
        try:
            logger.info(f" Lade Update herunter: {url}")
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Checksum verify
            if expected_checksum:
                import hashlib
                sha256 = hashlib.sha256()
                with open(update_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        sha256.update(chunk)
                actual = sha256.hexdigest()
                if actual != expected_checksum:
                    logger.error(f"[ERROR] Checksum mismatch: {actual} != {expected_checksum}")
                    update_file.unlink()
                    return None
            
            logger.info(f"[OK] Download abgeschlossen: {update_file.stat().st_size / 1024 / 1024:.1f} MB")
            return update_file
            
        except Exception as e:
            logger.error(f"Download fehlgeschlagen: {e}")
            update_file.unlink(missing_ok=True)
            return None
    
    def _create_backup(self):
        """Erstellt Backup vor Update."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        
        try:
            # Backup backend
            backend_src = self.base_dir / "backend"
            if backend_src.exists():
                shutil.copytree(backend_src, backup_path / "backend", 
                               ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            
            # Backup frontend dist
            frontend_dist = self.base_dir / "frontend" / "dist"
            if frontend_dist.exists():
                shutil.copytree(frontend_dist, backup_path / "frontend_dist")
            
            logger.info(f"[SAVE] Backup erstellt: {backup_path}")
            
            # Cleanup: nur letzte 3 Backups behalten
            backups = sorted(self.backup_dir.glob("backup_*"))
            for old_backup in backups[:-3]:
                shutil.rmtree(old_backup, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"Backup fehlgeschlagen: {e}")
    
    def _apply_update(self, update_file: Path, version: str) -> bool:
        """Wendet Update-ZIP an."""
        extract_dir = self.update_dir / f"extract_{version}"
        
        try:
            # Entpacken
            with zipfile.ZipFile(update_file, 'r') as zf:
                zf.extractall(extract_dir)
            
            # Backend-Dateien überschreiben
            backend_update = extract_dir / "backend"
            if backend_update.exists():
                for py_file in backend_update.rglob("*.py"):
                    rel = py_file.relative_to(backend_update)
                    target = self.base_dir / "backend" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(py_file, target)
            
            # Frontend dist überschreiben
            frontend_update = extract_dir / "frontend" / "dist"
            if frontend_update.exists():
                target = self.base_dir / "frontend" / "dist"
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(frontend_update, target)
            
            # Models überschreiben (wenn vorhanden)
            models_update = extract_dir / "models"
            if models_update.exists():
                for model_file in models_update.glob("*"):
                    target = self.base_dir / "models" / model_file.name
                    shutil.copy2(model_file, target)
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            update_file.unlink(missing_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Update-Anwendung fehlgeschlagen: {e}")
            shutil.rmtree(extract_dir, ignore_errors=True)
            return False
    
    def _rollback(self):
        """Rollback zum letzten Backup."""
        backups = sorted(self.backup_dir.glob("backup_*"))
        if not backups:
            logger.error("Kein Backup für Rollback verfügbar!")
            return
        
        latest_backup = backups[-1]
        logger.info(f" Rollback zu: {latest_backup.name}")
        
        try:
            # Backend wiederherstellen
            backend_backup = latest_backup / "backend"
            if backend_backup.exists():
                target = self.base_dir / "backend"
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(backend_backup, target)
            
            # Frontend wiederherstellen
            frontend_backup = latest_backup / "frontend_dist"
            if frontend_backup.exists():
                target = self.base_dir / "frontend" / "dist"
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(frontend_backup, target)
            
            logger.success("[OK] Rollback erfolgreich")
            
        except Exception as e:
            logger.error(f"[ERROR] Rollback fehlgeschlagen: {e}")
