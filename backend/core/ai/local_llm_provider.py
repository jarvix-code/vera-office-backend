"""
Local LLM Provider - Wrapper around existing LLMManager.

Two providers:
- LocalLLMProvider: Slow model (Mistral-7B) for docs/background tasks
- FastLLMProvider: Fast model (Qwen2.5-1.5B) for chat

This wraps the existing LLMManager Singleton to conform to BaseLLMProvider interface.
No changes to existing LLMManager - pure adapter pattern.
"""
import logging
from typing import Optional, List
from backend.core.ai.llm_router import BaseLLMProvider
from backend.core.ai.llm_manager import llm as llm_manager

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM provider (Mistral-7B via llama-cpp)."""
    
    def __init__(self):
        """Initialize Local LLM provider (uses existing LLMManager)."""
        self.llm = llm_manager
    
    def is_available(self) -> bool:
        """Check if Local LLM is available."""
        return self.llm.is_available()
    
    def get_provider_name(self) -> str:
        """Get provider name for logging."""
        model_path = self.llm.get_config('model_path') if self.llm.is_available() else "unknown"
        # Extract model name from path (e.g., "mistral-7b-instruct-v0.2.Q4_K_M.gguf" → "Mistral 7B")
        if "mistral" in model_path.lower():
            return "Mistral 7B (Local)"
        elif "llama" in model_path.lower():
            return "Llama (Local)"
        return f"Local LLM ({model_path.split('/')[-1] if '/' in model_path else 'unknown'})"
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate text completion using Local LLM.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use config default)
            stop: Stop sequences
        
        Returns:
            Generated text or None if failed
        """
        if not self.is_available():
            logger.warning("Local LLM not available for generation")
            return None
        
        # Delegate to existing LLMManager (slow model)
        return self.llm.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )


class FastLLMProvider(BaseLLMProvider):
    """Fast LLM provider (Qwen2.5-1.5B via llama-cpp) for chat."""
    
    def __init__(self):
        """Initialize Fast LLM provider (uses existing LLMManager)."""
        self.llm = llm_manager
        self._uses_qwen = False
        
        # Detect if Qwen model is loaded
        if self.is_available():
            try:
                model_path = self.llm.get_config('fast_model_path', '')
                if 'qwen' in model_path.lower():
                    self._uses_qwen = True
                    logger.info("FastLLMProvider: Using Qwen chat format")
            except:
                pass
    
    def is_available(self) -> bool:
        """Check if Fast LLM is available."""
        return self.llm.is_fast_available()
    
    def get_provider_name(self) -> str:
        """Get provider name for logging."""
        if self.is_available():
            return "Qwen 2.5-1.5B (Local, Fast)"
        return "Fast LLM (unavailable)"
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate text completion using Fast LLM.
        Falls back to slow model if fast unavailable.
        
        Args:
            prompt: Input prompt (can be Mistral or Qwen format)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use config default)
            stop: Stop sequences
        
        Returns:
            Generated text or None if failed
        """
        if not self.is_available():
            logger.warning("Fast LLM not available, trying fallback to slow model")
        
        # Convert Mistral prompt to Qwen format if needed
        if self._uses_qwen and "[INST]" in prompt:
            prompt = self._convert_to_qwen_format(prompt)
            use_qwen_format = True
        else:
            use_qwen_format = self._uses_qwen
        
        # Delegate to LLMManager.generate_fast() (handles fallback internally)
        return self.llm.generate_fast(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            use_qwen_format=use_qwen_format
        )
    
    def _convert_to_qwen_format(self, mistral_prompt: str) -> str:
        """
        Convert Mistral [INST] format to Qwen <|im_start|> format.
        
        Args:
            mistral_prompt: Prompt in Mistral format
        
        Returns:
            Prompt in Qwen format
        """
        # Simple conversion: extract system + user message
        # Mistral format: "[INST] system\n\nUser: message [/INST]"
        # Qwen format: "<|im_start|>system\nsystem<|im_end|>\n<|im_start|>user\nmessage<|im_end|>\n<|im_start|>assistant\n"
        
        if "[INST]" not in mistral_prompt:
            return mistral_prompt
        
        try:
            # Extract content between [INST] and [/INST]
            content = mistral_prompt.split("[INST]")[1].split("[/INST]")[0].strip()
            
            # Split system and user parts
            if "\nUser:" in content:
                parts = content.split("\nUser:", 1)
                system = parts[0].strip()
                user = parts[1].strip()
            else:
                system = "Du bist VERA, eine Dokumenten-Assistentin."
                user = content
            
            # Build Qwen format
            qwen_prompt = f"<|im_start|>system\n{system}<|im_end|>\n"
            qwen_prompt += f"<|im_start|>user\n{user}<|im_end|>\n"
            qwen_prompt += "<|im_start|>assistant\n"
            
            return qwen_prompt
        
        except Exception as e:
            logger.warning(f"Failed to convert Mistral->Qwen format: {e}")
            return mistral_prompt
