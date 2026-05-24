"""
Document Filer - Automatically files documents into organized folder structure.
Creates year/month subfolders and moves files.
"""
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentFiler:
    """Automatically files documents into organized structure."""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize filer.
        
        Args:
            base_path: Base documents directory (default: data/documents/)
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent.parent / "data" / "documents"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def file_document(
        self,
        source_path: str,
        category: str,
        document_date: Optional[datetime] = None
    ) -> str:
        """
        File document into organized structure.
        
        Args:
            source_path: Current file path
            category: Document category (creates subfolder)
            document_date: Document date (for year/month folders)
        
        Returns:
            New file path after filing
        """
        source = Path(source_path)
        
        if not source.exists():
            logger.error(f"Source file not found: {source_path}")
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Use document date or current date
        if document_date is None:
            document_date = datetime.now()
        
        # Build target path: base/category/year/month/
        category_path = self.base_path / self._sanitize_path_component(category)
        year_path = category_path / str(document_date.year)
        month_path = year_path / f"{document_date.month:02d}"
        
        # Create directories
        month_path.mkdir(parents=True, exist_ok=True)
        
        # Target file path
        target = month_path / source.name
        
        # Handle duplicate filenames
        if target.exists():
            target = self._get_unique_filename(target)
        
        # Move file
        try:
            shutil.move(str(source), str(target))
            logger.info(f"Filed document: {source.name} -> {target}")
            return str(target)
        
        except Exception as e:
            logger.error(f"Failed to file document: {e}")
            raise
    
    def _sanitize_path_component(self, component: str) -> str:
        """Sanitize path component (folder name)."""
        # Remove invalid characters for folder names
        invalid_chars = '<>:"|?*\\'
        for char in invalid_chars:
            component = component.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        component = component.strip('. ')
        
        return component or 'unknown'
    
    def _get_unique_filename(self, path: Path) -> Path:
        """Generate unique filename if file already exists."""
        base = path.stem
        ext = path.suffix
        parent = path.parent
        counter = 1
        
        while True:
            new_path = parent / f"{base}_{counter}{ext}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    def get_category_path(self, category: str) -> Path:
        """Get base path for a category."""
        return self.base_path / self._sanitize_path_component(category)
    
    def ensure_category_folder(self, category: str, storage_path: Optional[str] = None):
        """
        Ensure category folder exists.
        
        Args:
            category: Category name
            storage_path: Custom storage path (relative to base_path)
        """
        if storage_path:
            # Use custom path from DocumentType
            target = self.base_path / storage_path
        else:
            # Use category name
            target = self.get_category_path(category)
        
        target.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured category folder: {target}")


# Global instance
filer = DocumentFiler()
