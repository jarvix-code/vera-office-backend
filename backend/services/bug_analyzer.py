"""
VERA Bug Analyzer - Nutzt VERA's LLM um Bug-Reports zu analysieren und zu strukturieren.
Identifiziert: Modul, Severity, betroffene Code-Bereiche, Reproduktionsschritte.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("vera.bug_analyzer")

# VERA module map -> code paths
MODULE_MAP = {
    "ocr": {
        "description": "OCR-Pipeline (Texterkennung, Bildverarbeitung)",
        "paths": ["backend/core/ocr_engine.py", "backend/core/image_processor.py"],
    },
    "klassifikation": {
        "description": "KI-Dokumentenklassifikation (Mistral 7B, Few-Shot)",
        "paths": ["backend/core/ai/classifier.py", "backend/core/ai/few_shot_examples.py", "backend/core/ai/feedback_store.py"],
    },
    "ablage": {
        "description": "Dateiablage, Ordnerstruktur, Benennung",
        "paths": ["backend/core/ai/filer.py", "backend/core/ai/namer.py", "backend/core/folder_manager.py"],
    },
    "suche": {
        "description": "Dokumentensuche, Volltextsuche",
        "paths": ["backend/api/documents.py"],
    },
    "scanner": {
        "description": "Scanner-Integration, Hotfolder",
        "paths": ["backend/core/scanner.py", "backend/core/scanner_discovery.py", "backend/api/scanner.py"],
    },
    "ui": {
        "description": "Frontend, Benutzeroberfläche (Vue/Quasar)",
        "paths": ["frontend/src/"],
    },
    "agent": {
        "description": "VERA Chat-Agent, Konversation",
        "paths": ["backend/core/ai/agent.py", "backend/core/ai/vera_prompt.py", "backend/api/agent.py"],
    },
    "auth": {
        "description": "Authentifizierung, Lizenz, Login",
        "paths": ["backend/core/auth_middleware.py", "backend/core/license.py", "backend/api/auth.py"],
    },
    "erp": {
        "description": "ERP-Modul (Finanzen, DATEV)",
        "paths": ["backend/modules/erp/"],
    },
    "qm": {
        "description": "QM-Modul (Qualitätsmanagement)",
        "paths": ["backend/modules/qm/"],
    },
    "system": {
        "description": "System, Updates, Konfiguration, Startup",
        "paths": ["backend/main.py", "backend/config.py", "backend/api/system.py"],
    },
}

ANALYSIS_PROMPT = """[INST] Du bist VERA's interner Bug-Analyst. Analysiere diesen Bug-Report eines Users und erstelle einen strukturierten Report.

## Bug-Report vom User:
{bug_text}

## Verfügbare Module:
{modules_list}

## Aufgabe:
Analysiere den Bug und antworte NUR als JSON:
{{
  "module": "<modul-name aus der Liste>",
  "severity": "<critical|high|medium|low>",
  "title": "<kurzer, präziser Bug-Titel>",
  "description": "<was genau passiert>",
  "expected": "<was erwartet wurde>",
  "possible_cause": "<vermutete Ursache im Code>",
  "affected_files": ["<betroffene Dateien>"],
  "reproduction_steps": ["<Schritt 1>", "<Schritt 2>"],
  "fix_hint": "<Hinweis für den Entwickler>"
}}

Antworte NUR mit dem JSON, kein anderer Text. [/INST]"""


def _get_modules_list() -> str:
    lines = []
    for name, info in MODULE_MAP.items():
        lines.append(f"- {name}: {info['description']}")
    return "\n".join(lines)


def analyze_with_llm(bug_text: str) -> Optional[dict]:
    """Analyze bug report using VERA's local Mistral 7B."""
    try:
        from backend.core.ai.llm_manager import llm

        if not llm.is_available():
            logger.warning("LLM nicht verfügbar, nutze regelbasierten Fallback")
            return None

        prompt = ANALYSIS_PROMPT.format(
            bug_text=bug_text[:1500],
            modules_list=_get_modules_list()
        )

        response = llm.generate(prompt, max_tokens=800, temperature=0.1,
                                stop=["</s>", "[INST]"])
        if not response:
            return None

        # Parse JSON from response
        # LLM might wrap it in ```json ... ```
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.error(f"LLM JSON parse error: {e}\nResponse: {response[:300]}")
        return None
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return None


def analyze_rule_based(bug_text: str) -> dict:
    """Regelbasierter Fallback wenn LLM nicht verfügbar."""
    text_lower = bug_text.lower()

    # Module detection via keywords
    module = "system"  # default
    keyword_map = {
        "ocr": ["ocr", "texterkennung", "erkennt nicht", "unleserlich", "scan", "bild"],
        "klassifikation": ["klassifik", "kategorie", "falsch eingeordnet", "falsch zugeordnet", "erkennung"],
        "ablage": ["ablage", "ordner", "dateiname", "verschoben", "gespeichert"],
        "suche": ["suche", "finde nicht", "nicht gefunden", "volltextsuche"],
        "scanner": ["scanner", "hotfolder", "einzug", "scannen"],
        "ui": ["anzeige", "button", "klick", "seite", "laden", "frontend", "browser", "bildschirm"],
        "agent": ["chat", "vera sagt", "antwort", "konversation", "assistent"],
        "auth": ["login", "passwort", "lizenz", "zugang", "berechtigung"],
        "erp": ["rechnung", "datev", "finanzen", "buchhaltung", "export"],
        "qm": ["qm", "qualität", "audit", "checkliste", "protokoll"],
    }

    max_hits = 0
    for mod, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > max_hits:
            max_hits = hits
            module = mod

    # Severity detection
    severity = "medium"
    if any(w in text_lower for w in ["crash", "absturz", "startet nicht", "datenverlust", "kaputt", "geht gar nicht"]):
        severity = "critical"
    elif any(w in text_lower for w in ["falsch", "fehler", "funktioniert nicht", "geht nicht", "bug"]):
        severity = "high"
    elif any(w in text_lower for w in ["langsam", "umständlich", "könnte besser", "wäre schön"]):
        severity = "low"

    mod_info = MODULE_MAP.get(module, MODULE_MAP["system"])

    return {
        "module": module,
        "severity": severity,
        "title": bug_text[:80],
        "description": bug_text,
        "expected": "",
        "possible_cause": f"Vermutlich im Modul '{module}' ({mod_info['description']})",
        "affected_files": mod_info["paths"],
        "reproduction_steps": [],
        "fix_hint": "Manuell prüfen — regelbasierte Analyse, kein LLM verfügbar.",
        "analysis_method": "rule_based"
    }


def analyze_bug(bug_text: str) -> dict:
    """Hauptfunktion: Analysiert Bug-Report (LLM mit Fallback auf Regelbasiert)."""
    result = analyze_with_llm(bug_text)

    if result is None:
        result = analyze_rule_based(bug_text)
        result["analysis_method"] = "rule_based"
    else:
        result["analysis_method"] = "llm"

    # Enrich with file paths from module map
    module = result.get("module", "system")
    if module in MODULE_MAP and not result.get("affected_files"):
        result["affected_files"] = MODULE_MAP[module]["paths"]

    return result
