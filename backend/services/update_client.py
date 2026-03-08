"""
VERA Office Update Client - Ed25519 signierte Updates
Prüft periodisch auf Updates, lädt herunter, verifiziert, installiert.
"""
import asyncio
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from backend.config import config

# Singleton
_update_client: Optional["UpdateClient"] = None


def get_update_client():
    """
    Factory für Update-Client.
    Nutzt GitHub Update Client im Entwicklermodus.
    """
    global _update_client
    
    if _update_client is not None:
        return _update_client
    
    # Check Config für Update-Mode
    update_config = config.CONFIG_DATA.get("update", {})
    mode = update_config.get("mode", "github")
    
    if mode == "github":
        # GitHub Release Update Client
        from backend.services.github_update_client import GitHubUpdateClient
        
        repo_owner = update_config.get("github_repo_owner", "boris-reimers")
        repo_name = update_config.get("github_repo_name", "vera-office")
        
        _update_client = GitHubUpdateClient(
            repo_owner=repo_owner,
            repo_name=repo_name,
            current_version=config.APP_VERSION,
            install_dir=config.BASE_DIR,
            data_dir=config.DATA_DIR
        )
        logger.info(f"GitHub Update Client initialisiert: {repo_owner}/{repo_name}")
    else:
        # Original Server-based Update Client
        _update_client = UpdateClient(update_config)
        logger.info(f"Server Update Client initialisiert: {update_config.get('server_url')}")
    
    return _update_client


