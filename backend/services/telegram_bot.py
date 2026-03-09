"""
VERA Office Telegram Feedback Bot
Empfängt Bug-Reports & Feedback von Usern zur Verbesserung von VERA.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import yaml

# Ensure project root is in path for imports
import sys
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from telegram import Update, BotCommand
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
except ImportError:
    raise ImportError("python-telegram-bot nicht installiert: pip install python-telegram-bot")

try:
    import aiohttp
except ImportError:
    raise ImportError("aiohttp nicht installiert: pip install aiohttp")

# Import nur für Fallback (wenn Backend nicht erreichbar)
from backend.services.bug_analyzer import analyze_rule_based
from backend.services.javix_bridge import submit_bug

logger = logging.getLogger("vera.telegram")

# Backend API URL
BACKEND_API_URL = "http://localhost:8000/api/analyze-bug"

# ---------------------------------------------------------------------------
# Bug Analysis (HTTP-Call mit Fallback)
# ---------------------------------------------------------------------------
async def analyze_bug(text: str) -> dict:
    """
    Analysiert Bug via Backend API (HTTP).
    Fallback auf regelbasierte Analyse wenn Backend nicht erreichbar.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                BACKEND_API_URL,
                json={"text": text, "category": "bug"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Bug-Analyse via Backend API: {result.get('module')} ({result.get('analysis_method')})")
                    return result
                else:
                    logger.warning(f"Backend API error {response.status}, nutze Fallback")
                    return analyze_rule_based(text)
    
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning(f"Backend nicht erreichbar ({e}), nutze regelbasierten Fallback")
        return analyze_rule_based(text)
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Bug-Analyse: {e}")
        return analyze_rule_based(text)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "vera.yaml"
DB_PATH = Path(__file__).parent.parent.parent / "data" / "feedback.db"

# Boris' Telegram ID – wird beim ersten /admin Befehl gesetzt
ADMIN_IDS: set[int] = set()


def load_token() -> str:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    token = cfg.get("telegram", {}).get("bot_token", "")
    if not token:
        raise ValueError("Kein Telegram bot_token in vera.yaml gefunden")
    return token


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def init_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER,
            username TEXT,
            first_name TEXT,
            category TEXT DEFAULT 'bug',
            message TEXT NOT NULL,
            media_path TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            replies TEXT DEFAULT '[]'
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            telegram_user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_at TEXT NOT NULL
        )
    """)
    db.commit()
    # Load admins
    for row in db.execute("SELECT telegram_user_id FROM admins"):
        ADMIN_IDS.add(row[0])
    db.close()


def save_feedback(user_id: int, username: str, first_name: str,
                  message: str, category: str = "bug", media_path: str = None) -> int:
    db = sqlite3.connect(str(DB_PATH))
    cur = db.execute(
        "INSERT INTO feedback (telegram_user_id, username, first_name, category, message, media_path, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, first_name, category, message, media_path,
         datetime.now().isoformat())
    )
    ticket_id = cur.lastrowid
    db.commit()
    db.close()
    return ticket_id


def get_open_tickets() -> list[dict]:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT * FROM feedback WHERE status = 'open' ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def resolve_ticket(ticket_id: int) -> bool:
    db = sqlite3.connect(str(DB_PATH))
    cur = db.execute(
        "UPDATE feedback SET status = 'resolved', resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), ticket_id)
    )
    db.commit()
    ok = cur.rowcount > 0
    db.close()
    return ok


def get_stats() -> dict:
    db = sqlite3.connect(str(DB_PATH))
    total = db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    open_count = db.execute("SELECT COUNT(*) FROM feedback WHERE status = 'open'").fetchone()[0]
    resolved = db.execute("SELECT COUNT(*) FROM feedback WHERE status = 'resolved'").fetchone()[0]
    db.close()
    return {"total": total, "open": open_count, "resolved": resolved}


def add_reply_to_ticket(ticket_id: int, reply_text: str, user_info: dict) -> bool:
    """Add user reply to ticket and update fix_task JSON if exists."""
    db = sqlite3.connect(str(DB_PATH))
    
    # Get current replies
    row = db.execute("SELECT replies FROM feedback WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        db.close()
        return False
    
    replies = json.loads(row[0] or "[]")
    replies.append({
        "timestamp": datetime.now().isoformat(),
        "text": reply_text,
        "user": user_info
    })
    
    # Update feedback DB
    db.execute(
        "UPDATE feedback SET replies = ? WHERE id = ?",
        (json.dumps(replies), ticket_id)
    )
    db.commit()
    db.close()
    
    # Update fix_task JSON if exists
    fix_tasks_dir = Path(__file__).parent.parent.parent / "data" / "bug_queue" / "fix_tasks"
    if fix_tasks_dir.exists():
        # Find matching fix_task file (format: fix_task_NNNN_timestamp.json)
        pattern = f"fix_task_{ticket_id:04d}_*.json"
        task_files = list(fix_tasks_dir.glob(pattern))
        
        for task_file in task_files:
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task_data = json.load(f)
                
                if "user_replies" not in task_data:
                    task_data["user_replies"] = []
                
                task_data["user_replies"].append({
                    "timestamp": datetime.now().isoformat(),
                    "text": reply_text,
                    "user": user_info
                })
                
                with open(task_file, "w", encoding="utf-8") as f:
                    json.dump(task_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Updated fix_task file: {task_file.name}")
            except Exception as e:
                logger.error(f"Failed to update {task_file}: {e}")
    
    return True


# ---------------------------------------------------------------------------
# Bot Handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Willkommen beim VERA Office Feedback-Bot!\n\n"
        "Hier kannst du Fehler melden und Verbesserungsvorschläge einreichen.\n\n"
        "📝 Einfach eine Nachricht schreiben — Text, Foto oder Screenshot.\n"
        "🏷️ Nutze /bug oder /feature vor deiner Nachricht für die Kategorie.\n\n"
        "Befehle:\n"
        "/bug <Text> — Fehler melden\n"
        "/feature <Text> — Verbesserung vorschlagen\n"
        "/status — Deine offenen Meldungen\n"
        "/help — Diese Hilfe"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_bug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Bitte beschreibe den Fehler: /bug <Beschreibung>")
        return
    ticket_id = save_feedback(
        update.effective_user.id,
        update.effective_user.username or "",
        update.effective_user.first_name or "",
        text, category="bug"
    )
    # VERA LLM analysiert den Bug
    await update.message.reply_text(f"🐛 Bug #{ticket_id} erfasst. VERA analysiert...")
    analysis = analyze_bug(text)
    user_info = {"id": update.effective_user.id, "username": update.effective_user.username,
                 "name": update.effective_user.first_name}
    queue_path = submit_bug(analysis, text, ticket_id, user_info=user_info)

    # Feedback an User
    method = "🤖 KI" if analysis.get("analysis_method") == "llm" else "📋 Regel"
    await update.message.reply_text(
        f"✅ Analyse fertig ({method}):\n\n"
        f"📦 Modul: {analysis.get('module', '?')}\n"
        f"🔴 Severity: {analysis.get('severity', '?')}\n"
        f"📝 {analysis.get('title', text[:60])}\n\n"
        f"→ Wird automatisch an das Entwicklungsteam weitergeleitet."
    )
    await notify_admins(context, ticket_id, "bug", text, update.effective_user,
                        analysis=analysis)


async def cmd_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Bitte beschreibe den Vorschlag: /feature <Beschreibung>")
        return
    ticket_id = save_feedback(
        update.effective_user.id,
        update.effective_user.username or "",
        update.effective_user.first_name or "",
        text, category="feature"
    )
    await update.message.reply_text(
        f"💡 Feature-Request #{ticket_id} erfasst. Danke!"
    )
    await notify_admins(context, ticket_id, "feature", text, update.effective_user)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id, category, message, status, created_at FROM feedback "
        "WHERE telegram_user_id = ? ORDER BY created_at DESC LIMIT 10",
        (update.effective_user.id,)
    ).fetchall()
    db.close()

    if not rows:
        await update.message.reply_text("Du hast noch keine Meldungen eingereicht.")
        return

    lines = ["📋 Deine letzten Meldungen:\n"]
    for r in rows:
        icon = "🐛" if r["category"] == "bug" else "💡"
        status_icon = "🟢" if r["status"] == "resolved" else "🟡"
        lines.append(f"{icon} #{r['id']} {status_icon} {r['message'][:60]}")
    await update.message.reply_text("\n".join(lines))


# Admin commands
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register as admin (first user gets admin, or existing admin adds others)."""
    user_id = update.effective_user.id
    if not ADMIN_IDS:
        # First admin
        ADMIN_IDS.add(user_id)
        db = sqlite3.connect(str(DB_PATH))
        db.execute("INSERT OR REPLACE INTO admins VALUES (?, ?, ?)",
                    (user_id, update.effective_user.username, datetime.now().isoformat()))
        db.commit()
        db.close()
        await update.message.reply_text("✅ Du bist jetzt Admin!")
    elif user_id in ADMIN_IDS:
        await update.message.reply_text("Du bist bereits Admin.")
    else:
        await update.message.reply_text("⛔ Nur bestehende Admins können neue Admins hinzufügen.")


