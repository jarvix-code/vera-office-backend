"""
VERA Auto-Fix Agent
Daemon-Service der:
1. data/bug_queue/ pollt (alle 30s)
2. Fix-Briefings erstellt für Coding-Agent
3. Telegram-Rückkanal an User bereitstellt
"""
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("vera.autofix_agent")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "vera.yaml"
QUEUE_DIR = PROJECT_ROOT / "data" / "bug_queue"
IN_PROGRESS_DIR = QUEUE_DIR / "in_progress"
FIX_TASKS_DIR = QUEUE_DIR / "fix_tasks"
BACKUP_DIR = QUEUE_DIR / "backups"

# Config
POLL_INTERVAL = 30  # seconds
MAX_CODE_LINES_PER_FILE = 200

# Global Telegram config
TELEGRAM_BOT_TOKEN = None
TELEGRAM_API_URL = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def load_config():
    """Load Telegram bot token from vera.yaml"""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_API_URL
    
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return False
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    TELEGRAM_BOT_TOKEN = cfg.get("telegram", {}).get("bot_token", "")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No telegram.bot_token in vera.yaml")
        return False
    
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    logger.info("✅ Telegram config loaded")
    return True


# ---------------------------------------------------------------------------
# Telegram Utilities
# ---------------------------------------------------------------------------
def send_to_user(telegram_user_id: int, message_text: str) -> bool:
    """
    Send message to a Telegram user.
    Returns True on success, False on failure.
    """
    if not TELEGRAM_API_URL:
        logger.error("Telegram not configured")
        return False
    
    try:
        response = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": telegram_user_id,
                "text": message_text,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"📤 Telegram sent to {telegram_user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Telegram send failed to {telegram_user_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------
