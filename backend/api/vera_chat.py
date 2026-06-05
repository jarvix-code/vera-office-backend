"""
VERA Chat API
Integration zwischen Gwen (Frontend Chat) und LLM Worker (Mistral 7B Backend)

Endpoints:
- POST /api/chat - Main chat endpoint (Gwen → LLM Worker → Response)
- GET /api/chat/history - Get chat history for current user
- DELETE /api/chat/history - Clear chat history for current user

Flow: User → Gwen → /api/chat → LLM Worker (port 18793) → Response → Gwen
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from datetime import datetime
from typing import List
import httpx  # Async HTTP client (replaces requests)
import traceback
from loguru import logger

from backend.api.auth import get_current_user
from backend.models.chat import store_chat_message, get_chat_history, clear_chat_history
# Optional: RAG integration
# from backend.services.rag_engine import get_relevant_context

router = APIRouter(prefix="/api/chat", tags=["chat"])

LLM_WORKER_URL = "http://127.0.0.1:18793"


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = False  # Enable RAG context retrieval
    max_tokens: int = 512
    temperature: float = 0.7


class ChatResponse(BaseModel):
    response: str
    tokens: int
    processing_time_ms: int
    used_context: bool


class ChatHistoryItem(BaseModel):
    id: int
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime


class ChatMessageItem(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: str
    read: bool


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,  # FastAPI Request object for app.state access
    current_user = Depends(get_current_user)
):
    """
    Main chat endpoint.
    
    Flow:
    1. User sends message via Gwen
    2. (Optional) Retrieve RAG context from documents
    3. Forward to LLM Worker (Mistral 7B)
    4. Store message + response in history
    5. Return response to Gwen
    
    Args:
        request: ChatRequest with user message and generation params
        req: FastAPI Request object (for app.state.http_client access)
        current_user: Authenticated user (from JWT)
    
    Returns:
        ChatResponse with AI response and metadata
    """
    try:
        # Optional: Get context from RAG (QM documents, etc.)
        context = None
        if request.use_rag:
            try:
                # TODO: Implement RAG integration
                # context = await get_relevant_context(request.message)
                logger.info("RAG requested but not yet implemented")
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
        
        # Call LLM Worker (use shared HTTP client from app.state)
        logger.info(f"Sending chat request to LLM Worker: {request.message[:50]}...")
        
        client = req.app.state.http_client  # Use shared client (connection pooling!)
        llm_response = await client.post(
            f"{LLM_WORKER_URL}/chat",
            json={
                "message": request.message,
                "context": context,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
        )
        
        if llm_response.status_code != 200:
            logger.error(f"LLM Worker error: {llm_response.status_code} - {llm_response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM Worker error: {llm_response.status_code}"
            )
        
        data = llm_response.json()
        
        # Store user message in history
        await store_chat_message(
            user_id=current_user.id,
            role="user",
            content=request.message
        )
        
        # Store assistant response in history
        await store_chat_message(
            user_id=current_user.id,
            role="assistant",
            content=data['response']
        )
        
        logger.success(f"✅ Chat response generated ({data['tokens_used']} tokens)")
        
        return ChatResponse(
            response=data['response'],
            tokens=data['tokens_used'],
            processing_time_ms=data['processing_time_ms'],
            used_context=context is not None
        )
    
    except httpx.ConnectError as e:
        logger.error(f"❌ Cannot connect to LLM Worker (port 18793): {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=503,
            detail="LLM Worker nicht verfügbar. Bitte starten Sie den Service."
        )
    
    except httpx.TimeoutException as e:
        logger.error(f"❌ LLM Worker timeout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=504,
            detail="LLM Worker antwortet nicht (Timeout)"
        )
    
    except Exception as e:
        logger.error(f"❌ Chat error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_history(
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Get chat history for current user.
    
    Args:
        limit: Maximum number of messages to return (default: 50)
        current_user: Authenticated user
    
    Returns:
        List of chat messages (user + assistant) ordered by time
    """
    try:
        history = await get_chat_history(
            user_id=current_user.id,
            limit=limit
        )
        
        return [
            ChatHistoryItem(
                id=msg['id'],
                role=msg['role'],
                content=msg['content'],
                created_at=msg['created_at']
            )
            for msg in history
        ]
    
    except Exception as e:
        logger.error(f"Failed to retrieve chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages")