async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Nur für Admins.")
        return
    tickets = get_open_tickets()
    if not tickets:
        await update.message.reply_text("✅ Keine offenen Tickets!")
        return
    lines = [f"📋 {len(tickets)} offene Tickets:\n"]
    for t in tickets:
        icon = "🐛" if t["category"] == "bug" else "💡"
        lines.append(f"{icon} #{t['id']} @{t['username'] or t['first_name']} — {t['message'][:50]}")
    await update.message.reply_text("\n".join(lines))


async def cmd_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Nur für Admins.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /resolve <ticket_id>")
        return
    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Ungültige Ticket-ID.")
        return
    if resolve_ticket(ticket_id):
        await update.message.reply_text(f"✅ Ticket #{ticket_id} als gelöst markiert.")
    else:
        await update.message.reply_text(f"❌ Ticket #{ticket_id} nicht gefunden.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Nur für Admins.")
        return
    s = get_stats()
    await update.message.reply_text(
        f"📊 Feedback-Statistik:\n"
        f"Gesamt: {s['total']}\n"
        f"🟡 Offen: {s['open']}\n"
        f"🟢 Gelöst: {s['resolved']}"
    )


# Reply Handler: User antwortet auf Bot-Nachricht
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user replies to bot messages (e.g., answering questions about a bug)."""
    reply_to = update.message.reply_to_message
    
    # Check if reply is to bot
    if not reply_to or not reply_to.from_user.is_bot:
        # Not a reply to bot → treat as new bug report
        await handle_message(update, context)
        return
    
    # Extract ticket ID from bot message (format: "Bug #1234" or "Ticket #1234")
    import re
    bot_text = reply_to.text or ""
    match = re.search(r"(?:Bug|Ticket)\s*#(\d+)", bot_text)
    
    if not match:
        await update.message.reply_text(
            "⚠️ Konnte keine Ticket-Nummer in der ursprünglichen Nachricht finden.\n"
            "Bitte sende deine Antwort als neue Nachricht oder nutze /bug."
        )
        return
    
    ticket_id = int(match.group(1))
    reply_text = update.message.text or update.message.caption or ""
    
    user_info = {
        "id": update.effective_user.id,
        "username": update.effective_user.username,
        "name": update.effective_user.first_name
    }
    
    # Save reply to DB and fix_task JSON
    success = add_reply_to_ticket(ticket_id, reply_text, user_info)
    
    if success:
        await update.message.reply_text(
            f"✅ Deine Antwort zu Bug #{ticket_id} wurde gespeichert.\n\n"
            f"Das Entwicklungsteam wird sie bei der Behebung berücksichtigen!"
        )
        # Notify admins
        await notify_admins(
            context, ticket_id, "reply", reply_text,
            update.effective_user, is_reply=True
        )
    else:
        await update.message.reply_text(
            f"❌ Bug #{ticket_id} nicht gefunden.\n"
            f"Möglicherweise wurde es bereits gelöst oder die Nummer ist falsch."
        )


# Catch-all: freie Nachrichten als Bug behandeln
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a reply to bot message
    if update.message.reply_to_message:
        await handle_reply(update, context)
        return
    
    text = update.message.text or update.message.caption or ""
    if not text.strip():
        await update.message.reply_text("Bitte beschreibe das Problem als Text.")
        return

    media_path = None
    # Foto speichern
    if update.message.photo:
        photo = update.message.photo[-1]  # Höchste Auflösung
        file = await context.bot.get_file(photo.file_id)
        media_dir = DB_PATH.parent / "feedback_media"
        media_dir.mkdir(exist_ok=True)
        media_path = str(media_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.file_id[:8]}.jpg")
        await file.download_to_drive(media_path)

    ticket_id = save_feedback(
        update.effective_user.id,
        update.effective_user.username or "",
        update.effective_user.first_name or "",
        text, category="bug", media_path=media_path
    )
    await update.message.reply_text(f"🐛 Bug #{ticket_id} erfasst. VERA analysiert...")

    # VERA LLM analysiert den Bug
    analysis = await analyze_bug(text)
    user_info = {"id": update.effective_user.id, "username": update.effective_user.username,
                 "name": update.effective_user.first_name}
    queue_path = submit_bug(analysis, text, ticket_id, user_info=user_info, media_path=media_path)

    method = "🤖 KI" if analysis.get("analysis_method") == "llm" else "📋 Regel"
    await update.message.reply_text(
        f"✅ Analyse fertig ({method}):\n\n"
        f"📦 Modul: {analysis.get('module', '?')}\n"
        f"🔴 Severity: {analysis.get('severity', '?')}\n"
        f"📝 {analysis.get('title', text[:60])}\n\n"
        f"→ Wird automatisch an das Entwicklungsteam weitergeleitet."
    )
    await notify_admins(context, ticket_id, "bug", text, update.effective_user,
                        has_media=media_path is not None, analysis=analysis)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foto ohne Text → Screenshot-Bug-Report"""
    await handle_message(update, context)


