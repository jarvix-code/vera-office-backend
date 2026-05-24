"""
VERA Office - Hotfolder Scanner
Überwacht data/inbox/ auf neue Dateien und triggert Verarbeitung
"""
import time
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from loguru import logger
from backend.config import config


class DocumentHandler(FileSystemEventHandler):
    """
    Event Handler für neue Dokumente im Inbox-Ordner
    """

    def __init__(self, callback, loop: asyncio.AbstractEventLoop):
        """
        Args:
            callback: Async-Funktion die bei neuer Datei aufgerufen wird
            loop: Laufender asyncio Event-Loop (aus dem Async-Kontext des Aufrufers)
        """
        super().__init__()
        self.callback = callback
        self.loop = loop
        self.processing = set()  # Verhindere Doppelverarbeitung
        
    def on_created(self, event):
        """
        Wird aufgerufen wenn neue Datei erstellt wurde
        """
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Nur bestimmte Dateitypen verarbeiten
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        if file_path.suffix.lower() not in allowed_extensions:
            logger.debug(f"⏭ Überspringe: {file_path.name} (nicht unterstützter Dateityp)")
            return
        
        # Temporäre Dateien ignorieren
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return
            
        # Verhindere Doppelverarbeitung
        if str(file_path) in self.processing:
            return
            
        logger.info(f"[DOC] Neue Datei erkannt: {file_path.name}")
        self.processing.add(str(file_path))
        
        # Warte kurz damit Datei vollständig geschrieben ist
        time.sleep(0.5)
        
        # Rufe Callback auf (Verarbeitung).
        # on_created() läuft im watchdog-Thread (kein Event Loop) ->
        # run_coroutine_threadsafe() übergibt die Coroutine thread-safe an den
        # FastAPI/uvicorn Event Loop.
        try:
            asyncio.run_coroutine_threadsafe(self.callback(file_path), self.loop)
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei Verarbeitung von {file_path.name}: {e}")
        finally:
            self.processing.discard(str(file_path))


class HotfolderScanner:
    """
    Hotfolder-Watcher für automatische Dokumentenverarbeitung
    """

    def __init__(self, callback, loop: asyncio.AbstractEventLoop):
        """
        Args:
            callback: Async-Funktion die bei neuer Datei aufgerufen wird
                      (Signatur: async def process(file_path: Path))
            loop: Laufender asyncio Event-Loop aus dem aufrufenden Async-Kontext.
                  Verwende asyncio.get_running_loop() im lifespan-Handler.
        """
        self.observer = Observer()
        self.handler = DocumentHandler(callback, loop)
        self.inbox_path = config.INBOX_DIR
        self.running = False
        
    def start(self):
        """
        Startet Hotfolder-Überwachung
        """
        if not self.inbox_path.exists():
            self.inbox_path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f" Starte Hotfolder-Überwachung: {self.inbox_path}")
        
        self.observer.schedule(self.handler, str(self.inbox_path), recursive=False)
        self.observer.start()
        self.running = True
        
        logger.success(f"[OK] Hotfolder-Scanner aktiv")
        
    def stop(self):
        """
        Stoppt Hotfolder-Überwachung
        """
        if self.running:
            logger.info(" Stoppe Hotfolder-Scanner...")
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.success("[OK] Hotfolder-Scanner gestoppt")
    
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
