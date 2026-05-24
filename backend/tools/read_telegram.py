"""
VERA Office - Telegram Chat Reader
Liest die letzten Nachrichten des Telegram-Bots via getUpdates API.
Lädt Token aus config/vera.yaml (oder TOKEN-Umgebungsvariable).
Bilder/Screenshots werden in data/telegram_downloads/ gespeichert.

Verwendung:
    python backend/tools/read_telegram.py
    python backend/tools/read_telegram.py --limit 20
    python backend/tools/read_telegram.py --token 123456:ABC-DEF
"""

import json
import os
import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Projekt-Root für Imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Config laden
# ---------------------------------------------------------------------------
def load_token_from_yaml() -> tuple[str, str]:
    """Lädt bot_token und chat_id aus config/vera.yaml."""
    config_path = PROJECT_ROOT / "config" / "vera.yaml"
    if not config_path.exists():
        return "", ""
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        tg = cfg.get("telegram", {})
        return tg.get("bot_token", ""), tg.get("chat_id", "")
    except Exception as e:
        print(f"[WARN] vera.yaml nicht lesbar: {e}")
        return "", ""


def get_token(cli_token: str = None) -> str:
    """Gibt Token zurück: CLI > Umgebungsvariable > vera.yaml."""
    if cli_token:
        return cli_token
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if env_token:
        return env_token
    yaml_token, _ = load_token_from_yaml()
    return yaml_token


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------
def api_request(token: str, method: str, params: dict = None) -> dict:
    """Führt einen Telegram Bot API Request aus."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "description": str(e)}


def download_file(token: str, file_id: str, dest_dir: Path) -> str | None:
    """Lädt eine Datei (Foto, Dokument) vom Telegram-Server herunter."""
    # Schritt 1: file_path vom Server holen
    result = api_request(token, "getFile", {"file_id": file_id})
    if not result.get("ok"):
        print(f"  [WARN] getFile fehlgeschlagen: {result.get('description')}")
        return None
    file_path = result["result"]["file_path"]

    # Schritt 2: Datei herunterladen
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    ext = Path(file_path).suffix or ".bin"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_name = f"tg_{timestamp}_{file_id[:8]}{ext}"
    local_path = dest_dir / local_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, local_path)
        return str(local_path)
    except Exception as e:
        print(f"  [WARN] Download fehlgeschlagen: {e}")
        return None


# ---------------------------------------------------------------------------
# Nachrichten parsen und ausgeben
# ---------------------------------------------------------------------------
def format_message(update: dict, token: str, download: bool, dest_dir: Path) -> str:
    """Formatiert ein Update für die Konsolenausgabe."""
    msg = update.get("message") or update.get("edited_message") or {}
    if not msg:
        return f"[Update {update.get('update_id')} - kein message-Feld]"

    update_id = update.get("update_id", "?")
    user = msg.get("from", {})
    username = user.get("username", "")
    first_name = user.get("first_name", "")
    user_id = user.get("id", "?")
    chat = msg.get("chat", {})
    chat_id = chat.get("id", "?")
    chat_type = chat.get("type", "?")
    date_ts = msg.get("date", 0)
    try:
        date_str = datetime.utcfromtimestamp(date_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        date_str = str(date_ts)

    text = msg.get("text") or msg.get("caption") or ""

    lines = [
        f" Update #{update_id} ",
        f"  Zeitpunkt : {date_str}",
        f"  Von       : {first_name} (@{username}) [ID: {user_id}]",
        f"  Chat      : {chat_id} ({chat_type})",
    ]

    if text:
        lines.append(f"  Text      : {text[:500]}")
        if len(text) > 500:
            lines.append(f"              ... [{len(text)} Zeichen gesamt]")

    # Fotos
    photos = msg.get("photo", [])
    if photos:
        lines.append(f"  Foto      : {len(photos)} Auflösungen")
        if download:
            best = photos[-1]  # höchste Auflösung
            local = download_file(token, best["file_id"], dest_dir)
            if local:
                lines.append(f"  Gespeichert: {local}")

    # Dokumente
    doc = msg.get("document")
    if doc:
        lines.append(f"  Dokument  : {doc.get('file_name', '?')} ({doc.get('mime_type', '?')})")
        if download:
            local = download_file(token, doc["file_id"], dest_dir)
            if local:
                lines.append(f"  Gespeichert: {local}")

    # Sticker
    sticker = msg.get("sticker")
    if sticker:
        lines.append(f"  Sticker   : {sticker.get('emoji', '')} {sticker.get('set_name', '')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------
def read_telegram_messages(token: str = None, limit: int = 10,
                            download: bool = True, offset: int = None) -> list[dict]:
    """
    Liest die letzten Nachrichten via getUpdates.
    Gibt die Updates als Liste zurück.
    """
    resolved_token = get_token(token)
    if not resolved_token:
        print("FEHLER: Kein Telegram Bot-Token gefunden!")
        print("Optionen:")
        print("  1. Token in config/vera.yaml unter telegram.bot_token eintragen")
        print("  2. Umgebungsvariable TELEGRAM_BOT_TOKEN setzen")
        print("  3. --token DEIN_TOKEN als Argument übergeben")
        return []

    dest_dir = PROJECT_ROOT / "data" / "telegram_downloads"
    params = {"limit": str(limit)}
    if offset is not None:
        params["offset"] = str(offset)

    print(f"\nLade Updates von Telegram (limit={limit})...")
    result = api_request(resolved_token, "getUpdates", params)

    if not result.get("ok"):
        print(f"FEHLER: {result.get('description', 'Unbekannter Fehler')}")
        print("\nMögliche Ursachen:")
        print("  - Token ungültig oder abgelaufen")
        print("  - Kein Internetzugang")
        print("  - Bot wurde noch nicht gestartet (kein Update-Konflikt mit Webhook)")
        return []

    updates = result.get("result", [])
    if not updates:
        print("Keine neuen Nachrichten vorhanden.")
        print("(Bot-Updates werden nur angezeigt wenn jemand dem Bot geschrieben hat)")
        return []

    print(f"\n{len(updates)} Update(s) gefunden:\n")
    for update in updates:
        print(format_message(update, resolved_token, download, dest_dir))

    # Chat-IDs zusammenfassen (nützlich für Konfiguration)
    print("\n Chat-ID Übersicht ")
    seen_chats: set[str] = set()
    for update in updates:
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type", "?")
        if chat_id and chat_id not in seen_chats:
            seen_chats.add(chat_id)
            title = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
            print(f"  chat_id: {chat_id}  ({chat_type})  {title}")

    print()
    return updates


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERA Telegram Chat Reader")
    parser.add_argument("--token", default=None, help="Bot-Token (überschreibt vera.yaml)")
    parser.add_argument("--limit", type=int, default=10, help="Anzahl Updates (max 100)")
    parser.add_argument("--no-download", action="store_true", help="Fotos nicht herunterladen")
    parser.add_argument("--offset", type=int, default=None, help="Update-Offset (für Paging)")
    args = parser.parse_args()

    # Bot-Info anzeigen
    resolved_token = get_token(args.token)
    if resolved_token:
        info = api_request(resolved_token, "getMe")
        if info.get("ok"):
            bot = info["result"]
            print(f"\nBot: @{bot.get('username')} [{bot.get('first_name')}]")
            print(f"ID : {bot.get('id')}")

    read_telegram_messages(
        token=args.token,
        limit=args.limit,
        download=not args.no_download,
        offset=args.offset,
    )