# ---------------------------------------------------------------------------
# Admin Notification
# ---------------------------------------------------------------------------
async def notify_admins(context: ContextTypes.DEFAULT_TYPE, ticket_id: int,
                        category: str, text: str, user, has_media: bool = False,
                        analysis: dict = None, is_reply: bool = False):
    if is_reply:
        msg = (
            f"💬 User-Antwort zu Bug #{ticket_id}\n\n"
            f"Von: {user.first_name} (@{user.username or 'n/a'})\n"
            f"Antwort: {text[:300]}"
        )
    else:
        icon = "🐛" if category == "bug" else "💡"
        media_hint = " 📷" if has_media else ""
        msg = (
            f"🔔 Neues Feedback{media_hint}\n\n"
            f"{icon} #{ticket_id} ({category})\n"
            f"Von: {user.first_name} (@{user.username or 'n/a'})\n"
            f"Text: {text[:200]}"
        )
    if analysis:
        method = "KI" if analysis.get("analysis_method") == "llm" else "Regel"
        msg += (
            f"\n\n🔬 Analyse ({method}):\n"
            f"📦 Modul: {analysis.get('module', '?')}\n"
            f"🔴 Severity: {analysis.get('severity', '?')}\n"
            f"💡 Ursache: {analysis.get('possible_cause', '?')[:100]}\n"
            f"📁 Dateien: {', '.join(analysis.get('affected_files', [])[:3])}\n"
            f"🔧 Hinweis: {analysis.get('fix_hint', '?')[:100]}"
        )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=msg)
        except Exception as e:
            logger.error(f"Admin-Notification fehlgeschlagen für {admin_id}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("VERA Office Feedback Bot starting...")

    init_db()
    token = load_token()

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("bug", cmd_bug))
    app.add_handler(CommandHandler("feature", cmd_feature))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("resolve", cmd_resolve))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # Photos (with or without caption)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ready — polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
