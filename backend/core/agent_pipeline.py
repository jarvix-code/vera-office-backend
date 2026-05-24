"""
Agent Pipeline — Paralleles Multi-Agent-Dokument-Verarbeitungs-System für VERA
===============================================================================
Orchestriert 3 spezialisierte Agents PARALLEL:

  Agent 1 — Klassifizierung  (Mistral 7B)   → Dokumenttyp erkennen
  Agent 2 — Extraktion       (Mistral 7B)   → Felder extrahieren
  Agent 3 — Validierung      (Qwen 2.5)     → OCR-Qualität + Plausibilität prüfen

Agents 1+2+3 laufen gleichzeitig auf den OCR-Text.
Nach Zusammenführung: optionale Typ-spezifische Nachextraktion wenn Konfidenz > 0.8.

Pipeline-State wird in vera.db (SQLite) geloggt.

Usage:
    from core.agent_pipeline import pipeline

    result = await pipeline.process(ocr_text)
    # oder synchron:
    result = pipeline.process_sync(ocr_text)
"""

import asyncio
import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai.llm_manager import llm

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="vera-agent")

# Pipeline-State-Log in bestehender vera.db
_VERA_DB = Path(__file__).parent.parent.parent / "data" / "vera.db"

_CREATE_LOG_TABLE = """
    CREATE TABLE IF NOT EXISTS agent_pipeline_runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type    TEXT,
        confidence  REAL,
        valid       INTEGER,        -- 1 / 0
        ocr_chars   INTEGER,
        duration_ms INTEGER,
        agents_ok   TEXT,           -- JSON list
        agents_err  TEXT,           -- JSON list
        created_at  TEXT NOT NULL
    )
"""


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    agent: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PipelineResult:
    document_type: str
    confidence: float
    extracted_fields: Dict[str, Any]
    validation: Dict[str, Any]
    agents: List[AgentResult]

    @property
    def is_valid(self) -> bool:
        return self.validation.get("valid", False)

    @property
    def completeness(self) -> float:
        return self.validation.get("completeness", 0.0)


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Extrahiert erstes vollständiges JSON-Objekt aus LLM-Antwort."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]
    raise ValueError(f"Kein JSON-Objekt in Antwort: {text[:80]!r}")


# ---------------------------------------------------------------------------
# Agent 1: Klassifizierung (Mistral)
# ---------------------------------------------------------------------------

