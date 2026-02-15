"""
Base Extractor - Abstract base class for all extractors.

SHARED FILE - Do not modify unless discussed with team.

All team members inherit from this class.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import hashlib
import json
from typing import Dict, Any

from storage.json_store import JSONStore
from storage.schemas import validate_extraction


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    
    Each team member creates their own extractor by:
    1. Inheriting from this class
    2. Implementing load_model(), unload_model(), extract()
    3. Using the shared utilities for metadata, hashing, etc.
    
    Example:
        class ImageExtractor(BaseExtractor):
            def load_model(self):
                # Load Qwen2.5-VL
                pass
            
            def extract(self, file_path: str) -> Dict[str, Any]:
                # Process image, return extraction dict
                pass
    """
    
    SUPPORTED_EXTENSIONS = set()  # Override in child class
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.model = None
        self.json_store = JSONStore()
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by each team member
    # =========================================================================
    
    @abstractmethod
    def load_model(self):
        """
        Load the AI model into memory.
        
        Called automatically before first extraction.
        Implement your model loading logic here.
        """
        pass
    
    @abstractmethod
    def unload_model(self):
        """
        Unload model to free memory.
        
        Call this when done processing to free GPU/RAM.
        """
        pass
    
    @abstractmethod
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract information from a file.
        
        Args:
            file_path: Path to the file to process
        
        Returns:
            Extraction dictionary matching the schema in storage/schemas.py
        
        The returned dict MUST include:
            - file_id
            - file_path
            - file_type
            - file_hash
            - file_size_bytes
            - created_at
            - modified_at
            - extracted_at
            - extraction (dict with type-specific fields)
            - embedding_text
        """
        pass
    
    # =========================================================================
    # SHARED METHODS - Use these in your implementation
    # =========================================================================
    
    def extract_and_save(self, file_path: str) -> Path:
        """
        Extract from file and save to JSON.
        
        Args:
            file_path: Path to the file to process
        
        Returns:
            Path to the saved JSON file
        
        Raises:
            ValueError: If extraction is invalid
        """
        # Extract
        extraction = self.extract(file_path)
        
        # Validate
        validation = validate_extraction(extraction)
        if not validation["valid"]:
            raise ValueError(f"Invalid extraction: {validation['errors']}")
        
        if validation["warnings"]:
            for warning in validation["warnings"]:
                print(f"  Warning: {warning}")
        
        # Save
        json_path = self.json_store.save(extraction)
        
        return json_path
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get basic file metadata.
        
        Use this at the start of your extract() method.
        
        Returns:
            Dict with file_path, file_name, file_extension, 
            file_size_bytes, created_at, modified_at, extracted_at, file_hash
        """
        path = Path(file_path)
        stat = path.stat()
        
        return {
            "file_path": str(path.absolute()),
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extracted_at": datetime.now().isoformat(),
            "file_hash": self.get_file_hash(file_path)
        }
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Generate MD5 hash for change detection.
        
        Same file content = same hash.
        Used to detect when files are modified.
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def generate_file_id(self, file_path: str, prefix: str) -> str:
        """
        Generate unique file ID.
        
        Args:
            file_path: Path to the file
            prefix: "img" for images, "aud" for audio, "doc" for documents
        
        Returns:
            ID like "img_a1b2c3d4"
        """
        hash_short = self.get_file_hash(file_path)[:8]
        return f"{prefix}_{hash_short}"
    
    def is_already_extracted(self, file_path: str, file_type: str) -> bool:
        """
        Check if file was already extracted with same content.
        
        Returns True if a JSON exists with the same file_hash.
        Use this to skip already-processed files.
        """
        current_hash = self.get_file_hash(file_path)
        existing = self.json_store.find_by_hash(current_hash)
        return existing is not None
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file extension is supported by this extractor"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def create_embedding_text(self, extraction: Dict[str, Any]) -> str:
        """
        Create text for vector embedding.
        
        Override this in your extractor for custom logic.
        Default implementation combines summary + categories + topics.
        """
        parts = []
        
        ext = extraction.get("extraction", {})
        
        # Add summary or description
        for field in ["summary", "description", "visual_summary"]:
            if ext.get(field):
                parts.append(ext[field])
                break
        
        # Add categories
        if ext.get("categories"):
            parts.append(f"Categories: {', '.join(ext['categories'])}")
        
        # Add topics
        if ext.get("topics"):
            parts.append(f"Topics: {', '.join(ext['topics'])}")
        
        # Add key entities
        entities = ext.get("entities", {})
        for entity_type in ["people", "organizations", "locations"]:
            if entities.get(entity_type):
                values = entities[entity_type][:5]  # Limit to 5
                parts.append(f"{entity_type.capitalize()}: {', '.join(str(v) for v in values)}")
        
        return " | ".join(parts)
