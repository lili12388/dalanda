"""
JSON Store - Handles saving and loading extraction JSON files.

SHARED FILE - Do not modify unless discussed with team.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.settings import (
    IMAGES_EXTRACTIONS_DIR,
    AUDIO_EXTRACTIONS_DIR,
    DOCUMENTS_EXTRACTIONS_DIR,
    ensure_directories
)


class JSONStore:
    """
    Handles saving and loading JSON extraction files.
    Each extraction is stored as a separate JSON file.
    
    Structure:
        data/extractions/
        ├── images/
        │   ├── img_a1b2c3d4.json
        │   └── img_e5f6g7h8.json
        ├── audio/
        │   └── aud_m3n4o5p6.json
        └── documents/
            └── doc_q7r8s9t0.json
    """
    
    # Map file types to their directories
    TYPE_DIRS = {
        "image": IMAGES_EXTRACTIONS_DIR,
        "audio": AUDIO_EXTRACTIONS_DIR,
        "document": DOCUMENTS_EXTRACTIONS_DIR
    }
    
    def __init__(self):
        ensure_directories()
    
    def save(self, extraction: Dict[str, Any]) -> Path:
        """
        Save an extraction to a JSON file.
        
        Args:
            extraction: Dictionary containing the extraction data.
                       Must have 'file_type' and 'file_id' keys.
        
        Returns:
            Path to the saved JSON file.
        """
        file_type = extraction.get("file_type")
        file_id = extraction.get("file_id")
        
        if not file_type or not file_id:
            raise ValueError("Extraction must have 'file_type' and 'file_id'")
        
        if file_type not in self.TYPE_DIRS:
            raise ValueError(f"Unknown file type: {file_type}. Must be one of: {list(self.TYPE_DIRS.keys())}")
        
        # Determine output path
        output_dir = self.TYPE_DIRS[file_type]
        output_path = output_dir / f"{file_id}.json"
        
        # Save with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extraction, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load(self, file_id: str, file_type: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific extraction by ID and type.
        
        Args:
            file_id: The unique file ID (e.g., "img_a1b2c3d4")
            file_type: The type ("image", "audio", "document")
        
        Returns:
            The extraction dictionary or None if not found.
        """
        if file_type not in self.TYPE_DIRS:
            return None
        
        file_path = self.TYPE_DIRS[file_type] / f"{file_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_by_path(self, json_path: str) -> Optional[Dict[str, Any]]:
        """Load extraction from a specific JSON file path"""
        path = Path(json_path)
        
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_all(self, file_type: str = None) -> List[Dict[str, Any]]:
        """
        Get all extractions, optionally filtered by type.
        
        Args:
            file_type: Optional filter ("image", "audio", "document")
        
        Returns:
            List of extraction dictionaries.
        """
        extractions = []
        
        if file_type:
            dirs = [self.TYPE_DIRS.get(file_type)]
        else:
            dirs = list(self.TYPE_DIRS.values())
        
        for dir_path in dirs:
            if dir_path and dir_path.exists():
                for json_file in dir_path.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            extractions.append(json.load(f))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse {json_file}")
        
        return extractions
    
    def get_all_paths(self, file_type: str = None) -> List[Path]:
        """Get paths to all JSON files, optionally filtered by type"""
        paths = []
        
        if file_type:
            dirs = [self.TYPE_DIRS.get(file_type)]
        else:
            dirs = list(self.TYPE_DIRS.values())
        
        for dir_path in dirs:
            if dir_path and dir_path.exists():
                paths.extend(dir_path.glob("*.json"))
        
        return paths
    
    def exists(self, file_id: str, file_type: str) -> bool:
        """Check if an extraction already exists"""
        if file_type not in self.TYPE_DIRS:
            return False
        
        file_path = self.TYPE_DIRS[file_type] / f"{file_id}.json"
        return file_path.exists()
    
    def delete(self, file_id: str, file_type: str) -> bool:
        """Delete an extraction"""
        if file_type not in self.TYPE_DIRS:
            return False
        
        file_path = self.TYPE_DIRS[file_type] / f"{file_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    def find_by_source_path(self, source_path: str) -> Optional[Dict[str, Any]]:
        """Find extraction by original file path"""
        source_path = str(Path(source_path).absolute())
        
        for extraction in self.get_all():
            if extraction.get("file_path") == source_path:
                return extraction
        
        return None
    
    def find_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Find extraction by file hash"""
        for extraction in self.get_all():
            if extraction.get("file_hash") == file_hash:
                return extraction
        
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get count of extractions by type"""
        stats = {}
        
        for file_type, dir_path in self.TYPE_DIRS.items():
            if dir_path.exists():
                stats[file_type] = len(list(dir_path.glob("*.json")))
            else:
                stats[file_type] = 0
        
        stats["total"] = sum(stats.values())
        return stats
