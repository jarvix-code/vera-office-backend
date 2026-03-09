"""
LLM Router - Routes tasks to appropriate LLM (Fast Cloud vs Local).

Boris' Vision:
- KOMMUNIKATION (User-facing) → GPT-4o-mini (< 1s)
- VERWALTUNG (Background)     → Mistral-7B (30s OK)

Task Classification:
- FAST_TASKS: chat, onboarding, user_query, quick_answer, search_query
- LOCAL_TASKS: doc_classification, summarization, batch_processing, 
               ocr_improvement, entity_extraction
"""
import logging
from typing import Optional, List, Literal
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """LLM task types for routing."""
    # Fast tasks (User-facing, < 2s target)
    CHAT = "chat"
    ONBOARDING = "onboarding"
    USER_QUERY = "user_query"
    QUICK_ANSWER = "quick_answer"
    SEARCH_QUERY = "search_query"
    
    # Local tasks (Background, 30s+ acceptable)
    DOC_CLASSIFICATION = "doc_classification"
    SUMMARIZATION = "summarization"
    BATCH_PROCESSING = "batch_processing"
    OCR_IMPROVEMENT = "ocr_improvement"
    ENTITY_EXTRACTION = "entity_extraction"


# Task routing map
FAST_TASKS = {
    TaskType.CHAT,
    TaskType.ONBOARDING,
    TaskType.USER_QUERY,
    TaskType.QUICK_ANSWER,
    TaskType.SEARCH_QUERY,
}

LOCAL_TASKS = {
    TaskType.DOC_CLASSIFICATION,
    TaskType.SUMMARIZATION,
    TaskType.BATCH_PROCESSING,
    TaskType.OCR_IMPROVEMENT,
    TaskType.ENTITY_EXTRACTION,
}


class BaseLLMProvider:
    """Base interface for LLM providers."""
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Optional[str]:
        """Generate text completion."""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        raise NotImplementedError
    
    def get_provider_name(self) -> str:
        """Get provider name for logging."""
        raise NotImplementedError


class LLMRouter:
    """
    Routes LLM tasks to appropriate provider (Fast Cloud vs Local).
    
    Routing Logic:
    - Fast tasks (chat, onboarding) → Fast LLM if available, else Local
    - Local tasks (classification) → Local LLM always (offline-first)
    - Fallback: If Fast LLM unavailable (no API key) → Local for everything
    """
    
    def __init__(self):
        """Initialize router with Fast and Local LLM providers."""
        self._fast_llm: Optional[BaseLLMProvider] = None
        self._local_llm: Optional[BaseLLMProvider] = None
        
        # Lazy initialization - providers load on first access
        self._fast_initialized = False
        self._local_initialized = False
    
    def _init_fast_llm(self):
        """Initialize Fast Local LLM (Qwen2.5-1.5B with proper chat format)."""
        if self._fast_initialized:
            return
        
        self._fast_initialized = True
        
        try:
            from backend.core.ai.local_llm_provider import FastLLMProvider
            self._fast_llm = FastLLMProvider()
            
            if self._fast_llm.is_available():
                logger.info(f"✅ Fast LLM initialized: {self._fast_llm.get_provider_name()}")
                logger.info("📌 Using Qwen chat format with <|im_start|>/<|im_end|> tokens")
            else:
                logger.warning("⚠️ Fast LLM not available (model not found)")
                self._fast_llm = None
        
        except ImportError as e:
            logger.warning(f"Fast LLM provider not available: {e}")
            self._fast_llm = None
        except Exception as e:
            logger.error(f"Failed to initialize Fast LLM: {e}")
            self._fast_llm = None
    
    def _init_local_llm(self):
        """Initialize Local LLM (Mistral-7B via llama-cpp)."""
        if self._local_initialized:
            return
        
        self._local_initialized = True
        
        try:
            from backend.core.ai.local_llm_provider import LocalLLMProvider
            self._local_llm = LocalLLMProvider()
            
            if self._local_llm.is_available():
                logger.info(f"✅ Local LLM initialized: {self._local_llm.get_provider_name()}")
            else:
                logger.warning("⚠️ Local LLM not available (model not found or load failed)")
        
        except Exception as e:
            logger.error(f"Failed to initialize Local LLM: {e}")
            self._local_llm = None
    
    def get_llm(self, task_type: str) -> Optional[BaseLLMProvider]:
        """
        Get appropriate LLM for task type.
        
        Args:
            task_type: Task type string (e.g., "chat", "doc_classification")
        
        Returns:
            LLM provider or None if no LLM available
        
        Routing Rules:
        - Fast tasks → Fast LLM (if available), else Local
        - Local tasks → Local LLM always
        - Logging: which LLM was selected for transparency
        """
        # Validate task type
        try:
            task = TaskType(task_type)
        except ValueError:
            logger.warning(f"Unknown task type '{task_type}' - defaulting to Local LLM")
            task = TaskType.DOC_CLASSIFICATION  # Default to local
        
        # Route based on task type
        if task in FAST_TASKS:
            # Fast task: prefer Fast LLM, fallback to Local
            if self._fast_llm is None:
                self._init_fast_llm()
            
            if self._fast_llm and self._fast_llm.is_available():
                logger.debug(f"🚀 Task '{task_type}' routed to: {self._fast_llm.get_provider_name()}")
                return self._fast_llm
            
            # Fallback to Local LLM
            logger.info(f"📍 Task '{task_type}' fallback to Local LLM (Fast LLM unavailable)")
            if self._local_llm is None:
                self._init_local_llm()
            
            if self._local_llm and self._local_llm.is_available():
                logger.debug(f"🏠 Task '{task_type}' routed to: {self._local_llm.get_provider_name()}")
                return self._local_llm
            
            logger.error(f"❌ No LLM available for task '{task_type}'")
            return None
        
        else:
            # Local task: always use Local LLM (offline-first)
            if self._local_llm is None:
                self._init_local_llm()
            
            if self._local_llm and self._local_llm.is_available():
                logger.debug(f"🏠 Task '{task_type}' routed to: {self._local_llm.get_provider_name()}")
                return self._local_llm
            
            logger.error(f"❌ Local LLM not available for task '{task_type}'")
            return None
    
    def is_fast_llm_available(self) -> bool:
        """Check if Fast LLM is available."""
        if self._fast_llm is None:
            self._init_fast_llm()
        return self._fast_llm is not None and self._fast_llm.is_available()
    
    def is_local_llm_available(self) -> bool:
        """Check if Local LLM is available."""
        if self._local_llm is None:
            self._init_local_llm()
        return self._local_llm is not None and self._local_llm.is_available()
    
    def get_routing_status(self) -> dict:
        """
        Get routing status for diagnostics.
        
        Returns:
            {
                "fast_llm_available": bool,
                "fast_llm_provider": str or None,
                "local_llm_available": bool,
                "local_llm_provider": str or None,
                "routing_mode": "hybrid" | "local_only" | "none"
            }
        """
        fast_available = self.is_fast_llm_available()
        local_available = self.is_local_llm_available()
        
        if fast_available and local_available:
            mode = "hybrid"
        elif local_available:
            mode = "local_only"
        else:
            mode = "none"
        
        return {
            "fast_llm_available": fast_available,
            "fast_llm_provider": self._fast_llm.get_provider_name() if self._fast_llm else None,
            "local_llm_available": local_available,
            "local_llm_provider": self._local_llm.get_provider_name() if self._local_llm else None,
            "routing_mode": mode
        }


# Global instance (lazy initialization)
llm_router = LLMRouter()
