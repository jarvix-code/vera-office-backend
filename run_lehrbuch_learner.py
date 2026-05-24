#!/usr/bin/env python3
"""
VERA Lehrbuch-Scheduler
Verarbeitet alle Dokumente mit OCR-Text und speichert S-P-O Tripel in vera_brain.db.
Wird woechentlich via systemd-Timer aufgerufen.

Aufruf: python3 /opt/vera-office/run_lehrbuch_learner.py [--doc-id ID] [--all] [--dry-run]
"""
import sys
import json
import sqlite3
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Pfade
BASE_DIR = Path("/opt/vera-office")
VERA_DB  = BASE_DIR / "data" / "vera.db"
BRAIN_DB = BASE_DIR / "data" / "vera_brain.db"
LOG_FILE = BASE_DIR / "logs" / "lehrbuch_learner.log"

# Logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("lehrbuch_learner_scheduler")

# ─── Lehrbuch-Erkennung ────────────────────────────────────────────────────
LEHRBUCH_KEYWORDS = [
    "kapitel", "abschnitt", "lernziel", "zusammenfassung", "definition",
    "fachbegriff", "grundlagen", "einfuehrung", "inhalt", "literatur",
    "qm-handbuch", "qualitaetsmanagement", "strahlenschutz", "hygiene",
    "kurs", "schulung", "leitfaden", "handbuch", "richtlinie",
]
LEHRBUCH_FN_KEYWORDS = [
    "lehrbuch", "skript", "handbuch", "leitfaden", "kurs",
    "anleitung", "schulung", "training", "strahlenschutz",
]


def is_lehrbuch(filename: str, ocr_text: str) -> bool:
    """Heuristik: Ist dieses Dokument ein Lehrbuch/Fachliteratur?"""
    fn = (filename or "").lower()
    tx = (ocr_text or "").lower()
    for kw in LEHRBUCH_FN_KEYWORDS:
        if kw in fn:
            return True
    hits = sum(1 for kw in LEHRBUCH_KEYWORDS if kw in tx)
    return hits >= 3


# ─── S-P-O Regelextraktion (Fallback ohne LLM) ────────────────────────────
def simple_extract_triples(text: str) -> list:
    """Regelbasierte S-P-O Extraktion als Fallback."""
    triples = []
    sentences = re.split(r"[.!?]\s+", text)
    patterns = [
        (r"(?P<s>[A-ZÄÖÜ][^,\n]{3,40})\s+(?P<p>betraegt|beträgt|ist|bedeutet|bezeichnet|umfasst)\s+(?P<o>[^.!?\n]{5,100})"),
        (r"(?P<s>[A-ZÄÖÜ][^,\n]{3,40})\s+(?P<p>muss|soll|darf|kann|wird)\s+(?P<o>[^.!?\n]{5,100})"),
        (r"(?:gemaess|gemäß|nach|laut)\s+(?P<s>[A-ZÄÖÜ§][^\s,]{2,30})\s+(?P<p>gilt|betraegt|beträgt|ist)\s+(?P<o>[^.!?\n]{5,80})"),
    ]
    for sent in sentences[:50]:
        for pat in patterns:
            m = re.search(pat, sent, re.IGNORECASE)
            if m:
                s = m.group("s").strip()
                p = m.group("p").strip()
                o = m.group("o").strip()
                if len(s) >= 3 and len(o) >= 5:
                    triples.append({"subject": s, "predicate": p, "object": o[:200]})
                    break
    return triples[:20]


