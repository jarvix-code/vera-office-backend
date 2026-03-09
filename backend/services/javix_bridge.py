"""
Javix Bridge - Sendet strukturierte Bug-Reports an Javix (OpenClaw) zur automatischen Behebung.

Kommunikation via JSON-Queue-Dateien:
  data/bug_queue/*.json  → Javix liest diese im Heartbeat
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vera.javix_bridge")

QUEUE_DIR = Path(__file__).parent.parent.parent / "data" / "bug_queue"
PROCESSED_DIR = QUEUE_DIR / "processed"


def init_queue():
    """Create queue directories."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def submit_bug(analysis: dict, original_text: str, ticket_id: int,
               user_info: Optional[dict] = None, media_path: Optional[str] = None) -> str:
    """
    Submit analyzed bug to Javix queue.
    
    Returns: path to queue file
    """
    init_queue()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bug_{ticket_id:04d}_{timestamp}.json"
    filepath = QUEUE_DIR / filename

    payload = {
        "version": 1,
        "ticket_id": ticket_id,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        # Original
        "original_text": original_text,
        "media_path": media_path,
        "user": user_info,
        # LLM Analysis
        "analysis": analysis,
        # Javix instructions
        "javix_task": {
            "action": "investigate_and_fix",
            "project_root": "C:\\Jarvix\\vera-office",
            "module": analysis.get("module", "system"),
            "severity": analysis.get("severity", "medium"),
            "affected_files": analysis.get("affected_files", []),
            "title": analysis.get("title", "Unknown bug"),
            "fix_hint": analysis.get("fix_hint", ""),
        }
    }

    filepath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Bug #{ticket_id} submitted to Javix queue: {filepath}")
    return str(filepath)


def get_pending_bugs() -> list[dict]:
    """Get all pending bugs from queue (for Javix to process)."""
    init_queue()
    bugs = []
    for f in sorted(QUEUE_DIR.glob("bug_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_queue_file"] = str(f)
            bugs.append(data)
        except Exception as e:
            logger.error(f"Failed to read {f}: {e}")
    return bugs


def mark_processed(queue_file: str, result: str = "fixed"):
    """Move processed bug to processed directory."""
    src = Path(queue_file)
    if not src.exists():
        return
    
    # Update status
    data = json.loads(src.read_text(encoding="utf-8"))
    data["status"] = result
    data["processed_at"] = datetime.now().isoformat()
    
    dst = PROCESSED_DIR / src.name
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    src.unlink()
    logger.info(f"Bug marked as {result}: {src.name}")
