"""
VERA Office Subscription Plans
Defines available plans and their features.
"""

PLANS = {
    "trial": {
        "name": "Testversion",
        "duration_days": 30,
        "max_documents": 100,
        "features": ["ocr", "classify", "search", "export"],
        "price_monthly": 0,
        "description": "30 Tage kostenlos testen"
    },
    "basic": {
        "name": "Basic",
        "duration_days": 365,
        "max_documents": 5000,
        "features": ["ocr", "classify", "search", "export", "scanner"],
        "price_monthly": 29,
        "description": "Fur kleine Buros und Selbststandige"
    },
    "professional": {
        "name": "Professional",
        "duration_days": 365,
        "max_documents": -1,  # unlimited
        "features": [
            "ocr",
            "classify",
            "search",
            "export",
            "scanner",
            "voice",
            "api",
            "multi_user"
        ],
        "price_monthly": 59,
        "description": "Unbegrenzte Dokumente + API-Zugriff"
    },
    "enterprise": {
        "name": "Enterprise",
        "duration_days": 365,
        "max_documents": -1,  # unlimited
        "features": [
            "ocr",
            "classify",
            "search",
            "export",
            "scanner",
            "voice",
            "api",
            "multi_user",
            "priority_support",
            "custom_training"
        ],
        "price_monthly": 99,
        "description": "Alles inklusive + Priority Support"
    }
}


def get_plan(plan_id: str) -> dict:
    """Get plan configuration by ID"""
    return PLANS.get(plan_id, PLANS["trial"])


def get_all_plans() -> dict:
    """Get all available plans"""
    return PLANS
