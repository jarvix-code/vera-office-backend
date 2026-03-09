"""
LLM Manager - Singleton for Multi-LLM (Fast Chat + Slow Docs + Vision).
Loads models once and provides generation interface.
"""
import os
import logging
import base64
from pathlib import Path
from typing import Optional, List
import yaml

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class LLMManager:
    """Singleton manager for local LLMs (Fast Chat + Slow Docs + Vision)."""
    
    _instance: Optional['LLMManager'] = None
    _model = None              # Slow model (Mistral-7B) for docs
    _fast_model = None         # Fast model (Qwen2.5-1.5B) for chat
    _vision_model = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize LLM Manager (loads models on first access)."""
        if self._config is None:
            self._load_config()
        if self._model is None:
            self._load_model()
        if self._fast_model is None:
            self._load_fast_model()
    
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
            'model_path': 'models/mistral-7b-instruct-v0.2.Q4_K_M.gguf',  # Slow model for docs
            'fast_model_path': 'models/qwen2.5-1.5b-instruct-q4_k_m.gguf',  # Fast model for chat
            'n_ctx': 4096,
            'n_threads': 8,
            'temperature': 0.1,
            'confidence_threshold': 0.80,
            'auto_confirm_threshold': 0.95,
            'few_shot_examples': 5,
            'vision': {
                'enabled': True,
                'model_path': 'models/ggml-model-q4_k.gguf',
                'clip_model_path': 'models/mmproj-model-f16.gguf',
                'n_ctx': 2048,
                'n_threads': 8,
                'temperature': 0.1,
            }
        }
    
    def _load_model(self):
        """Load text GGUF model via llama-cpp-python."""
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
        """Load fast GGUF model for chat (Qwen2.5-1.5B)."""
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.warning("llama-cpp-python not installed. Fast LLM disabled.")
            return
        
        fast_model_path = PROJECT_ROOT / self._config.get('fast_model_path', 'models/qwen2.5-1.5b-instruct-q4_k_m.gguf')
        
        if not fast_model_path.exists():
            logger.warning(f"Fast model not found: {fast_model_path}")
            logger.info("Fast chat disabled. Will use slow model for chat too.")
            return
        
        try:
            logger.info(f"Loading fast LLM from {fast_model_path}...")
            self._fast_model = Llama(
                model_path=str(fast_model_path),
                n_ctx=2048,  # Qwen needs less context
                n_threads=self._config['n_threads'],
                verbose=False
            )
            logger.info("Fast LLM loaded successfully (for chat)")
        except Exception as e:
            logger.error(f"Failed to load fast LLM: {e}")
            self._fast_model = None
    
    def _load_vision_model(self):
        """Load Vision-LLM (LLaVA) on first use."""
        if self._vision_model is not None:
            return
        
        vision_config = self._config.get('vision', {})
        if not vision_config.get('enabled', False):
            logger.info("Vision-LLM disabled in config")
            return
        
        try:
            from llama_cpp import Llama
            from llama_cpp.llama_chat_format import Llava15ChatHandler
        except ImportError:
            logger.warning("llama-cpp-python not installed. Vision-LLM disabled.")
            return
        
        model_path = PROJECT_ROOT / vision_config['model_path']
        clip_path = PROJECT_ROOT / vision_config['clip_model_path']
        
        if not model_path.exists():
            logger.warning(f"Vision model not found: {model_path}")
            return
        if not clip_path.exists():
            logger.warning(f"CLIP projector not found: {clip_path}")
            return
        
        try:
            logger.info(f"Loading Vision-LLM from {model_path}...")
            chat_handler = Llava15ChatHandler(clip_model_path=str(clip_path), verbose=False)
            self._vision_model = Llama(
                model_path=str(model_path),
                chat_handler=chat_handler,
                n_ctx=vision_config.get('n_ctx', 2048),
                n_threads=vision_config.get('n_threads', 8),
                logits_all=True,
                verbose=False
            )
            logger.info("Vision-LLM loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Vision-LLM: {e}")
            self._vision_model = None
    
    def is_available(self) -> bool:
        """Check if text LLM is available."""
        return self._model is not None
    
    def is_fast_available(self) -> bool:
        """Check if fast LLM is available."""
        return self._fast_model is not None
    
    def is_vision_available(self) -> bool:
        """Check if Vision-LLM is available (loads on first check)."""
        if self._vision_model is None:
            self._load_vision_model()
        return self._vision_model is not None
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 500, 
        temperature: Optional[float] = None,
        stop: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate text completion.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use config default)
            stop: Stop sequences
        
        Returns:
            Generated text or None if model unavailable
        """
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
    
    def generate_fast(
        self, 
        prompt: str, 
        max_tokens: int = 500, 
        temperature: Optional[float] = None,
        stop: Optional[list] = None,
        use_qwen_format: bool = False
    ) -> Optional[str]:
        """
        Generate text completion using FAST model (Qwen for chat).
        Falls back to slow model if fast model unavailable.
        
        Args:
            prompt: Input prompt (pre-formatted for Qwen if use_qwen_format=True)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use config default)
            stop: Stop sequences (if None, uses Qwen defaults)
            use_qwen_format: If True, uses Qwen chat stop sequences
        
        Returns:
            Generated text or None if no model available
        """
        # Try fast model first
        if self.is_fast_available():
            model = self._fast_model
            logger.debug("Using FAST model (Qwen) for generation")
            # Qwen needs special stop sequences
            if stop is None and use_qwen_format:
                stop = ["<|im_end|>", "<|endoftext|>"]
        elif self.is_available():
            model = self._model
            logger.debug("Fast model unavailable, falling back to slow model (Mistral)")
            # Mistral stop sequences
            if stop is None:
                stop = ["</s>", "\n\n\n"]
        else:
            logger.warning("No LLM available for generation")
            return None
        
        if temperature is None:
            temperature = self._config['temperature']
        
        try:
            response = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                echo=False
            )
            
            text = response['choices'][0]['text'].strip()
            
            # Clean up Qwen artifacts if needed
            if use_qwen_format and "<|im_end|>" in text:
                text = text.split("<|im_end|>")[0].strip()
            
            return text
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
    
    def analyze_image(
        self,
        image_path: str,
        prompt: str = "Is this document photo readable, complete, and sharp enough for OCR? Answer in JSON.",
        max_tokens: int = 300,
    ) -> Optional[str]:
        """
        Analyze an image using Vision-LLM.
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            max_tokens: Maximum tokens to generate
        
        Returns:
            Vision-LLM response text or None
        """
        if not self.is_vision_available():
            logger.warning("Vision-LLM not available")
            return None
        
        # Read and encode image
        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return None
        
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine mime type
            suffix = image_path.suffix.lower()
            mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.tiff': 'image/tiff', '.tif': 'image/tiff'}
            mime_type = mime_map.get(suffix, 'image/jpeg')
            data_uri = f"data:{mime_type};base64,{image_data}"
            
            vision_config = self._config.get('vision', {})
            temperature = vision_config.get('temperature', 0.1)
            
            response = self._vision_model.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_uri}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            return response['choices'][0]['message']['content'].strip()
        
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return None
    
    def get_config(self, key: str):
        """Get configuration value."""
        return self._config.get(key)


# Global instance
llm = LLMManager()
