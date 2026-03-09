"""
Template Knowledge - Loads document categories from YAML folder templates.
Provides category knowledge for LLM classification prompts.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
import yaml

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "data" / "folder_templates"


def _load_yaml(filename: str) -> dict:
    path = TEMPLATES_DIR / f"{filename}.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_doc_types(folders: list, parent_path: str = "") -> List[Dict]:
    """Recursively extract doc_types with their folder context."""
    results = []
    for folder in folders:
        if folder.get("is_template"):
            continue
        name = folder.get("name", folder.get("id", ""))
        display = folder.get("display_name", name)
        current_path = f"{parent_path}/{name}" if parent_path else name
        retention = folder.get("retention_years")
        
        for dt in folder.get("doc_types", []):
            results.append({
                "name": dt,
                "description": f"{display} ({current_path})",
                "storage_path": current_path,
                "retention_years": retention,
                "folder_display": display,
            })
        
        children = folder.get("children", [])
        if children:
            results.extend(_extract_doc_types(children, current_path))
    
    return results


def get_all_categories(industry: str = "allgemein") -> List[Dict]:
    """
    Get all document categories from base + industry templates.
    
    Returns list of dicts: {name, description, storage_path, retention_years}
    """
    base = _load_yaml("base")
    categories = _extract_doc_types(base.get("folders", []))
    
    # Add industry-specific
    from backend.core.folder_manager import _resolve_template
    template_name = _resolve_template(industry)
    if template_name != "base":
        try:
            branch = _load_yaml(template_name)
            categories.extend(_extract_doc_types(branch.get("folders", [])))
            
            # Add extra_categories
            for ec in branch.get("extra_categories", []):
                categories.append({
                    "name": ec["name"],
                    "description": ec.get("display_name", ec["name"]),
                    "storage_path": ec.get("storage_path", ""),
                    "retention_years": ec.get("retention_years"),
                    "folder_display": ec.get("display_name", ec["name"]),
                })
        except Exception as e:
            logger.warning(f"Failed to load branch template '{template_name}': {e}")
    
    # Deduplicate by name
    seen = set()
    unique = []
    for cat in categories:
        if cat["name"] not in seen:
            seen.add(cat["name"])
            unique.append(cat)
    
    return unique


def get_categories_prompt_text(industry: str = "allgemein") -> str:
    """
    Build a text summary of all categories for LLM prompt context.
    """
    categories = get_all_categories(industry)
    lines = []
    for cat in categories:
        ret = f", Aufbewahrung: {cat['retention_years']} Jahre" if cat.get('retention_years') else ""
        lines.append(f"- {cat['name']}: {cat['description']}{ret}")
    return "\n".join(lines)


def sync_categories_to_db(db_session, industry: str = "allgemein"):
    """
    Sync YAML categories to database Category table.
    Creates missing categories, doesn't delete existing ones.
    """
    from backend.models.category import Category
    
    yaml_cats = get_all_categories(industry)
    existing = {c.name: c for c in db_session.query(Category).all()}
    
    created = 0
    for cat in yaml_cats:
        if cat["name"] not in existing:
            db_cat = Category(
                name=cat["name"],
                display_name=cat.get("folder_display", cat["description"]),
                description=cat["description"],
                storage_path=cat.get("storage_path", ""),
                retention_years=cat.get("retention_years"),
                is_system=True,
            )
            db_session.add(db_cat)
            created += 1
    
    if created:
        db_session.commit()
        logger.info(f"Synced {created} new categories from YAML templates to DB")
    
    return created