async def get_messages(
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    GET /api/chat/messages
    Liefert Chat-Nachrichten im Format, das KommunikationView (ModuleView.tsx) erwartet.

    Response: { messages: [{ id, sender, content, timestamp, read }] }
    """
    try:
        history = await get_chat_history(user_id=current_user.id, limit=limit)

        messages = [
            ChatMessageItem(
                id=str(msg['id']),
                sender="Du" if msg['role'] == "user" else "VERA",
                content=msg['content'],
                timestamp=msg['created_at'].strftime("%H:%M") if isinstance(msg['created_at'], datetime) else str(msg['created_at']),
                read=True
            )
            for msg in history
        ]

        return {"messages": messages}

    except Exception as e:
        logger.error(f"Failed to retrieve chat messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def delete_history(
    current_user = Depends(get_current_user)
):
    """
    Clear chat history for current user.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        Success message
    """
    try:
        await clear_chat_history(user_id=current_user.id)
        logger.info(f"Chat history cleared for user {current_user.id}")
        
        return {"message": "Chat-Verlauf gelöscht"}
    
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health(req: Request):
    """
    Enhanced health check: Backend + LLM Worker status.
    
    Returns:
        Detailed health status including LLM Worker availability
    """
    backend_status = "online"
    llm_status = "unknown"
    llm_details = None
    
    try:
        client = req.app.state.http_client  # Use shared client
        response = await client.get(f"{LLM_WORKER_URL}/health", timeout=5.0)
        
        if response.status_code == 200:
            llm_status = "online"
            llm_details = response.json()
        else:
            llm_status = "error"
            llm_details = {"status_code": response.status_code, "text": response.text}
    
    except httpx.ConnectError:
        llm_status = "offline"
        llm_details = {"error": "Connection refused - Service not running?"}
    except httpx.TimeoutException:
        llm_status = "timeout"
        llm_details = {"error": "Service not responding"}
    except Exception as e:
        llm_status = "error"
        llm_details = {"error": str(e), "type": type(e).__name__}
    
    return {
        "backend": backend_status,
        "llm_worker": llm_status,
        "llm_details": llm_details,
        "llm_url": LLM_WORKER_URL
    }


@router.post("/test")
async def chat_test(message: str = "Hallo"):
    """
    Minimal test endpoint (no auth, no history storage).
    
    Usage:
        curl -X POST "http://127.0.0.1:8081/api/chat/test?message=Test"
    
    Purpose:
        Isolate LLM Worker connection issues from auth/DB overhead.
    
    Args:
        message: Test message to send to LLM Worker
    
    Returns:
        Raw LLM Worker response or error details
    """
    try:
        logger.info(f"[TEST] Sending test message: {message}")
        
        # Create temporary client (minimal overhead)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{LLM_WORKER_URL}/chat",
                json={
                    "message": message,
                    "max_tokens": 128,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                logger.success("[TEST] ✅ LLM Worker responded successfully")
                return response.json()
            else:
                logger.error(f"[TEST] ❌ LLM Worker error: {response.status_code}")
                return {
                    "error": "LLM Worker error",
                    "status_code": response.status_code,
                    "text": response.text
                }
    
    except httpx.ConnectError as e:
        logger.error(f"[TEST] ❌ Connection refused: {e}")
        return {
            "error": "Connection refused",
            "type": "ConnectError",
            "message": str(e),
            "llm_url": LLM_WORKER_URL
        }
    
    except httpx.TimeoutException as e:
        logger.error(f"[TEST] ❌ Timeout: {e}")
        return {
            "error": "Timeout",
            "type": "TimeoutException",
            "message": str(e)
        }
    
    except Exception as e:
        logger.error(f"[TEST] ❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        return {
            "error": "Unexpected error",
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/status")
async def chat_status(req: Request):
    """
    Legacy status endpoint (kept for backward compatibility).
    
    Redirects to /health internally.
    """
    return await chat_health(req)