class ClassificationAgent:
    NAME = "classifier"

    _PROMPT = (
        "[INST] Analysiere diesen OCR-Text und klassifiziere das Dokument.\n"
        "Antworte NUR mit einem JSON-Objekt (keine Erklärung):\n"
        '{"type": "KATEGORIE", "confidence": 0.0-1.0, "language": "de/en", '
        '"reasoning": "kurze Begründung"}\n\n'
        "Erlaubte Kategorien: {categories}\n\n"
        "OCR-Text (erste 1800 Zeichen):\n{ocr_text}\n[/INST]"
    )

    DEFAULT_CATEGORIES = [
        "RECHNUNG", "LIEFERSCHEIN", "VERTRAG", "PROTOKOLL",
        "ANGEBOT", "BESTELLUNG", "FORMULAR", "SONSTIGES",
    ]

    def run(self, ocr_text: str, categories: Optional[List[str]] = None) -> AgentResult:
        cats = ", ".join(categories or self.DEFAULT_CATEGORIES)
        prompt = self._PROMPT.format(ocr_text=ocr_text[:1800], categories=cats)
        raw = llm.generate(prompt, max_tokens=200, temperature=0.1,
                           stop=["[INST]", "</s>", "\n\n\n"])
        if raw is None:
            return AgentResult(self.NAME, False, error="Mistral nicht verfügbar",
                               data={"type": "SONSTIGES", "confidence": 0.1})
        try:
            data = json.loads(_extract_json(raw))
            return AgentResult(self.NAME, True, data=data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[ClassificationAgent] JSON-Parse-Fehler: %s | raw=%r", exc, raw[:120])
            return AgentResult(self.NAME, False, error=str(exc),
                               data={"type": "SONSTIGES", "confidence": 0.1})


# ---------------------------------------------------------------------------
# Agent 2: Extraktion (Mistral)
# ---------------------------------------------------------------------------

class ExtractionAgent:
    NAME = "extractor"

    _PROMPT = (
        "[INST] Extrahiere alle relevanten Felder aus diesem OCR-Text.\n"
        "Antworte NUR mit einem JSON-Objekt. Fehlende Felder → null.\n\n"
        "Typische Felder für {doc_type}: {fields}\n\n"
        "OCR-Text (erste 2000 Zeichen):\n{ocr_text}\n[/INST]"
    )

    _FIELDS_BY_TYPE: Dict[str, str] = {
        "RECHNUNG": (
            "datum, rechnungsnummer, lieferant, empfaenger, "
            "nettobetrag, mwst_betrag, bruttobetrag, zahlungsziel, iban"
        ),
        "LIEFERSCHEIN": (
            "datum, lieferscheinnummer, lieferant, empfaenger, "
            "positionen, gesamtgewicht"
        ),
        "VERTRAG": (
            "datum, vertragsparteien, vertragsbeginn, vertragsende, "
            "vertragsgegenstand, kuendigungsfrist"
        ),
        "ANGEBOT": (
            "datum, angebotsnummer, lieferant, empfaenger, "
            "positionen, gesamtbetrag, gueltig_bis"
        ),
        "BESTELLUNG": (
            "datum, bestellnummer, lieferant, empfaenger, "
            "positionen, gesamtbetrag, lieferdatum"
        ),
        "PROTOKOLL": (
            "datum, teilnehmer, ort, tagesordnung, beschluesse, naechster_termin"
        ),
        "DEFAULT": (
            "datum, referenznummer, absender, empfaenger, betreff, betrag"
        ),
    }

    def run(self, ocr_text: str, doc_type: str = "DEFAULT") -> AgentResult:
        fields = self._FIELDS_BY_TYPE.get(doc_type.upper(), self._FIELDS_BY_TYPE["DEFAULT"])
        prompt = self._PROMPT.format(
            doc_type=doc_type, fields=fields, ocr_text=ocr_text[:2000]
        )
        raw = llm.generate(prompt, max_tokens=500, temperature=0.05,
                           stop=["[INST]", "</s>", "\n\n\n"])
        if raw is None:
            return AgentResult(self.NAME, False, error="Mistral nicht verfügbar")
        try:
            data = json.loads(_extract_json(raw))
            return AgentResult(self.NAME, True, data=data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[ExtractionAgent] JSON-Parse-Fehler: %s | raw=%r", exc, raw[:120])
            return AgentResult(self.NAME, False, error=str(exc), data={})


# ---------------------------------------------------------------------------
# Agent 3: Validierung (Qwen — schnell)
# ---------------------------------------------------------------------------

class ValidationAgent:
    NAME = "validator"

    # Qwen-Chat-Format
    _PROMPT = (
        "<|im_start|>system\n"
        "Du bist ein Qualitätsprüfer für OCR-Dokumente. "
        "Prüfe Lesbarkeit und Vollständigkeit.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "Dokumenttyp: {doc_type}\n"
        "OCR-Qualität: Sind die Texte gut lesbar und vollständig?\n"
        "Erste 800 Zeichen OCR:\n{ocr_preview}\n\n"
        "Antworte NUR mit JSON:\n"
        '{"valid": true/false, "ocr_quality": "gut/mittel/schlecht", '
        '"issues": ["..."], "completeness": 0.0-1.0}\n'
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    _FALLBACK_PROMPT = (
        "[INST] Ist dieser OCR-Text für Typ {doc_type} plausibel und lesbar?\n"
        "JSON: {{\"valid\": true/false, \"completeness\": 0.0-1.0}}\n"
        "Text: {ocr_preview} [/INST]"
    )

    def run(self, ocr_text: str, doc_type: str = "UNBEKANNT") -> AgentResult:
        preview = ocr_text[:800]
        prompt = self._PROMPT.format(doc_type=doc_type, ocr_preview=preview)
        raw = llm.generate_fast(prompt, max_tokens=200, temperature=0.2,
                                use_qwen_format=True)

        if raw is None:
            # Fallback auf Mistral
            prompt_fb = self._FALLBACK_PROMPT.format(
                doc_type=doc_type, ocr_preview=preview
            )
            raw = llm.generate(prompt_fb, max_tokens=100, temperature=0.1)

        if raw is None:
            return AgentResult(self.NAME, False, error="Kein LLM verfügbar",
                               data={"valid": True, "completeness": 0.5, "issues": []})
        try:
            data = json.loads(_extract_json(raw))
            return AgentResult(self.NAME, True, data=data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[ValidationAgent] JSON-Parse-Fehler: %s | raw=%r", exc, raw[:120])
            return AgentResult(self.NAME, True,
                               data={"valid": True, "completeness": 0.5, "issues": []})


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DocumentPipeline:
    """
    Koordiniert 3 Agents für parallele Dokumentenverarbeitung.

    Phase 1 (parallel, 3 Threads):
      - Classifier  → Dokumenttyp
      - Extractor   → Felder (mit Default-Typ)
      - Validator   → OCR-Qualität

    Phase 2 (optional, wenn Typ-Konfidenz > 0.8):
      - Nachextraktion mit erkanntem Dokumenttyp

    State-Logging → vera.db :: agent_pipeline_runs
    """

    def __init__(self):
        self._classifier = ClassificationAgent()
        self._extractor = ExtractionAgent()
        self._validator = ValidationAgent()
        self._ensure_log_table()

    def _ensure_log_table(self):
        try:
            with sqlite3.connect(str(_VERA_DB), timeout=5) as conn:
                conn.execute(_CREATE_LOG_TABLE)
        except Exception as exc:
            logger.warning("[Pipeline] Log-Tabelle nicht angelegt: %s", exc)

    def _log_run(
        self,
        doc_type: str,
        confidence: float,
        valid: bool,
        ocr_chars: int,
        duration_ms: int,
        agents: List[AgentResult],
    ):
        try:
            ok = [a.agent for a in agents if a.success]
            err = [a.agent for a in agents if not a.success]
            with sqlite3.connect(str(_VERA_DB), timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO agent_pipeline_runs
                        (doc_type, confidence, valid, ocr_chars, duration_ms,
                         agents_ok, agents_err, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_type, round(confidence, 3), int(valid),
                        ocr_chars, duration_ms,
                        json.dumps(ok), json.dumps(err),
                        datetime.utcnow().isoformat(),
                    ),
                )
        except Exception as exc:
            logger.debug("[Pipeline] Log-Fehler: %s", exc)

    async def process(
        self,
        ocr_text: str,
        categories: Optional[List[str]] = None,
    ) -> PipelineResult:
        """
        Verarbeitet OCR-Text durch alle 3 Agents parallel.

        Returns:
            PipelineResult mit Typ, Feldern, Validierung, Agent-Status.
        """
        start_ms = _now_ms()
        loop = asyncio.get_event_loop()

        # ---- Phase 1: Alle 3 Agents parallel ----
        logger.info("[Pipeline] Phase 1: 3 Agents starten parallel...")
        classify_f = loop.run_in_executor(_executor, self._classifier.run, ocr_text, categories)
        extract_f  = loop.run_in_executor(_executor, self._extractor.run, ocr_text, "DEFAULT")
        validate_f = loop.run_in_executor(_executor, self._validator.run, ocr_text, "UNBEKANNT")

        classify_r, extract_r, validate_r = await asyncio.gather(
            classify_f, extract_f, validate_f, return_exceptions=False
        )

        doc_type = classify_r.data.get("type", "SONSTIGES")
        type_conf = float(classify_r.data.get("confidence", 0.0))
        logger.info(
            "[Pipeline] Phase 1 fertig: type=%s conf=%.0f%% "
            "extract_ok=%s validate_ok=%s",
            doc_type, type_conf * 100, extract_r.success, validate_r.success,
        )

        # ---- Phase 2: Typ-spezifische Nachextraktion ----
        if type_conf > 0.8 and doc_type != "SONSTIGES":
            logger.info("[Pipeline] Phase 2: Nachextraktion für %s...", doc_type)
            extract_r = await loop.run_in_executor(
                _executor, self._extractor.run, ocr_text, doc_type
            )

        all_agents = [classify_r, extract_r, validate_r]
        failed = [a.agent for a in all_agents if not a.success]
        if failed:
            logger.warning("[Pipeline] Agents mit Fehler: %s", failed)

        duration_ms = _now_ms() - start_ms
        valid = validate_r.data.get("valid", True)
        self._log_run(doc_type, type_conf, valid, len(ocr_text), duration_ms, all_agents)
        logger.info("[Pipeline] Abgeschlossen in %dms — %s valid=%s", duration_ms, doc_type, valid)

        return PipelineResult(
            document_type=doc_type,
            confidence=type_conf,
            extracted_fields=extract_r.data,
            validation=validate_r.data,
            agents=all_agents,
        )

    def process_sync(self, ocr_text: str, **kwargs) -> PipelineResult:
        """Synchroner Wrapper — nutzbar außerhalb von async-Kontexten."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(1) as ex:
                    return ex.submit(asyncio.run, self.process(ocr_text, **kwargs)).result()
            return loop.run_until_complete(self.process(ocr_text, **kwargs))
        except Exception as exc:
            logger.error("[Pipeline] process_sync fehlgeschlagen: %s", exc)
            return PipelineResult("FEHLER", 0.0, {}, {"valid": False, "issues": [str(exc)]}, [])


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def _now_ms() -> int:
    from time import time
    return int(time() * 1000)


# ---------------------------------------------------------------------------
# Singleton — importieren mit: from core.agent_pipeline import pipeline
# ---------------------------------------------------------------------------
pipeline = DocumentPipeline()
