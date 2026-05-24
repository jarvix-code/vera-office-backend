"""
VERA Lehrbuch-Scheduler Service
Laeuft im FastAPI-Lifespan als asyncio-Background-Task.
Verarbeitet neue Lehrbuch-Dokumente periodisch (alle 24h).
Bug #59 Fix: 2026-04-19
"""
import asyncio
import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

log = logging.getLogger("lehrbuch_scheduler")

# Verarbeitungs-Intervall in Sekunden (24h)
SCHEDULER_INTERVAL_SEC = 24 * 60 * 60
# Start-Delay nach Service-Start (30s)
INITIAL_DELAY_SEC = 30

LEHRBUCH_FN_KEYWORDS = [
    "lehrbuch", "skript", "handbuch", "leitfaden", "kurs",
    "anleitung", "schulung", "training", "strahlenschutz",
    "grundlagen", "richtlinie",
]
LEHRBUCH_TX_KEYWORDS = [
    "kapitel", "abschnitt", "lernziel", "zusammenfassung", "definition",
    "grundlagen", "hygiene", "qm-handbuch", "qualitaetsmanagement",
    "kurs", "schulung",
]


def _is_lehrbuch(filename: str, ocr_text: str) -> bool:
    fn = (filename or "").lower()
    tx = (ocr_text or "").lower()
    for kw in LEHRBUCH_FN_KEYWORDS:
        if kw in fn:
            return True
    return sum(1 for kw in LEHRBUCH_TX_KEYWORDS if kw in tx) >= 3


def _simple_extract(text: str) -> list:
    """Regelbasierte S-P-O Extraktion als Fallback ohne LLM."""
    triples = []
    patterns = [
        r"(?P<s>[A-ZÄÖÜ][^,\n]{3,40})\s+(?P<p>beträgt|ist|bedeutet|umfasst)\s+(?P<o>[^.!?\n]{5,100})",
        r"(?P<s>[A-ZÄÖÜ][^,\n]{3,40})\s+(?P<p>muss|soll|darf|wird)\s+(?P<o>[^.!?\n]{5,100})",
        r"(?:gemäß|nach|laut)\s+(?P<s>[A-ZÄÖÜ§][^\s,]{2,30})\s+(?P<p>gilt|beträgt|ist)\s+(?P<o>[^.!?\n]{5,80})",
    ]
    for sent in re.split(r"[.!?]\s+", text)[:50]:
        for pat in patterns:
            m = re.search(pat, sent, re.IGNORECASE)
            if m:
                s, p, o = m.group("s").strip(), m.group("p").strip(), m.group("o").strip()
                if len(s) >= 3 and len(o) >= 5:
                    triples.append({"subject": s, "predicate": p, "object": o[:200]})
                    break
    return triples[:20]


def _try_llm_extract(chunk: str) -> list:
    """S-P-O via LLM (optional). Gibt [] wenn LLM nicht verfuegbar."""
    try:
        from backend.core.ai.llm_manager import llm  # noqa: F401
        prompt = (
            "Extrahiere die 3-5 wichtigsten Aussagen als JSON-Array.\n"
            'Format: [{"subject":"...","predicate":"...","object":"..."}]\n'
            "Nur JSON, kein Text. Text: " + chunk[:3000]
        )
        resp = None
        try:
            resp = llm.generate(prompt, max_tokens=600, temperature=0.1)
        except Exception:
            try:
                resp = llm.generate_fast(prompt, max_tokens=600, temperature=0.1)
            except Exception:
                pass
        if resp:
            m = re.search(r"\[.*?\]", resp, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                result = []
                for item in data:
                    if isinstance(item, dict):
                        s = str(item.get("subject", "")).strip()
                        p = str(item.get("predicate", "")).strip()
                        o = str(item.get("object", "")).strip()
                        if s and p and o:
                            result.append({"subject": s, "predicate": p, "object": o})
                return result[:20]
    except Exception:
        pass
    return []


def _store_triples(triples: list, source: str, brain_db: Path, confidence: float = 0.85) -> int:
    if not triples:
        return 0
    conn = sqlite3.connect(str(brain_db))
    now = datetime.utcnow().isoformat()
    stored = 0
    for t in triples:
        try:
            if not conn.execute(
                "SELECT id FROM facts WHERE category=? AND key=? AND source=?",
                ("lehrbuch", t["subject"], source),
            ).fetchone():
                conn.execute(
                    "INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    ("lehrbuch", t["subject"], f"{t['predicate']} {t['object']}", source, confidence, now, now),
                )
                stored += 1
        except Exception as e:
            log.warning("Fact store failed: %s", e)
    conn.commit()
    conn.close()
    return stored


def _process_one(doc_id: int, filename: str, ocr_text: str, brain_db: Path) -> int:
    source = f"lehrbuch:{filename}"
    total = 0
    for i in range(0, min(len(ocr_text), 30000), 3000):
        chunk = ocr_text[i : i + 3000].strip()
        if len(chunk) < 100:
            continue
        triples = _try_llm_extract(chunk) or _simple_extract(chunk)
        total += _store_triples(triples, source, brain_db)
        if total >= 200:
            break
    log.info("Doc #%d %s: %d facts stored", doc_id, filename[:40], total)
    return total


def run_learner_cycle(vera_db: Path, brain_db: Path) -> dict:
    """
    Einmalige Verarbeitungs-Runde: Alle neuen Lehrbuch-Docs -> Brain.
    Gibt Stats-Dict zurueck.
    """
    # Bereits verarbeitete Sources
    bconn = sqlite3.connect(str(brain_db))
    done = set(
        r[0]
        for r in bconn.execute(
            "SELECT DISTINCT source FROM facts WHERE source LIKE 'lehrbuch:%'"
        ).fetchall()
    )
    bconn.close()

    # Docs mit OCR-Text laden
    vconn = sqlite3.connect(str(vera_db))
    rows = vconn.execute(
        "SELECT id, filename, ocr_text FROM documents "
        "WHERE ocr_text IS NOT NULL AND LENGTH(ocr_text) > 200"
    ).fetchall()
    vconn.close()

    new_docs = [
        (did, fn, tx)
        for did, fn, tx in rows
        if f"lehrbuch:{fn}" not in done and _is_lehrbuch(fn, tx)
    ]

    log.info("Lehrbuch-Cycle: %d neue Docs gefunden", len(new_docs))
    total_facts = 0
    for doc_id, filename, ocr_text in new_docs:
        total_facts += _process_one(doc_id, filename, ocr_text, brain_db)

    return {"docs_processed": len(new_docs), "facts_stored": total_facts}


async def start_lehrbuch_scheduler(vera_db: Path, brain_db: Path) -> None:
    """
    Async-Background-Task fuer den Lehrbuch-Scheduler.
    Wird via asyncio.create_task im lifespan gestartet.
    """
    log.info("Lehrbuch-Scheduler gestartet (Interval: %dh)", SCHEDULER_INTERVAL_SEC // 3600)
    await asyncio.sleep(INITIAL_DELAY_SEC)

    while True:
        try:
            # Fix Bug: asyncio.to_thread prevents blocking the event loop during LLM inference
            stats = await asyncio.to_thread(run_learner_cycle, vera_db, brain_db)
            log.info(
                "Lehrbuch-Cycle abgeschlossen: %d Docs, %d Facts",
                stats["docs_processed"],
                stats["facts_stored"],
            )
        except Exception as e:
            log.error("Lehrbuch-Scheduler Fehler: %s", e)

        await asyncio.sleep(SCHEDULER_INTERVAL_SEC)
