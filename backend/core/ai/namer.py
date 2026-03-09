"""
Document Namer - Generates semantic filenames using LLM.
Pattern: YYYY-MM-DD_Category_Sender_Subject.pdf
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional
from .llm_manager import llm

logger = logging.getLogger(__name__)


class DocumentNamer:
    """Generates semantic document filenames."""
    
    def __init__(self):
        """Initialize namer."""
        self.llm = llm
    
    def generate_filename(
        self, 
        ocr_text: str, 
        category: str,
        original_filename: Optional[str] = None
    ) -> str:
        """
        Generate semantic filename.
        
        Args:
            ocr_text: OCR extracted text
            category: Document category
            original_filename: Original filename (for extension)
        
        Returns:
            Suggested filename (e.g., "2026-02-21_Rechnung_Mueller_Zahnarztbedarf.pdf")
        """
        if not self.llm.is_available():
            return self._fallback_filename(category, original_filename)
        
        # Build prompt
        prompt = self._build_prompt(ocr_text, category)
        
        # Generate
        response = self.llm.generate(
            prompt,
            max_tokens=200,
            temperature=0.1,
            stop=["</s>", "\n\n"]
        )
        
        if not response:
            return self._fallback_filename(category, original_filename)
        
        # Parse and sanitize
        filename = self._parse_response(response, category, original_filename)
        
        return filename
    
    def _build_prompt(self, ocr_text: str, category: str) -> str:
        """Build filename generation prompt."""
        
        prompt = f"""<s>[INST] You are a document naming assistant.
Extract key information from the OCR text to create a semantic filename.

Category: {category}

OCR Text:
{ocr_text[:1000]}

Extract:
- date: Document date (YYYY-MM-DD format, use today if unclear)
- sender: Company/person name (short, no special characters)
- subject: Brief subject/description (2-4 words, no special characters)

Output as JSON:
{{
  "date": "2026-02-21",
  "sender": "Mueller",
  "subject": "Zahnarztbedarf"
}}
[/INST]"""
        
        return prompt
    
    def _parse_response(
        self, 
        response: str, 
        category: str,
        original_filename: Optional[str] = None
    ) -> str:
        """Parse LLM response and build filename."""
        
        try:
            # Extract JSON
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                
                date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
                sender = data.get('sender', 'Unknown')
                subject = data.get('subject', 'Document')
                
                # Sanitize components
                date = self._sanitize_date(date)
                sender = self._sanitize_component(sender)
                subject = self._sanitize_component(subject)
                category_clean = self._sanitize_component(category)
                
                # Get extension
                ext = self._get_extension(original_filename)
                
                # Build filename
                filename = f"{date}_{category_clean}_{sender}_{subject}{ext}"
                
                return filename
        
        except Exception as e:
            logger.error(f"Failed to parse namer response: {e}")
        
        return self._fallback_filename(category, original_filename)
    
    def _sanitize_date(self, date_str: str) -> str:
        """Sanitize and validate date string."""
        # Try to parse as date
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _sanitize_component(self, text: str) -> str:
        """Sanitize filename component (remove special chars, limit length)."""
        # Remove special characters, keep only alphanumeric and basic chars
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Replace spaces with underscores
        text = re.sub(r'\s+', '_', text)
        
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        
        # Limit length
        text = text[:50]
        
        # Remove leading/trailing underscores
        text = text.strip('_')
        
        return text or 'Unknown'
    
    def _get_extension(self, original_filename: Optional[str]) -> str:
        """Extract file extension from original filename."""
        if original_filename:
            ext = original_filename.lower().split('.')[-1]
            if ext in ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif']:
                return f'.{ext}'
        
        return '.pdf'  # Default
    
    def _fallback_filename(self, category: str, original_filename: Optional[str]) -> str:
        """Generate fallback filename if LLM unavailable."""
        date = datetime.now().strftime('%Y-%m-%d')
        category_clean = self._sanitize_component(category)
        timestamp = datetime.now().strftime('%H%M%S')
        ext = self._get_extension(original_filename)
        
        return f"{date}_{category_clean}_{timestamp}{ext}"


# Global instance
namer = DocumentNamer()
