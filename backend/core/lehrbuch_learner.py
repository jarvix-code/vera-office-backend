"""
VERA Lehrbuch-Lern-Mechanismus
Zerlegt Lehrbuch/Fachliteratur in Abschnitte und extrahiert S-P-O Tripel via LLM.
"""
import json
import logging
import re
from typing import Optional

log = logging.getLogger("lehrbuch_learner")

# Max Fakten pro Abschnitt
MAX_FACTS_PER_CHUNK = 20
# Max Zeichen pro Abschnitt fuer LLM
MAX_CHUNK_CHARS = 3000
# Min Zeichen fuer einen sinnvollen Abschnitt
MIN_CHUNK_CHARS = 100

_EXTRACT_PROMPT = (
    "Extrahiere die 3-5 wichtigsten Aussagen aus folgendem Text als JSON-Array.\n"
    "Jede Aussage als: {{\"subject\": \"...\", \"predicate\": \"...\", \"object\": \"...\"}}\n"
    "Beispiel: {{\"subject\": \"Aufbewahrungsfrist Rechnungen\", \"predicate\": \"betraegt\","
    " \"object\": \"10 Jahre nach HGB 257\"}}\n"
    "Antworte NUR mit dem JSON-Array, kein erklaerenden Text.\n"
    "Text: {chunk}"
)


def _split_into_sections(text: str) -> list:
    """
    Zerlegt OCR-Text in Abschnitte anhand von Ueberschriften-Mustern.
    Ueberschrift-Muster: Zeile die mit Grossbuchstaben beginnt, Nummer hat, etc.
    """
    # Verschiedene Ueberschriften-Muster
    heading_pattern = re.compile(
        r'(?m)^(?:'
        r'(?:\d+[\.\)]\s)'        # "1. " oder "1) "
        r'|(?:[A-Z][A-Z\s]{3,})'  # "KAPITEL", "ABSCHNITT"
        r'|(?:Kapitel\s+\d+)'     # "Kapitel 3"
        r'|(?:Abschnitt\s+\d+)'   # "Abschnitt 2"
        r'|(?:\d+\.\d+\s)'        # "1.2 "
        r')'
    )

    sections = []
    parts = heading_pattern.split(text)

    for part in parts:
        part = part.strip()
        if len(part) >= MIN_CHUNK_CHARS:
            # Falls Abschnitt zu lang: in MAX_CHUNK_CHARS-Haelften teilen
            if len(part) > MAX_CHUNK_CHARS:
                # Teile an Absatzgrenzen
                paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
                current_chunk = ""
                for para in paragraphs:
                    if len(current_chunk) + len(para) > MAX_CHUNK_CHARS and current_chunk:
                        sections.append(current_chunk)
                        current_chunk = para
                    else:
                        current_chunk = (current_chunk + "\n\n" + para).strip()
                if current_chunk and len(current_chunk) >= MIN_CHUNK_CHARS:
                    sections.append(current_chunk)
            else:
                sections.append(part)

    # Fallback: wenn keine Ueberschriften gefunden, teile nach Absaetzen
    if not sections:
        raw_chunks = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_CHUNK_CHARS]
        # Merge kleine Chunks
        merged = []
        current = ""
        for chunk in raw_chunks:
            if len(current) + len(chunk) > MAX_CHUNK_CHARS and current:
                merged.append(current)
                current = chunk
            else:
                current = (current + "\n\n" + chunk).strip()
        if current:
            merged.append(current)
        sections = merged

    return sections


def _extract_triples_from_chunk(chunk: str, llm) -> list:
    """
    Ruft LLM auf um S-P-O Tripel aus einem Textabschnitt zu extrahieren.
    Gibt Liste von Dicts zurueck: [{subject, predicate, object}]
    """
    prompt = _EXTRACT_PROMPT.format(chunk=chunk[:MAX_CHUNK_CHARS])

    response = None
    try:
        response = llm.generate(prompt, max_tokens=800, temperature=0.1, stop=["</s>", "\n\n\n"])
    except Exception as e:
        log.warning("LLM generate fehlgeschlagen (Mistral): %s", e)

    if not response:
        # Fallback: Qwen fast model
        try:
            response = llm.generate_fast(prompt, max_tokens=800, temperature=0.1)
        except Exception as e:
            log.warning("LLM generate_fast fehlgeschlagen (Qwen): %s", e)

    if not response:
        return []

    # JSON extrahieren
    try:
        # Suche nach JSON-Array in der Antwort
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            triples = []
            for item in data:
                if isinstance(item, dict):
                    s = str(item.get("subject", "")).strip()
                    p = str(item.get("predicate", "")).strip()
                    o = str(item.get("object", "")).strip()
                    if s and p and o and len(s) <= 1000 and len(p) <= 1000 and len(o) <= 1000:
                        triples.append({"subject": s, "predicate": p, "object": o})
            return triples[:MAX_FACTS_PER_CHUNK]
    except (json.JSONDecodeError, Exception) as e:
        log.warning("JSON-Parsing fehlgeschlagen: %s — Antwort: %s", e, response[:200])

    return []


async def extract_and_store_lehrbuch_facts(
    ocr_text: str,
    filename: str,
    confidence: float = 0.9,
) -> dict:
    """
    Extrahiert S-P-O Tripel aus Lehrbuch-Text und speichert in vera_brain.db.
    Wird asynchron aufgerufen nach Lehrbuch-Klassifizierung.
    """
    from backend.core.vera_brain import vera_brain
    from backend.core.ai.llm_manager import llm

    log.info("Lehrbuch-Lernen gestartet: %s (%d Zeichen)", filename, len(ocr_text))

    sections = _split_into_sections(ocr_text)
    log.info("  %d Abschnitte gefunden", len(sections))

    source = f"lehrbuch:{filename}"
    total_stored = 0
    total_sections = len(sections)

    for i, chunk in enumerate(sections):
        triples = _extract_triples_from_chunk(chunk, llm)
        log.debug("  Abschnitt %d/%d: %d Tripel extrahiert", i + 1, total_sections, len(triples))

        for triple in triples:
            try:
                vera_brain.remember(
                    subject=triple["subject"],
                    predicate=triple["predicate"],
                    object=triple["object"],
                    source=source,
                    confidence=confidence,
                )
                total_stored += 1
            except Exception as e:
                log.warning("  Fact-Speicherung fehlgeschlagen: %s", e)

        if total_stored >= 200:  # Sicherheitslimit pro Dokument
            log.warning("Lehrbuch-Limit 200 Fakten erreicht fuer %s", filename)
            break

    log.info("Lehrbuch-Lernen abgeschlossen: %s — %d Fakten gespeichert", filename, total_stored)
    return {
        "filename": filename,
        "sections_processed": min(i + 1, total_sections),
        "total_sections": total_sections,
        "facts_stored": total_stored,
        "source": source,
    }
