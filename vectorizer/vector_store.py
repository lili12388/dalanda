"""
Vector Store - FAISS-based vector storage and search.

SHARED FILE - Do not modify unless discussed with team.

Stores embeddings and maps them to file_ids for retrieval.
"""

import faiss
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import (
    FAISS_INDEX_PATH,
    INDEX_MAP_PATH,
    EMBEDDING_DIMENSION,
    ensure_directories
)
from vectorizer.embedder import Embedder
from storage.json_store import JSONStore


class VectorStore:
    """
    FAISS vector store for semantic search.
    
    Maps vectors to file_ids, which point to JSON extractions.
    
    Files:
        - data/vectors/index.faiss: The FAISS index
        - data/vectors/index_map.json: Maps vector_idx -> {file_id, file_type}
    
    Usage:
        store = VectorStore()
        
        # Add extractions
        store.add(extraction_dict)
        store.save()
        
        # Search
        results = store.search("my query", top_k=5)
    """
    
    def __init__(self):
        ensure_directories()
        self.embedder = Embedder()
        self.index = None
        self.index_map = {}  # str(vector_idx) -> {"file_id": "...", "file_type": "..."}
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index and map from disk"""
        if FAISS_INDEX_PATH.exists() and INDEX_MAP_PATH.exists():
            print("Loading existing vector index...")
            self.index = faiss.read_index(str(FAISS_INDEX_PATH))
            
            with open(INDEX_MAP_PATH, 'r') as f:
                self.index_map = json.load(f)
            
            print(f"✓ Loaded {self.index.ntotal} vectors")
        else:
            print("Creating new vector index...")
            # Use IndexFlatIP for cosine similarity (normalized vectors)
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
            self.index_map = {}
    
    def _save_index(self):
        """Save FAISS index and map to disk"""
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        
        with open(INDEX_MAP_PATH, 'w') as f:
            json.dump(self.index_map, f, indent=2)
    
    def add(self, extraction: Dict[str, Any]) -> int:
        """
        Add a single extraction to the vector store.
        
        Args:
            extraction: The extraction dictionary (must have embedding_text, file_id, file_type)
        
        Returns:
            The vector index assigned
        """
        embedding_text = extraction.get("embedding_text", "")
        file_id = extraction.get("file_id")
        file_type = extraction.get("file_type")
        
        if not embedding_text:
            raise ValueError("Extraction must have non-empty 'embedding_text'")
        if not file_id:
            raise ValueError("Extraction must have 'file_id'")
        
        # Check if already exists (by file_id)
        for idx, mapping in self.index_map.items():
            if mapping.get("file_id") == file_id:
                print(f"  Warning: {file_id} already in index, skipping...")
                return int(idx)
        
        # Generate embedding
        embedding = self.embedder.embed(embedding_text)
        embedding = embedding.reshape(1, -1)
        
        # Add to FAISS
        vector_idx = self.index.ntotal
        self.index.add(embedding)
        
        # Update map
        self.index_map[str(vector_idx)] = {
            "file_id": file_id,
            "file_type": file_type
        }
        
        return vector_idx
    
    def add_batch(self, extractions: List[Dict[str, Any]]) -> List[int]:
        """
        Add multiple extractions at once (more efficient).
        
        Args:
            extractions: List of extraction dictionaries
        
        Returns:
            List of vector indices assigned
        """
        if not extractions:
            return []
        
        # Filter out already indexed
        new_extractions = []
        existing_ids = {m["file_id"] for m in self.index_map.values()}
        
        for e in extractions:
            if e.get("file_id") not in existing_ids:
                new_extractions.append(e)
        
        if not new_extractions:
            print("  All extractions already indexed")
            return []
        
        # Generate embeddings
        texts = [e.get("embedding_text", "") for e in new_extractions]
        embeddings = self.embedder.embed_batch(texts)
        
        # Add to FAISS
        start_idx = self.index.ntotal
        self.index.add(embeddings)
        
        # Update map
        indices = []
        for i, extraction in enumerate(new_extractions):
            vector_idx = start_idx + i
            self.index_map[str(vector_idx)] = {
                "file_id": extraction.get("file_id"),
                "file_type": extraction.get("file_type")
            }
            indices.append(vector_idx)
        
        return indices
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        file_type: Optional[str] = None,
        min_score: float = 0.0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar items.
        
        Args:
            query: The search query
            top_k: Number of results to return
            file_type: Optional filter by type ("image", "audio", "document")
            min_score: Minimum similarity score (0 to 1)
            date_from: Optional filter - files created/modified after this date (ISO format or datetime)
            date_to: Optional filter - files created/modified before this date (ISO format or datetime)
        
        Returns:
            List of results, each containing:
                - file_id: The file ID
                - file_type: image/audio/document
                - score: Similarity score
                - extraction: The full extraction dict
        """
        from datetime import datetime
        
        if self.index.ntotal == 0:
            return []
        
        # Convert date strings to datetime if needed
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        
        # Embed query
        query_embedding = self.embedder.embed(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Search FAISS (get extra for filtering)
        search_k = min(top_k * 3, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, search_k)
        
        # Load JSON store
        json_store = JSONStore()
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            if score < min_score:
                continue
            
            mapping = self.index_map.get(str(idx))
            if not mapping:
                continue
            
            # Filter by file_type if specified
            if file_type and mapping["file_type"] != file_type:
                continue
            
            # Load the full extraction
            extraction = json_store.load(mapping["file_id"], mapping["file_type"])
            
            if extraction:
                # Date filtering
                if date_from or date_to:
                    # Get file date (prefer modified_at, fallback to created_at)
                    file_date_str = extraction.get("modified_at") or extraction.get("created_at")
                    if file_date_str:
                        try:
                            if isinstance(file_date_str, str):
                                file_date = datetime.fromisoformat(file_date_str.replace("Z", "+00:00"))
                            else:
                                file_date = file_date_str
                            
                            # Make naive datetime for comparison
                            if file_date.tzinfo:
                                file_date = file_date.replace(tzinfo=None)
                            
                            if date_from and file_date < date_from:
                                continue
                            if date_to and file_date > date_to:
                                continue
                        except:
                            pass  # Skip date filter if parsing fails
                
                results.append({
                    "file_id": mapping["file_id"],
                    "file_type": mapping["file_type"],
                    "score": float(score),
                    "extraction": extraction
                })
            
            if len(results) >= top_k:
                break
        
        return results
    
    def remove(self, file_id: str) -> bool:
        """
        Remove a file from the index.
        
        Note: FAISS doesn't support deletion, so we just remove from map.
        The vector stays in FAISS but won't be returned in searches.
        Call rebuild() periodically to clean up.
        """
        for idx, mapping in list(self.index_map.items()):
            if mapping.get("file_id") == file_id:
                del self.index_map[idx]
                return True
        return False
    
    def save(self):
        """Save index and map to disk"""
        self._save_index()
        print(f"✓ Saved {self.index.ntotal} vectors to disk")
    
    def rebuild(self):
        """
        Rebuild the entire index from JSON extractions.
        
        Use this to:
        - Clean up deleted entries
        - Fix corruption
        - Re-embed with new model
        """
        print("Rebuilding vector index from extractions...")
        
        # Reset index
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.index_map = {}
        
        # Load all extractions
        json_store = JSONStore()
        extractions = json_store.get_all()
        
        if not extractions:
            print("No extractions found")
            self.save()
            return
        
        # Add all
        self.add_batch(extractions)
        self.save()
        
        print(f"✓ Rebuilt index with {self.index.ntotal} vectors")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        type_counts = {}
        for mapping in self.index_map.values():
            t = mapping.get("file_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total_vectors": self.index.ntotal,
            "indexed_files": len(self.index_map),
            "by_type": type_counts,
            "dimension": EMBEDDING_DIMENSION,
            "index_path": str(FAISS_INDEX_PATH),
            "map_path": str(INDEX_MAP_PATH)
        }
