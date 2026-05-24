"""
VERA Agent API
Endpoints for chat interaction and suggestions
"""
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.core.ai.agent import agent
from backend.core.ai.suggestions import suggestion_engine
# from backend.core.telemetry import get_telemetry  # TODO: telemetry.py fehlt
from backend.core.diagnostics import get_diagnostics

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    suggestions: List[str] = []
    actions: List[dict] = []


class SuggestionResponse(BaseModel):
    """Response model for suggestions endpoint."""
    suggestions: List[dict]


@router.post("/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with VERA assistant.
    
    Args:
        request: ChatRequest with message and optional session_id
    
    Returns:
        ChatResponse with VERA's reply and suggestions
    """
    try:
        # Check Diagnostics für proaktive Problemmeldungen
        diagnostics = get_diagnostics()
        diagnostic_alerts = []
        if diagnostics:
            diagnostic_alerts = diagnostics.get_user_alerts()
        
        # Get response from agent
        start_time = time.time()
        agent_response = agent.chat(
            user_message=request.message,
            session_id=request.session_id
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Track Chat-Interaction
        # telemetry = get_telemetry()  # TODO: telemetry.py fehlt
        # if telemetry:
        #     await telemetry.track(
        #         action="chat",
        #         success=True,
        #         duration_ms=duration_ms,
        #         details={"session_id": request.session_id}
        #     )
        
        # Prepend diagnostic alerts to response (falls vorhanden)
        final_response = agent_response.message
        if diagnostic_alerts:
            alerts_text = "\n\n".join(diagnostic_alerts)
            final_response = f"{alerts_text}\n\n{agent_response.message}"
        
        return ChatResponse(
            response=final_response,
            suggestions=agent_response.suggestions,
            actions=agent_response.actions
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        
        # Track Fehler
        # telemetry = get_telemetry()  # TODO: telemetry.py fehlt
        # if telemetry:
        #     await telemetry.track(
        #         action="chat",
        #         success=False,
        #         error=str(e)
        #     )
        
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agent/suggestions", response_model=SuggestionResponse)
async def get_suggestions():
    """
    Get proactive suggestions from VERA.
    
    Returns:
        SuggestionResponse with list of suggestions
    """
    try:
        suggestions = suggestion_engine.get_suggestions()
        
        return SuggestionResponse(suggestions=suggestions)
    
    except Exception as e:
        logger.error(f"Error in suggestions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/agent/voice")
async def voice_input():
    """
    Voice input endpoint (placeholder for future implementation).
    
    Returns:
        Placeholder response
    """
    return {
        "status": "not_implemented",
        "message": "Voice input is not yet implemented"
    }
