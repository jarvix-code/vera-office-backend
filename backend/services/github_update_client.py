"""
DEPRECATED — Dieser Client wird nicht mehr verwendet.
Ersetzt durch backend/services/update_client.py (Ed25519-signierter Update-Server).
Bitte nicht für neue Features verwenden. Wird in einer zukünftigen Version entfernt.
"""
# DEPRECATED: See backend/services/update_client.py
import asyncio
import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from loguru import logger

try:
    import httpx
except ImportError:
    httpx = None


class GitHubUpdateClient:
    """
    Update-Client für VERA Office via GitHub Releases.
    Nutzt GitHub API um nach neuen Releases zu suchen.
    """
    
    def __init__(self, repo_owner: str, repo_name: str, current_version: str, install_dir: Path, data_dir: Path):
        """
        Args:
            repo_owner: GitHub Username/Org (z.B. "boris-reimers")
            repo_name: Repository Name (z.B. "vera-office")
            current_version: Aktuelle Version (z.B. "1.0.0-alpha")
            install_dir: Installations-Verzeichnis
            data_dir: Data-Verzeichnis für Updates/Backups
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.install_dir = install_dir
        self.data_dir = data_dir
        
        self.api_base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.updates_dir = data_dir / "updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = data_dir / "backups" / "pre-update"
        
        self._last_check: Optional[datetime] = None
        self._latest_release: Optional[Dict] = None
    
    async def check_for_updates(self) -> Optional[Dict]:
        """
        Prüft GitHub Releases auf neue Version.
        
        Returns:
            Release-Info dict oder None
        """
        if not httpx:
            logger.warning("httpx nicht installiert - Updates deaktiviert")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get latest release
                headers = {"Accept": "application/vnd.github.v3+json"}
                if hasattr(self, 'github_token') and self.github_token:
                    headers["Authorization"] = f"Bearer {self.github_token}"
                resp = await client.get(
                    f"{self.api_base}/releases/latest",
                    headers=headers
                )
                
                if resp.status_code == 404:
                    logger.debug("Keine GitHub Releases gefunden")
                    return None
                
                if resp.status_code != 200:
                    logger.warning(f"GitHub API error: {resp.status_code}")
                    return None
                
                release = resp.json()
                latest_version = release["tag_name"].lstrip("v")  # "v1.0.1" -> "1.0.1"
                
                self._last_check = datetime.now()
                
                # Version-Vergleich
                if self._version_newer(latest_version, self.current_version):
                    self._latest_release = {
                        "version": latest_version,
                        "name": release["name"],
                        "body": release["body"],  # Changelog
                        "published_at": release["published_at"],
                        "assets": release["assets"],
                        "download_url": self._get_download_url(release["assets"])
                    }
                    logger.info(f" Update verfügbar: {self.current_version} -> {latest_version}")
                    return self._latest_release
                
                logger.debug(f"Aktuelle Version ({self.current_version}) ist aktuell")
                return None
        
        except Exception as e:
            logger.debug(f"GitHub Release Check fehlgeschlagen: {e}")
            return None
    
    def _get_download_url(self, assets: list) -> Optional[str]:
        """
        Findet das ZIP-Asset in den Release-Assets.
        
        Args:
            assets: Liste der Release-Assets
        
        Returns:
            Download-URL oder None
        """
        # Suche nach .zip Asset
        for asset in assets:
            if asset["name"].endswith(".zip"):
                return asset["browser_download_url"]
        
        # Fallback: Erstes Asset
        if assets:
            return assets[0]["browser_download_url"]
        
        return None
    
    async def download_update(self, version: str) -> Optional[Path]:
        """
        Lädt Update-ZIP von GitHub herunter.
        
        Args:
            version: Zu ladende Version
        
        Returns:
            Pfad zum heruntergeladenen ZIP oder None
        """
        if not self._latest_release or self._latest_release["version"] != version:
            logger.warning(f"Keine Release-Info für Version {version}")
            return None
        
        download_url = self._latest_release["download_url"]
        if not download_url:
            logger.error("Kein Download-URL in Release gefunden")
            return None
        
        update_file = self.updates_dir / f"vera-office-{version}.zip"
        
        try:
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                logger.info(f" Lade Update {version} herunter...")
                resp = await client.get(download_url)
                
                if resp.status_code != 200:
                    logger.error(f"Download fehlgeschlagen: HTTP {resp.status_code}")
                    return None
                
                update_file.write_bytes(resp.content)
                logger.success(f"[OK] Update heruntergeladen: {update_file.name} ({len(resp.content) / 1024 / 1024:.1f} MB)")
                return update_file
        
        except Exception as e:
            logger.error(f"Download-Fehler: {e}")
            return None
    
    def verify_sha256(self, zip_path: Path) -> bool:
        """
        Verifiziert SHA256-Hash des Updates (falls SHA256SUMS vorhanden).
        
        Args:
            zip_path: Pfad zum Update-ZIP
        
        Returns:
            True wenn Hash stimmt oder keine Prüfsumme vorhanden, False bei Mismatch
        """
        # Suche nach SHA256SUMS-Asset im Release
        if not self._latest_release:
            logger.warning("Keine Release-Info - überspringe Hash-Check")
            return True
        
        # Check ob SHA256SUMS Asset existiert
        sha256_asset = None
        for asset in self._latest_release.get("assets", []):
            if "SHA256SUMS" in asset["name"].upper():
                sha256_asset = asset
                break
        
        if not sha256_asset:
            logger.info("Kein SHA256SUMS gefunden - überspringe Hash-Check")
            return True
        
        # TODO: SHA256SUMS herunterladen und vergleichen
        # Für jetzt: Skip
        logger.debug("SHA256-Verifikation noch nicht implementiert")
        return True
    
    def create_backup(self):
        """Erstellt Backup des aktuellen Installations-Verzeichnisses."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{self.current_version}_{timestamp}"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f" Erstelle Backup: {backup_path.name}")
        
        # Kopiere wichtige Verzeichnisse
        for dir_name in ["backend", "frontend", "config"]:
            src = self.install_dir / dir_name
            if src.exists():
                shutil.copytree(src, backup_path / dir_name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        
        logger.success("[OK] Backup erstellt")
        return backup_path
    
    async def apply_update(self, zip_path: Path) -> bool:
        """
        Entpackt und installiert Update.
        DANACH: Triggert automatischen Backend-Restart.
        
        Args:
            zip_path: Pfad zum Update-ZIP
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # 1. Backup erstellen
            backup_path = self.create_backup()
            
            # 2. ZIP entpacken
            logger.info(" Entpacke Update...")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Extrahiere in Install-Dir
                zf.extractall(self.install_dir)
            
            logger.success("[OK] Update installiert")
            
            # 3. Trigger Backend Restart (automatisch)
            self._trigger_restart()
            
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Update-Installation fehlgeschlagen: {e}")
            # TODO: Rollback
            return False
    
    def _trigger_restart(self):
        """
        Triggert Backend-Restart nach Update.
        
        Strategie:
        1. Schreibe Restart-Flag-File
        2. sys.exit(0) -> Backend beendet sich
        3. Monitor Worker / Service Manager startet Backend neu
        """
        import sys
        import os
        
        # Schreibe Restart-Flag
        restart_flag = self.data_dir / ".restart_pending"
        restart_flag.write_text("restart")
        
        logger.warning(" Backend wird neu gestartet in 3 Sekunden...")
        
        # Schedule restart via asyncio
        import asyncio
        loop = asyncio.get_event_loop()
        
        async def delayed_exit():
            await asyncio.sleep(3)  # 3s Verzögerung damit Response noch rausgeht
            logger.info("[WARNING] RESTART NOW")
            os._exit(0)  # Hard exit (sys.exit würde Exception werfen)
        
        asyncio.create_task(delayed_exit())
    
    def _version_newer(self, v1: str, v2: str) -> bool:
        """
        Vergleicht Versionen (semantic versioning).
        
        Args:
            v1: Neue Version
            v2: Alte Version
        
        Returns:
            True wenn v1 > v2
        """
        def parse_version(v: str) -> tuple:
            # "1.0.1-alpha" -> (1, 0, 1)
            v = v.split("-")[0]  # Remove suffix
            parts = v.split(".")
            return tuple(int(p) for p in parts if p.isdigit())
        
        try:
            return parse_version(v1) > parse_version(v2)
        except:
            return False
    
    def get_status(self) -> Dict:
        """Gibt aktuellen Update-Status zurück."""
        return {
            "current_version": self.current_version,
            "update_available": self._latest_release is not None,
            "latest_version": self._latest_release["version"] if self._latest_release else None,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "repo": f"{self.repo_owner}/{self.repo_name}"
        }
