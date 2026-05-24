"""
VERA Office Telegram Bot
Empfängt Dokumente, Notizen und Feedback von Usern.
- Fotos/PDFs → data/inbox/ (Dokument-Pipeline)
- Textnachrichten → data/notes/ (Notizen)
- /bug /feature → Feedback an Entwicklerteam
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import yaml

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

from backend.services.bug_analyzer import analyze_rule_based
from backend.services.javix_bridge import submit_bug

logger = logging.getLogger("vera.telegram")

BACKEND_API_URL = "http://localhost:8000/api/analyze-bug"

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "vera.yaml"
DB_PATH = Path(__file__).parent.parent.parent / "data" / "feedback.db"
INBOX_DIR = Path(__file__).parent.parent.parent / "data" / "inbox"
NOTES_DIR = Path(__file__).parent.parent.parent / "data" / "notes"

ADMIN_IDS: set[int] = set()

# Global bot application (for lifespan management)
_bot_app: Application = None


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_token() -> str:
    cfg = load_config()
    token = cfg.get("telegram", {}).get("bot_token", "")
    if not token:
        raise ValueError("Kein Telegram bot_token in vera.yaml gefunden")
    return token


def load_chat_id() -> str:
    cfg = load_config()
    return cfg.get("telegram", {}).get("chat_id", "")


def save_chat_id_to_config(chat_id: int):
    """Speichert chat_id dauerhaft in vera.yaml (Auto-Discovery)."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace empty chat_id line
    import re
    new_content = re.sub(
        r'(telegram:\s*\n(?:.*\n)*?.*chat_id:\s*)"[^"]*"',
        f'\\1"{chat_id}"',
        content
    )
    if new_content == content:
        # Fallback: simple line replacement
        new_content = re.sub(
            r'(  chat_id:\s*)""',
            f'\\1"{chat_id}"',
            content
        )

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    logger.info(f"✅ Telegram chat_id gespeichert: {chat_id}")


# ---------------------------------------------------------------------------
# Auto-Discovery
# ---------------------------------------------------------------------------
async def maybe_discover_chat_id(update: Update):
    """Speichert chat_id beim ersten Kontakt automatisch."""
    current = load_chat_id()
    if not current:
        chat_id = update.effective_chat.id
        save_chat_id_to_config(chat_id)
        logger.info(f"Auto-Discovery: chat_id={chat_id} für {update.effective_user.first_name}")
        await update.message.reply_text(
            f"✅ VERA hat deinen Chat registriert!\n"
            f"Chat-ID: {chat_id}\n\n"
            f"Du kannst jetzt Dokumente (Fotos, PDFs) und Notizen senden."
        )