# ─── LLM-Extraktion (optional) ────────────────────────────────────────────
def try_llm_extract(chunk: str) -> list:
    """Versucht S-P-O Extraktion via lokalem LLM (Mistral/Qwen). Gibt [] bei Fehler."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from backend.core.ai.llm_manager import llm  # noqa: F401
        prompt = (
            "Extrahiere die 3-5 wichtigsten Aussagen aus folgendem Text als JSON-Array.\n"
            'Jede Aussage als: {"subject": "...", "predicate": "...", "object": "..."}\n'
            "Antworte NUR mit dem JSON-Array, kein erklaerenden Text.\n"
            "Text: " + chunk[:3000]
        )
        response = None
        try:
            response = llm.generate(prompt, max_tokens=800, temperature=0.1)
        except Exception:
            try:
                response = llm.generate_fast(prompt, max_tokens=800, temperature=0.1)
            except Exception:
                pass
        if response:
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                result = []
                for item in data:
                    if isinstance(item, dict):
                        s = str(item.get("subject", "")).strip()
                        p = str(item.get("predicate", "")).strip()
                        o = str(item.get("object", "")).strip()
                        if s and p and o:
                            result.append({"subject": s, "predicate": p, "object": o})
                return result[:20]
    except Exception as e:
        log.debug("LLM nicht verfuegbar: %s — Fallback auf Regelextraktion", e)
    return []


# ─── Brain-Speicherung ─────────────────────────────────────────────────────
def store_triples(triples: list, source: str, confidence: float = 0.85) -> int:
    """Speichert Tripel direkt in vera_brain.db (facts-Tabelle)."""
    if not triples:
        return 0
    conn = sqlite3.connect(str(BRAIN_DB))
    now = datetime.utcnow().isoformat()
    stored = 0
    for t in triples:
        try:
            exists = conn.execute(
                "SELECT id FROM facts WHERE category=? AND key=? AND source=?",
                ("lehrbuch", t["subject"], source),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        "lehrbuch",
                        t["subject"],
                        f"{t['predicate']} {t['object']}",
                        source,
                        confidence,
                        now,
                        now,
                    ),
                )
                stored += 1
        except Exception as e:
            log.warning("Fact-Speicherung fehlgeschlagen: %s", e)
    conn.commit()
    conn.close()
    return stored


# ─── Dokument verarbeiten ──────────────────────────────────────────────────
def process_document(doc_id: int, filename: str, ocr_text: str) -> dict:
    """Text → Tripel → Brain-DB."""
    source = f"lehrbuch:{filename}"
    log.info("Verarbeite Doc #%d: %s (%d Zeichen)", doc_id, filename, len(ocr_text))

    # In 3000-Zeichen-Chunks aufteilen (max 30000 Zeichen = 10 Chunks)
    sections = []
    for i in range(0, min(len(ocr_text), 30000), 3000):
        chunk = ocr_text[i : i + 3000].strip()
        if len(chunk) >= 100:
            sections.append(chunk)

    total_stored = 0
    for i, chunk in enumerate(sections):
        triples = try_llm_extract(chunk)
        if not triples:
            triples = simple_extract_triples(chunk)
        log.debug("  Chunk %d/%d: %d Tripel", i + 1, len(sections), len(triples))
        total_stored += store_triples(triples, source)
        if total_stored >= 200:
            log.warning("Limit 200 Fakten erreicht fuer %s", filename)
            break

    log.info("  -> %d Fakten gespeichert", total_stored)
    return {"doc_id": doc_id, "filename": filename, "facts_stored": total_stored}


# ─── Unverarbeitete Docs laden ─────────────────────────────────────────────
def get_docs_to_process(only_id: int = None, force_all: bool = False) -> list:
    """Holt Docs aus vera.db. Filtert bereits verarbeitete (ausser --all)."""
    conn = sqlite3.connect(str(VERA_DB))
    if only_id:
        rows = conn.execute(
            "SELECT id, filename, ocr_text FROM documents WHERE id=? AND ocr_text IS NOT NULL",
            (only_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, filename, ocr_text FROM documents "
            "WHERE ocr_text IS NOT NULL AND LENGTH(ocr_text) > 200"
        ).fetchall()
    conn.close()

    # Bereits verarbeitete Sources
    bconn = sqlite3.connect(str(BRAIN_DB))
    done_sources = set(
        r[0]
        for r in bconn.execute(
            "SELECT DISTINCT source FROM facts WHERE source LIKE 'lehrbuch:%'"
        ).fetchall()
    )
    bconn.close()

    result = []
    for doc_id, filename, ocr_text in rows:
        source = f"lehrbuch:{filename}"
        if not force_all and source in done_sources and only_id is None:
            continue  # Bereits verarbeitet
        if only_id or force_all or is_lehrbuch(filename, ocr_text):
            result.append((doc_id, filename, ocr_text))
    return result


# ─── Entry Point ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="VERA Lehrbuch-Learner Scheduler")
    parser.add_argument("--doc-id", type=int, help="Nur dieses Dokument verarbeiten")
    parser.add_argument(
        "--all", action="store_true", help="Alle Lehrbuch-Docs (auch bereits verarbeitete)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht speichern")
    args = parser.parse_args()

    log.info("=== VERA Lehrbuch-Learner gestartet %s ===", datetime.now().isoformat())

    docs = get_docs_to_process(only_id=args.doc_id, force_all=args.all)
    if not docs:
        log.info("Keine neuen Lehrbuch-Dokumente zu verarbeiten.")
        return

    log.info("%d Dokument(e) zur Verarbeitung gefunden", len(docs))

    total_facts = 0
    for doc_id, filename, ocr_text in docs:
        if args.dry_run:
            log.info("[DRY-RUN] Wuerde verarbeiten: #%d %s (%d chars)", doc_id, filename, len(ocr_text))
            continue
        result = process_document(doc_id, filename, ocr_text)
        total_facts += result["facts_stored"]

    log.info("=== Fertig: %d Fakten gespeichert ===", total_facts)


if __name__ == "__main__":
    main()
