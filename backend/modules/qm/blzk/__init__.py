"""
BLZK Dokumentenkatalog Service
Lädt den BLZK-Katalog und stellt ihn über API bereit.
"""
import yaml
from pathlib import Path
from typing import Optional
from loguru import logger


_catalog = None


def load_catalog() -> dict:
    """Lädt den BLZK-Katalog aus der YAML-Datei."""
    global _catalog
    if _catalog:
        return _catalog
    
    catalog_file = Path(__file__).parent / "katalog.yaml"
    if not catalog_file.exists():
        logger.warning("BLZK-Katalog nicht gefunden")
        return {"kapitel": {}, "fristen": {}}
    
    with open(catalog_file, "r", encoding="utf-8") as f:
        _catalog = yaml.safe_load(f)
    
    logger.info(f"BLZK-Katalog geladen: {sum(len(k.get('dokumente', {})) for k in _catalog.get('kapitel', {}).values())} Dokumente")
    return _catalog


def get_all_documents() -> list:
    """Gibt alle BLZK-Dokumente als flache Liste zurück."""
    catalog = load_catalog()
    docs = []
    for kapitel_id, kapitel in catalog.get("kapitel", {}).items():
        for code, doc in kapitel.get("dokumente", {}).items():
            docs.append({
                "code": code,
                "kapitel": kapitel_id,
                "kapitel_name": kapitel["name"],
                "name": doc["name"],
                "typ": doc["typ"],
                "turnus": doc["turnus"],
                "stammdaten": doc.get("stammdaten", []),
                "beschreibung": doc.get("beschreibung", ""),
            })
    return docs


def get_fristen() -> dict:
    """Gibt den Fristen-Kalender zurück."""
    catalog = load_catalog()
    return catalog.get("fristen", {})


def get_document_by_code(code: str) -> Optional[dict]:
    """Findet ein Dokument anhand seines BLZK-Codes."""
    catalog = load_catalog()
    for kapitel_id, kapitel in catalog.get("kapitel", {}).items():
        for doc_code, doc in kapitel.get("dokumente", {}).items():
            if doc_code == code:
                return {
                    "code": doc_code,
                    "kapitel": kapitel_id,
                    "kapitel_name": kapitel["name"],
                    **doc
                }
    return None