# ---------------------------------------------------------------------------
# Bug Analysis (HTTP-Call mit Fallback)
# ---------------------------------------------------------------------------
async def analyze_bug(text: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                BACKEND_API_URL,
                json={"text": text, "category": "bug"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    return analyze_rule_based(text)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return analyze_rule_based(text)
    except Exception as e:
        logger.error(f"Bug-Analyse Fehler: {e}")
        return analyze_rule_based(text)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    db = sqlite3.connect(str(DB_PATH))
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

    db.execute(
        "UPDATE feedback SET replies = ? WHERE id = ?",
        (json.dumps(replies), ticket_id)
    )
    db.commit()
    db.close()

    fix_tasks_dir = Path(__file__).parent.parent.parent / "data" / "bug_queue" / "fix_tasks"
    if fix_tasks_dir.exists():
        pattern = f"fix_task_{ticket_id:04d}_*.json"
        for task_file in fix_tasks_dir.glob(pattern):
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
            except Exception as e:
                logger.error(f"Failed to update {task_file}: {e}")

    return True


# ---------------------------------------------------------------------------
# Dokument-Handling (→ data/inbox/)
# ---------------------------------------------------------------------------
async def save_photo_to_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Speichert Foto in data/inbox/ für die VERA Dokumenten-Pipeline."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    photo = update.message.photo[-1]  # Höchste Auflösung
    file = await context.bot.get_file(photo.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = INBOX_DIR / f"telegram_{timestamp}_{photo.file_id[:8]}.jpg"
    await file.download_to_drive(str(file_path))
    return str(file_path)


async def save_document_to_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Speichert PDF/Dokument in data/inbox/ für die VERA Dokumenten-Pipeline."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Dateiendung aus Original-Dateiname
    suffix = Path(doc.file_name or "document").suffix or ".bin"
    file_path = INBOX_DIR / f"telegram_{timestamp}_{doc.file_id[:8]}{suffix}"
    await file.download_to_drive(str(file_path))
    return str(file_path)


def save_note(user: object, text: str) -> str:
    """Speichert Textnachricht als Notiz in data/notes/."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    username = getattr(user, "username", None) or getattr(user, "first_name", "unknown")
    note_path = NOTES_DIR / f"telegram_{timestamp}_{username}.txt"
    content = (
        f"# Telegram-Notiz\n"
        f"Von: {getattr(user, 'first_name', '')} (@{username})\n"
        f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{text}\n"
    )
    note_path.write_text(content, encoding="utf-8")
    return str(note_path)


# ---------------------------------------------------------------------------
# Bot Handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await maybe_discover_chat_id(update)
    await update.message.reply_text(
        "👋 Willkommen bei VERA Office!\n\n"
        "📄 Dokument senden: Foto oder PDF schicken → wird automatisch verarbeitet\n"
        "📝 Notiz: Einfach Text schreiben → wird als Notiz gespeichert\n"
        "🐛 Bug melden: /bug <Beschreibung>\n"
        "💡 Vorschlag: /feature <Beschreibung>\n\n"
        "Befehle:\n"
        "/status — Deine offenen Meldungen\n"
        "/help — Diese Hilfe"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_bug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await maybe_discover_chat_id(update)
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
    await update.message.reply_text(f"🐛 Bug #{ticket_id} erfasst. VERA analysiert...")
    analysis = await analyze_bug(text)
    user_info = {"id": update.effective_user.id, "username": update.effective_user.username,
                 "name": update.effective_user.first_name}
    submit_bug(analysis, text, ticket_id, user_info=user_info)
    method = "🤖 KI" if analysis.get("analysis_method") == "llm" else "📋 Regel"
    await update.message.reply_text(
        f"✅ Analyse fertig ({method}):\n\n"
        f"📦 Modul: {analysis.get('module', '?')}\n"
        f"🔴 Severity: {analysis.get('severity', '?')}\n"
        f"📝 {analysis.get('title', text[:60])}\n\n"
        f"→ Wird automatisch an das Entwicklungsteam weitergeleitet."
    )
    await notify_admins(context, ticket_id, "bug", text, update.effective_user, analysis=analysis)


async def cmd_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await maybe_discover_chat_id(update)
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
    await update.message.reply_text(f"💡 Feature-Request #{ticket_id} erfasst. Danke!")
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


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ADMIN_IDS:
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


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foto → data/inbox/ (Dokument-Pipeline)."""
    await maybe_discover_chat_id(update)
    caption = update.message.caption or ""

    file_path = await save_photo_to_inbox(update, context)
    filename = Path(file_path).name

    await update.message.reply_text(
        f"📄 Foto empfangen!\n"
        f"→ VERA verarbeitet das Dokument automatisch.\n"
        f"Datei: {filename}"
        + (f"\nBeschreibung: {caption}" if caption else "")
    )
    logger.info(f"Foto in Inbox gespeichert: {file_path}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alle Dokumente → data/inbox/ (Dokument-Pipeline). Kein Dateifilter."""
    await maybe_discover_chat_id(update)
    doc = update.message.document

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    file = await context.bot.get_file(doc.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = doc.file_name or f"document_{timestamp}.bin"
    file_path = INBOX_DIR / f"telegram_{timestamp}_{original_name}"
    await file.download_to_drive(str(file_path))

    await update.message.reply_text(f"📄 Dokument erhalten: {original_name}")
    logger.info(f"Dokument in Inbox gespeichert: {file_path}")


async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Antwort auf Bot-Nachricht → Ticket-Antwort."""
    reply_to = update.message.reply_to_message
    if not reply_to or not reply_to.from_user.is_bot:
        await handle_message(update, context)
        return

    import re
    bot_text = reply_to.text or ""
    match = re.search(r"(?:Bug|Ticket)\s*#(\d+)", bot_text)

    if not match:
        await handle_message(update, context)
        return

    ticket_id = int(match.group(1))
    reply_text = update.message.text or update.message.caption or ""
    user_info = {
        "id": update.effective_user.id,
        "username": update.effective_user.username,
        "name": update.effective_user.first_name
    }

    success = add_reply_to_ticket(ticket_id, reply_text, user_info)
    if success:
        await update.message.reply_text(
            f"✅ Deine Antwort zu Bug #{ticket_id} wurde gespeichert."
        )
        await notify_admins(context, ticket_id, "reply", reply_text,
                            update.effective_user, is_reply=True)
    else:
        await update.message.reply_text(f"❌ Bug #{ticket_id} nicht gefunden.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Textnachricht → als Notiz speichern."""
    # Reply to bot → ticket reply
    if update.message.reply_to_message:
        await handle_reply(update, context)
        return

    await maybe_discover_chat_id(update)

    text = update.message.text or update.message.caption or ""
    if not text.strip():
        await update.message.reply_text(
            "📝 Schreibe eine Textnachricht als Notiz,\n"
            "oder sende ein Foto/PDF als Dokument."
        )
        return

    note_path = save_note(update.effective_user, text)
    filename = Path(note_path).name

    await update.message.reply_text(
        f"📝 Notiz gespeichert!\n"
        f"Datei: {filename}\n\n"
        f"Tipp: /bug <Text> für Fehlerberichte, /feature <Text> für Vorschläge."
    )
    logger.info(f"Notiz gespeichert: {note_path}")


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
            f"🔧 Hinweis: {analysis.get('fix_hint', '?')[:100]}"
        )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=msg)
        except Exception as e:
            logger.error(f"Admin-Notification fehlgeschlagen für {admin_id}: {e}")


# ---------------------------------------------------------------------------
# Lifespan Integration (Background Thread)
# ---------------------------------------------------------------------------
def start_bot_background() -> threading.Thread:
    """
    Startet den Telegram-Bot in einem Background-Thread.
    Wird von VERA Lifespan (main.py) aufgerufen.
    Returns den Thread (für Join beim Shutdown).
    """
    global _bot_app

    def _run():
        global _bot_app
        logging.basicConfig(level=logging.INFO)
        logger.info("Telegram Bot startet im Background-Thread...")

        init_db()
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        NOTES_DIR.mkdir(parents=True, exist_ok=True)

        try:
            token = load_token()
        except ValueError as e:
            logger.error(f"Telegram Bot: {e}")
            return

        _bot_app = Application.builder().token(token).build()

        _bot_app.add_handler(CommandHandler("start", cmd_start))
        _bot_app.add_handler(CommandHandler("help", cmd_help))
        _bot_app.add_handler(CommandHandler("bug", cmd_bug))
        _bot_app.add_handler(CommandHandler("feature", cmd_feature))
        _bot_app.add_handler(CommandHandler("status", cmd_status))
        _bot_app.add_handler(CommandHandler("admin", cmd_admin))
        _bot_app.add_handler(CommandHandler("tickets", cmd_tickets))
        _bot_app.add_handler(CommandHandler("resolve", cmd_resolve))
        _bot_app.add_handler(CommandHandler("stats", cmd_stats))

        # Documents (PDFs, images as file)
        _bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        # Photos
        _bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        # Text messages
        _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Telegram Bot bereit — polling...")
        _bot_app.run_polling(drop_pending_updates=True)

    thread = threading.Thread(target=_run, name="vera-telegram-bot", daemon=True)
    thread.start()
    return thread


def stop_bot():
    """Stoppt den Bot (wird beim Shutdown aufgerufen)."""
    global _bot_app
    if _bot_app:
        try:
            _bot_app.stop()
        except Exception as e:
            logger.error(f"Bot stop error: {e}")


# ---------------------------------------------------------------------------
# Standalone Main
# ---------------------------------------------------------------------------
def run_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("VERA Office Telegram Bot starting (standalone)...")

    init_db()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    token = load_token()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("bug", cmd_bug))
    app.add_handler(CommandHandler("feature", cmd_feature))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("resolve", cmd_resolve))
    app.add_handler(CommandHandler("stats", cmd_stats))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ready — polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
