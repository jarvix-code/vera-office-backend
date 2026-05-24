"""
VERA Tools API - Tools die VERA selbst aufrufen kann
Wie Javix seine Tools nutzt, nutzt VERA diese!
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from backend.core.vera_brain import vera_brain
from backend.db.database import SessionLocal
from backend.models.document import Document
from backend.models.qm import QMDocument
from loguru import logger

router = APIRouter()


class FactRequest(BaseModel):
    category: str
    key: str
    value: str
    source: str = "vera"


class SearchRequest(BaseModel):
    query: str
    doc_type: Optional[str] = None


class LearningRequest(BaseModel):
    topic: str
    insight: str


@router.post("/vera/add-fact")
async def add_fact(request: FactRequest):
    """
    VERA fügt ein Fact zu ihrem Brain hinzu.
    
    Beispiel:
    POST /api/vera/add-fact
    {
        "category": "praxis",
        "key": "adresse",
        "value": "Hauptstraße 123, 96047 Bamberg",
        "source": "user_input"
    }
    """
    vera_brain.add_fact(
        category=request.category,
        key=request.key,
        value=request.value,
        source=request.source
    )
    
    return {"success": True, "message": "Fact gespeichert"}


@router.post("/vera/search")
async def search(request: SearchRequest):
    """
    VERA durchsucht ihr Brain + alle Dokumente.
    
    Beispiel:
    POST /api/vera/search
    {
        "query": "Hygieneplan",
        "doc_type": "qm"
    }
    """
    # Search facts
    facts = vera_brain.search_facts(request.query)
    
    # Search documents
    docs = vera_brain.search_documents(request.query, request.doc_type)
    
    return {
        "facts": facts,
        "documents": docs,
        "total_results": len(facts) + len(docs)
    }


@router.get("/vera/compliance-status")
async def compliance_status():
    """
    VERA prüft QM-Compliance-Status.
    
    Gibt zurück:
    - Erfüllt: X
    - Offen: Y
    - In Arbeit: Z
    """
    status = vera_brain.get_compliance_status()
    return status


@router.post("/vera/learn")
async def learn(request: LearningRequest):
    """
    VERA lernt etwas Neues.
    
    Beispiel:
    POST /api/vera/learn
    {
        "topic": "qm_hygiene",
        "insight": "Hygienepläne müssen monatlich aktualisiert werden"
    }
    """
    vera_brain.add_learning(
        topic=request.topic,
        insight=request.insight
    )
    
    return {"success": True, "message": "Gelernt!"}


@router.post("/vera/index-all-documents")
async def index_all_documents():
    """
    VERA indexiert ALLE Dokumente (normale + QM).
    
    Das passiert automatisch, aber kann manuell getriggert werden.
    """
    db = SessionLocal()
    
    try:
        # Index normal documents
        docs = db.query(Document).filter(Document.ocr_text.isnot(None)).all()
        
        for doc in docs:
            vera_brain.index_document(
                doc_type="document",
                doc_id=doc.id,
                title=doc.filename,
                ocr_text=doc.ocr_text or ""
            )
        
        # Index QM documents
        qm_docs = db.query(QMDocument).filter(QMDocument.ocr_text.isnot(None)).all()
        
        for doc in qm_docs:
            vera_brain.index_document(
                doc_type="qm",
                doc_id=doc.id,
                title=doc.title,
                ocr_text=doc.ocr_text or ""
            )
        
        return {
            "success": True,
            "indexed": {
                "documents": len(docs),
                "qm_documents": len(qm_docs),
                "total": len(docs) + len(qm_docs)
            }
        }
        
    finally:
        db.close()


@router.get("/vera/brain-stats")
async def brain_stats():
    """
    VERA zeigt Brain-Statistiken.
    """
    import sqlite3
    
    conn = sqlite3.connect(vera_brain.db_path)
    cur = conn.cursor()
    
    stats = {}
    
    for table in ["facts", "document_index", "compliance_items", "learnings", "context"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cur.fetchone()[0]
    
    conn.close()
    
    return stats
