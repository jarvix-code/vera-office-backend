"""
LLM Manager - Singleton for Text-LLM (Mistral 7B) and Fast-LLM (Qwen 2.5).
Loads models once and provides generation interface.
"""
import logging
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class LLMManager:
    """Singleton manager for local LLMs (Text + Vision)."""

    _instance: Optional['LLMManager'] = None
    _model = None
    _fast_model = None
    _config = None
    # Sentinels: verhindern wiederholte Load-Versuche nach erstem Fehler
    _model_load_attempted: bool = False
    _fast_model_load_attempted: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize LLM Manager (lazy loading - model loads on first use)."""
        if self._config is None:
            self._load_config()
        # Model laden NICHT hier - erst bei erstem generate() Aufruf!
    
    def _load_config(self):
        """Load AI configuration from vera.yaml."""
        config_path = PROJECT_ROOT / "config" / "vera.yaml"
        
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            self._config = self._get_default_config()
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
            self._config = full_config.get('ai', self._get_default_config())
        
        logger.info(f"AI config loaded from {config_path}")
    
    def _get_default_config(self) -> dict:
        """Return default AI configuration."""
        return {
            'model_path': 'models/mistral-7b-instruct-v0.2.Q4_K_M.gguf',
            'n_ctx': 4096,
            'n_threads': 8,
            'temperature': 0.1,
            'confidence_threshold': 0.80,
            'auto_confirm_threshold': 0.95,
            'few_shot_examples': 5,
        }
    
    def _load_model(self):
        """Load text GGUF model via llama-cpp-python."""
        if self._model_load_attempted:
            return  # Nur einmal versuchen
        self._model_load_attempted = True
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.warning("llama-cpp-python not installed. LLM features disabled.")
            return
        
        model_path = PROJECT_ROOT / self._config['model_path']
        
        if not model_path.exists():
            logger.warning(f"Text model not found: {model_path}")
            logger.warning("LLM features disabled. Download model first.")
            return
        
        try:
            logger.info(f"Loading text LLM from {model_path}...")
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self._config['n_ctx'],
                n_threads=self._config['n_threads'],
                verbose=False
            )
            logger.info("Text LLM loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load text LLM: {e}")
            self._model = None
    
    def _load_fast_model(self):
        """Load fast GGUF model (Qwen2.5-1.5B) via llama-cpp-python."""
        if self._fast_model_load_attempted:
            return  # Nur einmal versuchen
        self._fast_model_load_attempted = True
        fast_path_str = self._config.get('fast_model_path', '')
        if not fast_path_str:
            logger.info("No fast_model_path configured – Qwen disabled")
            return

        try:
            from llama_cpp import Llama
        except ImportError:
            logger.warning("llama-cpp-python not installed. Fast LLM disabled.")
            return

        model_path = PROJECT_ROOT / fast_path_str
        if not model_path.exists():
            logger.warning(f"Fast model not found: {model_path} – Qwen disabled")
            return

        try:
            logger.info(f"Loading fast LLM from {model_path}...")
            self._fast_model = Llama(
                model_path=str(model_path),
                n_ctx=self._config.get('fast_n_ctx', 2048),
                n_threads=self._config.get('fast_n_threads', 4),
                verbose=False,
            )
            logger.info("Fast LLM (Qwen) loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load fast LLM: {e}")
            self._fast_model = None

    def is_available(self) -> bool:
        """Check if text LLM is available."""
        return self._model is not None
    
    def is_fast_available(self) -> bool:
        """Check if fast LLM (Qwen) is available (lazy-loads on first check)."""
        if self._fast_model is None and not self._fast_model_load_attempted:
            self._load_fast_model()
        return self._fast_model is not None

    def is_vision_available(self) -> bool:
        """Vision-LLM deaktiviert (LLaVA entfernt)."""
        return False

    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 500, 
        temperature: Optional[float] = None,
        stop: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate text completion (lazy-loads model on first call).
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use config default)
            stop: Stop sequences
        
        Returns:
            Generated text or None if model unavailable
        """
        # Lazy load: Model erst hier laden wenn noch nicht geschehen (und nie gescheitert)
        if self._model is None and not self._model_load_attempted:
            self._load_model()
        
        if not self.is_available():
            logger.warning("LLM not available for generation")
            return None
        
        if temperature is None:
            temperature = self._config['temperature']
        
        try:
            response = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or ["</s>", "\n\n\n"],
                echo=False
            )
            
            return response['choices'][0]['text'].strip()
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
    
    def analyze_image(self, image_path: str, **kwargs) -> None:
        """Vision-LLM deaktiviert (LLaVA entfernt)."""
        return None

    def generate_fast(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        stop: Optional[list] = None,
        use_qwen_format: bool = False,
    ) -> Optional[str]:
        """
        Generate using fast model (Qwen2.5-1.5B).
        Falls back to Mistral if fast model unavailable.

        Args:
            prompt: Input prompt (Qwen <|im_start|> format preferred)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences (auto-detected from format if None)
            use_qwen_format: Hint that prompt uses Qwen chat tokens

        Returns:
            Generated text or None on failure
        """
        if self._fast_model is None and not self._fast_model_load_attempted:
            self._load_fast_model()

        if self._fast_model is not None:
            if temperature is None:
                temperature = self._config.get('fast_temperature', 0.7)
            if stop is None:
                stop = ["<|im_end|>", "<|endoftext|>"] if use_qwen_format else ["</s>", "\n\n\n"]
            try:
                response = self._fast_model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop,
                    echo=False,
                )
                return response['choices'][0]['text'].strip()
            except Exception as e:
                logger.error(f"Fast LLM generation failed: {e}")

        # Fallback: Mistral
        logger.info("Fast model unavailable – falling back to Mistral")
        return self.generate(prompt=prompt, max_tokens=max_tokens, temperature=temperature, stop=stop)

    def get_config(self, key: str, default=None):
        """Get configuration value."""
        return self._config.get(key, default)


# Global instance
llm = LLMManager()
