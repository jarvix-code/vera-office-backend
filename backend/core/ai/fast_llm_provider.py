"""
Fast LLM Provider - Cloud-based LLM for user-facing tasks.

Supports:
- OpenAI GPT-4o-mini (primary)
- Anthropic Claude Haiku (optional, future)

Configuration (backend/config.py + config/vera.yaml):
- FAST_LLM_PROVIDER: "openai" | "anthropic"
- FAST_LLM_MODEL: "gpt-4o-mini" | "claude-3-haiku-20240307"
- FAST_LLM_API_KEY: API key from environment or config
"""
import os
import logging
from typing import Optional, List
from backend.core.ai.llm_router import BaseLLMProvider

logger = logging.getLogger(__name__)


class FastLLMProvider(BaseLLMProvider):
    """Fast Cloud LLM provider (OpenAI/Anthropic)."""
    
    def __init__(self):
        """Initialize Fast LLM from config."""
        self._provider = None
        self._model = None
        self._client = None
        self._api_key = None
        
        self._load_config()
        self._init_client()
    
    def _load_config(self):
        """Load Fast LLM configuration."""
        from backend.config import config
        from pathlib import Path
        import yaml
        
        # Load from YAML config if exists
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "vera.yaml"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    fast_llm_config = yaml_config.get('fast_llm', {})
            except Exception as e:
                logger.warning(f"Failed to load YAML config: {e}")
                fast_llm_config = {}
        else:
            fast_llm_config = {}
        
        # Priority: ENV > YAML > Default
        self._provider = os.getenv('FAST_LLM_PROVIDER') or fast_llm_config.get('provider', 'openai')
        self._model = os.getenv('FAST_LLM_MODEL') or fast_llm_config.get('model', 'gpt-4o-mini')
        self._api_key = os.getenv('FAST_LLM_API_KEY') or os.getenv('OPENAI_API_KEY') or fast_llm_config.get('api_key')
        
        logger.info(f"Fast LLM config: provider={self._provider}, model={self._model}, api_key={'***' if self._api_key else 'NOT SET'}")
    
    def _init_client(self):
        """Initialize API client based on provider."""
        if not self._api_key:
            logger.warning("Fast LLM API key not set - provider unavailable")
            return
        
        if self._provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
                logger.info(f"OpenAI client initialized (model: {self._model})")
            except ImportError:
                logger.error("openai package not installed - run: pip install openai")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self._client = None
        
        elif self._provider == "anthropic":
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self._api_key)
                logger.info(f"Anthropic client initialized (model: {self._model})")
            except ImportError:
                logger.error("anthropic package not installed - run: pip install anthropic")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self._client = None
        
        else:
            logger.error(f"Unknown Fast LLM provider: {self._provider}")
            self._client = None
    
    def is_available(self) -> bool:
        """Check if Fast LLM is available."""
        return self._client is not None and self._api_key is not None
    
    def get_provider_name(self) -> str:
        """Get provider name for logging."""
        if self._provider == "openai":
            return f"OpenAI {self._model}"
        elif self._provider == "anthropic":
            return f"Anthropic {self._model}"
        return f"Unknown ({self._provider})"
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate text completion using Fast Cloud LLM.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = provider default)
            stop: Stop sequences
        
        Returns:
            Generated text or None if failed
        """
        if not self.is_available():
            logger.warning("Fast LLM not available for generation")
            return None
        
        # Default temperature (higher than Local LLM for more natural chat)
        if temperature is None:
            temperature = 0.7
        
        try:
            if self._provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature, stop)
            elif self._provider == "anthropic":
                return self._generate_anthropic(prompt, max_tokens, temperature, stop)
            else:
                logger.error(f"Unknown provider: {self._provider}")
                return None
        
        except Exception as e:
            logger.error(f"Fast LLM generation failed: {e}")
            return None
    
    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]]
    ) -> Optional[str]:
        """Generate using OpenAI API."""
        try:
            # OpenAI expects messages format, not raw prompt
            # Convert Mistral-style [INST]...[/INST] to messages if present
            if "[INST]" in prompt and "[/INST]" in prompt:
                # Extract instruction
                start = prompt.find("[INST]") + 6
                end = prompt.find("[/INST]")
                instruction = prompt[start:end].strip()
                
                messages = [
                    {"role": "system", "content": "You are VERA, a helpful document management assistant for German SMEs. Answer in German."},
                    {"role": "user", "content": instruction}
                ]
            else:
                # Plain prompt
                messages = [
                    {"role": "system", "content": "You are VERA, a helpful document management assistant. Answer in German."},
                    {"role": "user", "content": prompt}
                ]
            
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def _generate_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]]
    ) -> Optional[str]:
        """Generate using Anthropic API."""
        try:
            # Anthropic expects messages format
            if "[INST]" in prompt and "[/INST]" in prompt:
                start = prompt.find("[INST]") + 6
                end = prompt.find("[/INST]")
                instruction = prompt[start:end].strip()
                user_content = instruction
            else:
                user_content = prompt
            
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are VERA, a helpful document management assistant for German SMEs. Answer in German.",
                messages=[
                    {"role": "user", "content": user_content}
                ],
                stop_sequences=stop or []
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None
