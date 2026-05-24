"""
BLZK Requirements Service
Loads requirements mapping from YAML and provides lookup functions.
"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger


_requirements: Optional[Dict] = None


def _load() -> Dict:
    """Load requirements YAML."""
    global _requirements
    if _requirements is not None:
        return _requirements
    
    yaml_file = Path(__file__).parent / "blzk_requirements.yaml"
    if not yaml_file.exists():
        logger.warning("blzk_requirements.yaml not found")
        _requirements = {}
        return _requirements
    
    with open(yaml_file, "r", encoding="utf-8") as f:
        _requirements = yaml.safe_load(f) or {}
    
    logger.info(f"BLZK Requirements geladen: {len(_requirements)} Mappings")
    return _requirements


def get_requirements(question_id: str) -> Optional[Dict[str, Any]]:
    """Get BLZK requirements for a question ID."""
    data = _load()
    mapping = data.get(question_id)
    if mapping:
        return {**mapping, "question_id": question_id, "found": True}
    return None


def get_requirements_text(question_id: str, include_actions: bool = True) -> str:
    """Format requirements as readable text."""
    req = get_requirements(question_id)
    if not req:
        return "Keine spezifischen Anforderungen gefunden."
    
    text = f"**BLZK-Anforderungen ({req.get('section', '')}):**\n\n"
    for i, r in enumerate(req.get("requirements", []), 1):
        text += f"{i}. {r}\n"
    
    if include_actions and req.get("action_items"):
        text += f"\n**Was ist zu tun:**\n"
        for item in req["action_items"]:
            text += f"- {item}\n"
    
    text += f"\n(Quelle: {req.get('pdf', 'bundle.pdf')}, Seite {req.get('page', '?')})"
    return text


def search_by_keyword(keyword: str) -> List[Dict[str, Any]]:
    """Search requirements by keyword."""
    data = _load()
    keyword_lower = keyword.lower()
    results = []
    
    for q_id, mapping in data.items():
        if not isinstance(mapping, dict):
            continue
        # Search in keywords, section, requirements
        if (any(keyword_lower in kw.lower() for kw in mapping.get("keywords", [])) or
            keyword_lower in mapping.get("section", "").lower() or
            any(keyword_lower in r.lower() for r in mapping.get("requirements", []))):
            results.append({"question_id": q_id, **mapping})
    
    return results


def get_all_requirements() -> List[Dict[str, Any]]:
    """Get all requirements as list."""
    data = _load()
    return [
        {"question_id": q_id, **mapping}
        for q_id, mapping in data.items()
        if isinstance(mapping, dict)
    ]
