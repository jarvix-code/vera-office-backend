"""
VERA Office Telemetry — Heartbeat + Events an Admin-Server
Sendet anonymisierte Systemstatus- und Nutzungsdaten (DSGVO-konform)
"""
import asyncio
import platform
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import aiohttp
from loguru import logger

from backend.config import config


class TelemetryClient:
    """
    Telemetrie-Client für VERA Office
    
    Features:
    - Heartbeat alle 30 Minuten (konfigurierbar)
    - Event-Tracking (OCR, Klassifikation, Suche, etc.)
    - Offline-Puffer (max. 1000 Events)
    - DSGVO-konform (keine personenbezogenen Daten)
    - Lizenz-Key als Authorization Header
    """
    
    def __init__(self, config_dict: dict):
        """
        Initialisiere Telemetrie-Client
        
        Args:
            config_dict: Config-Dict mit Keys:
                - update_server: Server-URL (gleiches wie Update-Server)
                - device_id: Eindeutige Geräte-ID (UUID)
                - license_key: VERA-Lizenzschlüssel
                - version: Aktuelle Version
                - telemetry.enabled: Telemetrie aktiviert?
                - telemetry.heartbeat_interval_minutes: Heartbeat-Intervall
                - telemetry.batch_size: Events pro Batch
                - telemetry.offline_buffer_max: Max. Events im Offline-Puffer
        """
        self.enabled = config_dict.get("telemetry", {}).get("enabled", True)
        self.server_url = config_dict.get("update_server", "https://updates.vera-office.de")
        self.device_id = config_dict.get("device_id") or config_dict.get("telemetry", {}).get("device_id")
        self.license_key = config_dict.get("license_key", "")
        self.version = config_dict.get("version", "1.0.0")
        
        telemetry_config = config_dict.get("telemetry", {})
        self.heartbeat_interval_minutes = telemetry_config.get("heartbeat_interval_minutes", 30)
        self.batch_size = telemetry_config.get("batch_size", 50)
        self.offline_buffer_max = telemetry_config.get("offline_buffer_max", 1000)
        
        self._event_buffer: List[Dict[str, Any]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None
        self._startup_time = datetime.now()
        
        if not self.enabled:
            logger.info("📊 Telemetrie deaktiviert (via Config)")
        else:
            logger.info(f"📊 Telemetrie-Client initialisiert (Device-ID: {self.device_id}, Intervall: {self.heartbeat_interval_minutes} min)")
    
    def _get_headers(self) -> Dict[str, str]:
        """Erstellt HTTP-Headers mit Lizenz-Key als Authorization"""
        headers = {
            "User-Agent": f"VERA-Office/{self.version}",
            "Content-Type": "application/json"
        }
        
        if self.license_key:
            headers["Authorization"] = f"Bearer {self.license_key}"
        
        return headers
    
    def _get_system_status(self) -> Dict[str, Any]:
        """
        Sammelt Systemstatus (CPU, RAM, Disk, Uptime)
        DSGVO-konform: Keine personenbezogenen Daten, nur Metriken
        """
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count(logical=True)
            
            # RAM
            mem = psutil.virtual_memory()
            mem_total_gb = round(mem.total / (1024**3), 1)
            mem_used_gb = round(mem.used / (1024**3), 1)
            mem_percent = mem.percent
            
            # Disk (Installationsverzeichnis)
            disk = psutil.disk_usage(config.DATA_DIR)
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_used_gb = round(disk.used / (1024**3), 1)
            disk_percent = disk.percent
            
            # Uptime
            uptime_seconds = (datetime.now() - self._startup_time).total_seconds()
            
            # Dokumenten-Count (aus DB oder Filesystem)
            doc_count = 0
            try:
                from backend.db.database import SessionLocal
                from backend.models.document import Document
                db = SessionLocal()
                doc_count = db.query(Document).count()
                db.close()
            except Exception:
                # Fallback: Zähle Dateien in documents/
                doc_dir = config.DOCUMENTS_DIR
                if doc_dir.exists():
                    doc_count = len(list(doc_dir.rglob("*.pdf")))
            
            return {
                "status": "healthy",  # healthy | degraded | error
                "uptime_seconds": int(uptime_seconds),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total_gb": mem_total_gb,
                    "used_gb": mem_used_gb,
                    "percent": mem_percent
                },
                "disk": {
                    "total_gb": disk_total_gb,
                    "used_gb": disk_used_gb,
                    "percent": disk_percent
                },
                "documents": {
                    "count": doc_count
                },
                "platform": {
                    "os": platform.system(),
                    "version": platform.version(),
                    "python": platform.python_version()
                }
            }
        
        except Exception as e:
            logger.warning(f"⚠️ Fehler beim Sammeln von System-Status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_heartbeat(self) -> bool:
        """
        Sendet Heartbeat mit Systemstatus an Server
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self.enabled:
            return False
        
        try:
            url = f"{self.server_url}/api/telemetry/heartbeat"
            payload = {
                "device_id": self.device_id,
                "version": self.version,
                "timestamp": datetime.now().isoformat(),
                **self._get_system_status()
            }
            
            logger.debug(f"💓 Sende Heartbeat an {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.debug("✅ Heartbeat gesendet")
                        return True
                    else:
                        logger.warning(f"⚠️ Heartbeat fehlgeschlagen: HTTP {response.status}")
                        return False
        
        except aiohttp.ClientError as e:
            logger.debug(f"⚠️ Telemetrie-Server nicht erreichbar: {e}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Fehler beim Senden des Heartbeats: {e}")
            return False
    
    async def send_event(
        self,
        action: str,
        success: bool,
        duration_ms: int = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Sendet Telemetrie-Event an Server
        
        Args:
            action: Aktion (z.B. "ocr", "classify", "search", "upload")
            success: Aktion erfolgreich?
            duration_ms: Dauer in Millisekunden
            details: Zusätzliche Details (keine personenbezogenen Daten!)
        
        Examples:
            await telemetry.send_event("ocr", True, 2500, {"language": "de", "pages": 1})
            await telemetry.send_event("classify", True, 1200, {"confidence": 0.95})
            await telemetry.send_event("search", True, 150, {"results": 5})
        """
        if not self.enabled:
            return
        
        event = {
            "device_id": self.device_id,
            "version": self.version,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "success": success,
            "duration_ms": duration_ms,
            "details": details or {}
        }
        
        # Event zum Puffer hinzufügen
        self._event_buffer.append(event)
        
        # Puffer-Limit prüfen
        if len(self._event_buffer) > self.offline_buffer_max:
            logger.warning(f"⚠️ Telemetrie-Puffer voll ({self.offline_buffer_max}) - älteste Events werden verworfen")
            self._event_buffer = self._event_buffer[-self.offline_buffer_max:]
        
        # Wenn Batch-Größe erreicht → sofort senden
        if len(self._event_buffer) >= self.batch_size:
            await self._flush_events()
    
    async def _flush_events(self) -> bool:
        """
        Sendet alle gepufferten Events an Server
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self._event_buffer:
            return True
        
        try:
            url = f"{self.server_url}/api/telemetry/events"
            batch = self._event_buffer[:self.batch_size]
            
            logger.debug(f"📊 Sende {len(batch)} Telemetrie-Events")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"events": batch},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        # Erfolgreich gesendete Events aus Puffer entfernen
                        self._event_buffer = self._event_buffer[len(batch):]
                        logger.debug(f"✅ {len(batch)} Events gesendet")
                        return True
                    else:
                        logger.warning(f"⚠️ Event-Upload fehlgeschlagen: HTTP {response.status}")
                        return False
        
        except aiohttp.ClientError as e:
            logger.debug(f"⚠️ Telemetrie-Server nicht erreichbar: {e}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Fehler beim Senden von Events: {e}")
            return False
    
    async def _background_heartbeat_loop(self):
        """Background-Loop für regelmäßige Heartbeats"""
        logger.info(f"💓 Heartbeat-Loop gestartet (alle {self.heartbeat_interval_minutes} min)")
        
        # Erster Heartbeat sofort
        await self.send_heartbeat()
        self._last_heartbeat = datetime.now()
        
        while self._running:
            try:
                # Warte bis nächster Heartbeat fällig
                await asyncio.sleep(self.heartbeat_interval_minutes * 60)
                
                # Sende Heartbeat
                await self.send_heartbeat()
                self._last_heartbeat = datetime.now()
                
                # Flush Events (wenn vorhanden)
                if self._event_buffer:
                    await self._flush_events()
            
            except Exception as e:
                logger.error(f"❌ Fehler im Heartbeat-Loop: {e}")
                await asyncio.sleep(60)  # Retry nach 1 Minute
    
    async def start(self):
        """Startet Background-Task für Heartbeats"""
        if not self.enabled:
            logger.info("📊 Telemetrie deaktiviert - kein Background-Task")
            return
        
        if self._running:
            logger.warning("⚠️ Telemetrie-Client läuft bereits")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._background_heartbeat_loop())
        logger.info("✅ Telemetrie-Client gestartet")
    
    async def stop(self):
        """Stoppt Background-Task und flusht verbleibende Events"""
        if not self._running:
            return
        
        logger.info("🛑 Stoppe Telemetrie-Client...")
        self._running = False
        
        # Flush verbleibende Events
        if self._event_buffer:
            logger.info(f"📊 Sende verbleibende {len(self._event_buffer)} Events...")
            await self._flush_events()
        
        # Task beenden
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Telemetrie-Client gestoppt")


# Singleton-Instanz
_telemetry_client: Optional[TelemetryClient] = None


def get_telemetry_client() -> Optional[TelemetryClient]:
    """Gibt Singleton-Instanz des Telemetrie-Clients zurück"""
    return _telemetry_client


def init_telemetry_client(config_dict: dict) -> TelemetryClient:
    """Initialisiert Telemetrie-Client (einmalig beim App-Start)"""
    global _telemetry_client
    _telemetry_client = TelemetryClient(config_dict)
    return _telemetry_client
