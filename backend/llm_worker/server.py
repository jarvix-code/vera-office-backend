"""
VERA LLM Worker - Mistral 7B Backend
FastAPI Server für Chat-Anfragen via llama-cpp-python

Endpoints:
- POST /chat - Main chat endpoint (Gwen → Mistral → Response)
- GET /health - Health check
- GET /models - List available models

Port: 18793
Model: Mistral 7B Instruct v0.2 Q4_K_M
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn
from pathlib import Path
from loguru import logger
import sys
import time

# Loguru Setup
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
    level="INFO"
)

app = FastAPI(
    title="VERA LLM Worker",
    description="Local Mistral 7B Backend for VERA Chat",
    version="1.0.0"
)

# Model Configuration
MODEL_PATH = Path("C:/Jarvix/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
MODEL_NAME = "mistral-7b-instruct-v0.2"
CONTEXT_WINDOW = 8192
CPU_THREADS = 8

# Global LLM instance (loaded on startup)
llm = None


class ChatRequest(BaseModel):
    message: str
    context: str | None = None  # Optional: RAG context from documents
    max_tokens: int = 512
    temperature: float = 0.7
    system_prompt: str | None = None  # Optional: Override default system prompt


class ChatResponse(BaseModel):
    response: str
    tokens_used: int
    processing_time_ms: int


class HealthResponse(BaseModel):
    status: str
    model: str
    port: int
    model_loaded: bool
    context_window: int


class ModelInfo(BaseModel):
    id: str
    type: str
    context_window: int
    path: str


def load_model():
    """Load Mistral 7B model into memory"""
    global llm
    
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    
    logger.info(f"Loading Mistral 7B from {MODEL_PATH}")
    start_time = time.time()
    
    try:
        llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=CONTEXT_WINDOW,
            n_threads=CPU_THREADS,
            n_gpu_layers=0,  # CPU only (no GPU)
            verbose=False
        )
        
        load_time = time.time() - start_time
        logger.success(f"✅ Model loaded successfully in {load_time:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Load model on server startup"""
    load_model()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for VERA.
    
    Flow: Gwen → POST /chat → Mistral 7B → Response → Gwen
    
    Args:
        request: ChatRequest with message, optional context, and generation params
    
    Returns:
        ChatResponse with generated text and metadata
    """
    if llm is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Build prompt using Mistral instruction format
        if request.system_prompt:
            system = request.system_prompt
        else:
            system = "Du bist VERA, ein intelligenter Assistent für Zahnarztpraxen. Du hilfst bei Dokumentation, QM-Fragen und Praxisorganisation. Antworte präzise, freundlich und auf Deutsch."
        
        # Build prompt with optional context
        if request.context:
            prompt = f"""[INST] {system}

Relevante Informationen:
{request.context}

Frage: {request.message}
[/INST]"""
        else:
            prompt = f"[INST] {system}\n\nFrage: {request.message}\n[/INST]"
        
        logger.info(f"Generating response for: {request.message[:50]}...")
        
        # Generate response
        output = llm(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=["[INST]", "</s>", "[/INST]"],
            echo=False
        )
        
        response_text = output['choices'][0]['text'].strip()
        tokens_used = output['usage']['total_tokens']
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.success(f"✅ Response generated ({tokens_used} tokens, {processing_time}ms)")
        
        return ChatResponse(
            response=response_text,
            tokens_used=tokens_used,
            processing_time_ms=processing_time
        )
    
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.
    Returns server status and model info.
    """
    return HealthResponse(
        status="healthy" if llm is not None else "degraded",
        model=MODEL_NAME,
        port=18793,
        model_loaded=llm is not None,
        context_window=CONTEXT_WINDOW
    )


@app.get("/models")
async def models():
    """
    List available models.
    Currently only supports Mistral 7B.
    """
    return {
        "models": [
            ModelInfo(
                id=MODEL_NAME,
                type="llama.cpp",
                context_window=CONTEXT_WINDOW,
                path=str(MODEL_PATH)
            )
        ]
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "VERA LLM Worker",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "status": "running" if llm is not None else "loading",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "models": "GET /models"
        }
    }


if __name__ == "__main__":
    logger.info("🚀 Starting VERA LLM Worker on port 18793")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=18793,
        log_level="info"
    )