class UpdateClient:
    """
    Update-Client für VERA Office.
    - Periodischer Check gegen Update-Server
    - Ed25519-Signatur-Verifikation
    - Rollback bei Fehler
    """
    
    def __init__(self, cfg: dict):
        self.update_server = cfg.get("update_server", "https://updates.vera-office.de")
        self.version = cfg.get("version", config.APP_VERSION)
        self.install_dir = Path(cfg.get("install_dir", str(config.BASE_DIR)))
        self.check_interval_hours = cfg.get("update_check_interval_hours", 24)
        self.auto_update = cfg.get("auto_update", False)
        
        self.updates_dir = config.DATA_DIR / "updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = config.DATA_DIR / "backups" / "pre-update"
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._latest_update: Optional[dict] = None
    
    async def start(self):
        """Startet periodische Update-Checks."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"Update-Client gestartet (Intervall: {self.check_interval_hours}h)")
    
    async def stop(self):
        """Stoppt den Update-Client."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Update-Client gestoppt")
    
    async def _check_loop(self):
        """Periodische Update-Prüfung."""
        # Erste Prüfung nach 60s (nicht sofort beim Start)
        await asyncio.sleep(60)
        while self._running:
            try:
                await self.check_for_updates()
            except Exception as e:
                logger.debug(f"Update-Check fehlgeschlagen: {e}")
            await asyncio.sleep(self.check_interval_hours * 3600)
    
    async def check_for_updates(self) -> Optional[dict]:
        """
        Prüft ob ein Update verfügbar ist.
        Returns: Update-Info dict oder None.
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.get(f"{self.update_server}/api/updates/manifest.json")
                if resp.status_code != 200:
                    return None
                
                manifest = resp.json()
                latest_version = manifest.get("version", "0.0.0")
                
                if self._version_newer(latest_version, self.version):
                    self._latest_update = manifest
                    logger.info(f"Update verfügbar: {self.version} -> {latest_version}")
                    return manifest
                
                return None
        except Exception as e:
            logger.debug(f"Update-Server nicht erreichbar: {e}")
            return None
    
    def get_available_update(self) -> Optional[dict]:
        """Gibt das zuletzt gefundene Update zurück."""
        return self._latest_update
    
    async def download_and_install(self, manifest: dict) -> dict:
        """
        Lädt Update herunter, verifiziert Signatur, erstellt Backup, installiert.
        Returns: {"success": bool, "message": str}
        """
        try:
            download_url = manifest.get("download_url")
            expected_hash = manifest.get("sha256")
            version = manifest.get("version")
            
            if not download_url:
                return {"success": False, "message": "Kein Download-URL im Manifest"}
            
            # 1. Download
            logger.info(f"Lade Update v{version} herunter...")
            update_file = self.updates_dir / f"vera-office-{version}.zip"
            
            import httpx
            async with httpx.AsyncClient(timeout=300.0, verify=False) as client:
                resp = await client.get(download_url)
                if resp.status_code != 200:
                    return {"success": False, "message": f"Download fehlgeschlagen: HTTP {resp.status_code}"}
                update_file.write_bytes(resp.content)
            
            # 2. Hash verifizieren
            if expected_hash:
                actual_hash = hashlib.sha256(update_file.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    update_file.unlink()
                    return {"success": False, "message": "Hash-Verifikation fehlgeschlagen"}
            
            # 3. Ed25519-Signatur verifizieren
            sig_ok = await self._verify_signature(manifest)
            if not sig_ok:
                update_file.unlink()
                return {"success": False, "message": "Signatur-Verifikation fehlgeschlagen"}
            
            # 4. Backup erstellen
            self._create_backup()
            
            # 5. Update installieren (ZIP entpacken)
            try:
                with zipfile.ZipFile(update_file, 'r') as zf:
                    zf.extractall(self.install_dir)
                logger.success(f"Update v{version} installiert")
                self._latest_update = None
                return {"success": True, "message": f"Update auf v{version} erfolgreich. Neustart erforderlich."}
            except Exception as e:
                # Rollback
                self._rollback()
                return {"success": False, "message": f"Installation fehlgeschlagen, Rollback durchgeführt: {e}"}
            
        except Exception as e:
            logger.error(f"Update fehlgeschlagen: {e}")
            return {"success": False, "message": str(e)}
    
    async def _verify_signature(self, manifest: dict) -> bool:
        """Verifiziert Ed25519-Signatur des Manifests."""
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives import serialization
            import base64
            
            sig_b64 = manifest.get("signature")
            if not sig_b64:
                logger.warning("Kein Signatur-Feld im Manifest")
                return False
            
            # Public Key laden
            pub_key_path = self.install_dir / "keys" / "public.pem"
            if not pub_key_path.exists():
                logger.warning("Public Key nicht gefunden")
                return False
            
            public_key = serialization.load_pem_public_key(pub_key_path.read_bytes())
            
            # Payload = Manifest ohne Signatur
            manifest_copy = {k: v for k, v in manifest.items() if k != "signature"}
            payload = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':')).encode('utf-8')
            
            signature = base64.b64decode(sig_b64)
            public_key.verify(signature, payload)
            
            logger.info("Update-Signatur verifiziert (Ed25519)")
            return True
        except Exception as e:
            logger.error(f"Signatur-Verifikation fehlgeschlagen: {e}")
            return False
    
    def _create_backup(self):
        """Erstellt Backup vor Update."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            
            # Nur Backend + Config sichern (nicht Models/Data)
            for subdir in ["backend", "config", "frontend"]:
                src = self.install_dir / subdir
                if src.exists():
                    shutil.copytree(src, backup_path / subdir, dirs_exist_ok=True)
            
            logger.info(f"Backup erstellt: {backup_path}")
        except Exception as e:
            logger.warning(f"Backup fehlgeschlagen: {e}")
    
    def _rollback(self):
        """Stellt letztes Backup wieder her."""
        try:
            if not self.backup_dir.exists():
                logger.error("Kein Backup zum Wiederherstellen")
                return
            
            # Neuestes Backup finden
            backups = sorted(self.backup_dir.iterdir(), reverse=True)
            if not backups:
                logger.error("Keine Backups gefunden")
                return
            
            latest = backups[0]
            for subdir in ["backend", "config", "frontend"]:
                src = latest / subdir
                dst = self.install_dir / subdir
                if src.exists():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
            
            logger.info(f"Rollback durchgeführt von: {latest}")
        except Exception as e:
            logger.error(f"Rollback fehlgeschlagen: {e}")
    
    def _version_newer(self, new_ver: str, current_ver: str) -> bool:
        """Vergleicht Versionsnummern."""
        def parse(v):
            parts = v.replace("-alpha", "").replace("-beta", "").split(".")
            return tuple(int(p) for p in parts if p.isdigit())
        try:
            return parse(new_ver) > parse(current_ver)
        except Exception:
            return False


def init_update_client(cfg: dict) -> UpdateClient:
    global _update_client
    _update_client = UpdateClient(cfg)
    return _update_client

def get_update_client() -> Optional[UpdateClient]:
    return _update_client
