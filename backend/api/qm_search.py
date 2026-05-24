"""
VERA Office - QM Search API
RAG-basierte Semantic Search für QM-Dokumente
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from backend.core.rag_engine import get_rag_engine, RAGEngine
from backend.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/qm", tags=["qm-search"])


# Request/Response Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Suchanfrage")
    top_k: int = Field(default=5, ge=1, le=20, description="Anzahl der Top-Ergebnisse")
    category_filter: Optional[str] = Field(None, description="Optional: Filter nach Kategorie")


class SearchResult(BaseModel):
    doc_id: int
    filename: str
    category: str
    preview: str
    distance: Optional[float]
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    result_count: int
    top_k: int


class IndexRequest(BaseModel):
    force: bool = Field(default=False, description="Force re-index (überschreibt bestehende Embeddings)")


class IndexResponse(BaseModel):
    status: str
    indexed_count: int
    failed_count: int
    total_documents: int
    collection_count: int
    message: Optional[str] = None


class StatsResponse(BaseModel):
    model: str
    vector_store: str
    indexed_documents: int
    available_documents: int
    index_coverage: str
    embedding_dimension: int
    chroma_path: str
    db_path: str


class DocumentResponse(BaseModel):
    id: int
    filename: str
    ocr_text: str
    category: str
    created_at: str
    file_path: str


# Endpoints

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic Search über QM-Dokumente
    
    Beispiele:
    - "Hygieneplan Desinfektion"
    - "Notfall Reanimation"
    - "Datenschutz Patientenakte"
    """
    try:
        rag = get_rag_engine()
        
        results = rag.search(
            query=request.query,
            top_k=request.top_k,
            category_filter=request.category_filter
        )
        
        return SearchResponse(
            query=request.query,
            results=[SearchResult(**r) for r in results],
            result_count=len(results),
            top_k=request.top_k
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/index", response_model=IndexResponse)
async def index_documents(
    request: IndexRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Alle QM-Dokumente indexieren (Embeddings erstellen)
    
    Dauert ca. 2-3 Minuten für 750 Dokumente.
    """
    try:
        rag = get_rag_engine()
        
        report = rag.index_documents(force=request.force)
        
        return IndexResponse(**report)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    RAG Engine Statistiken
    """
    try:
        rag = get_rag_engine()
        
        stats = rag.get_stats()
        
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


@router.get("/document/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Vollständiges Dokument abrufen
    """
    try:
        rag = get_rag_engine()
        
        doc = rag.get_document_by_id(doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        return DocumentResponse(**doc)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get document failed: {str(e)}")
