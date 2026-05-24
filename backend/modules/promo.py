# v2.0: [MODULE-AUTH] PromoStore — Promo-Code Validator
"""
PromoStore: Validiert Promo-Codes gegen data/promo_codes.json.

Promo-Codes schalten Module für EINZELNE USER frei.
Der tatsächliche Unlock-Status wird in User.unlocked_modules (DB) gespeichert,
NICHT in einer globalen Datei.

Workflow:
    1. User gibt Promo-Code ein
    2. PromoStore.validate(code) prüft gegen data/promo_codes.json
    3. Bei Erfolg gibt validate() die freizuschaltenden Module zurück
    4. Der API-Endpoint schreibt die Module in User.unlocked_modules (DB)
"""

import json
from pathlib import Path
from typing import Tuple
from loguru import logger


class PromoStore:
    """
    Validiert Promo-Codes. Keine eigene Persistierung —
    Unlock-Status wird vom Aufrufer in der DB gespeichert.
    """

    def __init__(self, codes_path: Path):
        """
        Args:
            codes_path: Pfad zu promo_codes.json
        """
        self.codes_path = codes_path
        self._codes: dict = {}
        self._load()

    def _load(self):
        """Lädt Promo-Code-Definitionen."""
        if not self.codes_path.exists():
            logger.warning(f"Promo-Codes nicht gefunden: {self.codes_path}")
            return
        try:
            with open(self.codes_path, "r") as f:
                self._codes = json.load(f)
            logger.info(f"Promo-Codes geladen: {len(self._codes)} Codes")
        except Exception as e:
            logger.error(f"Promo-Codes laden fehlgeschlagen: {e}")
            self._codes = {}

    def validate(self, code: str) -> Tuple[bool, list, str]:
        """
        Validiert einen Promo-Code.

        Args:
            code: Promo-Code (z.B. "VERA-DEMO-2026")

        Returns:
            (gültig, module_liste, nachricht)
        """
        code_upper = code.strip().upper()
        entry = self._codes.get(code_upper)

        if not entry:
            logger.warning(f"Ungültiger Promo-Code: '{code}'")
            return False, [], "Ungültiger Promo-Code"

        modules = entry.get("modules", [])
        if not modules:
            return False, [], "Promo-Code hat keine Module zugewiesen"

        module_names = ", ".join(m.upper() for m in modules)
        logger.info(f"Promo-Code gültig: '{code_upper}' → {modules}")
        return True, modules, f"Modul(e) freigeschaltet: {module_names}"