def backup_file(filepath: Path):
    """Create backup before processing."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(filepath, backup_path)
    logger.debug(f"💾 Backup created: {backup_path.name}")


def read_code_file(file_path: str, max_lines: int = MAX_CODE_LINES_PER_FILE) -> dict:
    """
    Read source code file safely.
    Returns: {
        "path": str,
        "exists": bool,
        "lines": int,
        "content": str,  # truncated to max_lines
        "truncated": bool
    }
    """
    abs_path = PROJECT_ROOT / file_path if not Path(file_path).is_absolute() else Path(file_path)
    
    if not abs_path.exists():
        return {
            "path": file_path,
            "exists": False,
            "lines": 0,
            "content": "",
            "truncated": False,
            "error": "File not found"
        }
    
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        truncated = total_lines > max_lines
        content_lines = lines[:max_lines] if truncated else lines
        
        return {
            "path": file_path,
            "exists": True,
            "lines": total_lines,
            "content": "".join(content_lines),
            "truncated": truncated
        }
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {
            "path": file_path,
            "exists": True,
            "lines": 0,
            "content": "",
            "truncated": False,
            "error": str(e)
        }


# ---------------------------------------------------------------------------
# Fix Task Generation
# ---------------------------------------------------------------------------
def create_fix_briefing(bug_data: dict) -> Optional[Path]:
    """
    Create structured fix briefing for coding agent.
    
    Returns: path to fix_task JSON file
    """
    ticket_id = bug_data.get("ticket_id", 0)
    analysis = bug_data.get("analysis", {})
    affected_files = analysis.get("affected_files", [])
    
    logger.info(f"🔧 Creating fix briefing for ticket #{ticket_id}...")
    
    # Read source code for affected files
    code_context = []
    for file_path in affected_files[:5]:  # Max 5 files
        code_data = read_code_file(file_path)
        code_context.append(code_data)
        
        if code_data.get("exists"):
            status = "✂️ TRUNCATED" if code_data.get("truncated") else "✅"
            logger.info(f"  {status} {file_path} ({code_data.get('lines', 0)} lines)")
        else:
            logger.warning(f"  ⚠️ {file_path} — NOT FOUND")
    
    # Build fix briefing
    fix_briefing = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "ticket_id": ticket_id,
        
        # Original bug data
        "bug": {
            "original_text": bug_data.get("original_text", ""),
            "media_path": bug_data.get("media_path"),
            "user": bug_data.get("user", {}),
        },
        
        # Analysis
        "analysis": analysis,
        
        # Code context
        "code_context": code_context,
        
        # Instructions for coding agent
        "fix_instructions": {
            "module": analysis.get("module", "system"),
            "severity": analysis.get("severity", "medium"),
            "title": analysis.get("title", "Unknown bug"),
            "possible_cause": analysis.get("possible_cause", ""),
            "fix_hint": analysis.get("fix_hint", ""),
            "reproduction_steps": analysis.get("reproduction_steps", []),
            "expected_behavior": analysis.get("expected", ""),
        },
        
        # Status tracking
        "status": "pending",
        "assigned_to": None,  # Will be filled by Javix/Coding-Agent
        "user_replies": [],  # Telegram replies from user
    }
    
    # Save to fix_tasks/
    FIX_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_file = FIX_TASKS_DIR / f"fix_task_{ticket_id:04d}_{timestamp}.json"
    
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(fix_briefing, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Fix briefing created: {task_file.name}")
    return task_file


def move_to_in_progress(bug_file: Path):
    """Move bug file to in_progress directory."""
    IN_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    dest = IN_PROGRESS_DIR / bug_file.name
    shutil.move(str(bug_file), str(dest))
    logger.info(f"📁 Moved to in_progress: {bug_file.name}")


# ---------------------------------------------------------------------------
# Queue Processing
# ---------------------------------------------------------------------------
def process_bug_queue():
    """
    Process all new bug files in data/bug_queue/.
    """
    if not QUEUE_DIR.exists():
        logger.warning(f"Queue directory not found: {QUEUE_DIR}")
        return
    
    # Find all bug_*.json files (not in subdirectories)
    bug_files = list(QUEUE_DIR.glob("bug_*.json"))
    
    if not bug_files:
        logger.debug("No pending bugs in queue")
        return
    
    logger.info(f"📋 Found {len(bug_files)} pending bug(s)")
    
    for bug_file in bug_files:
        try:
            process_single_bug(bug_file)
        except Exception as e:
            logger.error(f"❌ Failed to process {bug_file.name}: {e}", exc_info=True)


def process_single_bug(bug_file: Path):
    """Process a single bug file."""
    logger.info(f"🐛 Processing {bug_file.name}...")
    
    # 1. Backup
    backup_file(bug_file)
    
    # 2. Load bug data
    with open(bug_file, "r", encoding="utf-8") as f:
        bug_data = json.load(f)
    
    ticket_id = bug_data.get("ticket_id", 0)
    user_info = bug_data.get("user", {})
    user_id = user_info.get("id")
    
    # 3. Notify user: analysis started
    if user_id:
        send_to_user(
            user_id,
            f"🔬 <b>Bug #{ticket_id} — Auto-Fix wird vorbereitet</b>\n\n"
            f"VERA analysiert den Code und erstellt einen Fix-Plan.\n"
            f"Du wirst benachrichtigt, sobald es Updates gibt!"
        )
    
    # 4. Create fix briefing
    fix_task_file = create_fix_briefing(bug_data)
    
    if not fix_task_file:
        logger.error(f"Failed to create fix briefing for {bug_file.name}")
        return
    
    # 5. Move to in_progress
    move_to_in_progress(bug_file)
    
    # 6. Notify user: ready for coding agent
    if user_id:
        send_to_user(
            user_id,
            f"✅ <b>Bug #{ticket_id} — Fix-Plan erstellt</b>\n\n"
            f"Der Coding-Agent wird nun den Fix implementieren.\n"
            f"📝 Fix-Briefing: <code>{fix_task_file.name}</code>\n\n"
            f"Bei Rückfragen melde ich mich hier!"
        )
    
    logger.info(f"✅ Bug #{ticket_id} successfully processed")


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
def run_daemon():
    """Main daemon loop."""
    logger.info("🚀 VERA Auto-Fix Agent starting...")
    
    # Load config
    if not load_config():
        logger.error("❌ Configuration failed — exiting")
        return
    
    # Ensure directories exist
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    IN_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    FIX_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Queue directory: {QUEUE_DIR}")
    logger.info(f"⏱️  Poll interval: {POLL_INTERVAL}s")
    logger.info("✅ Daemon ready — watching queue...")
    
    try:
        while True:
            process_bug_queue()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested — stopping daemon")
    except Exception as e:
        logger.error(f"❌ Fatal error in daemon loop: {e}", exc_info=True)


if __name__ == "__main__":
    run_daemon()
