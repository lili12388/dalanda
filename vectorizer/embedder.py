"""
Embedder - Generates text embeddings using sentence-transformers.

SHARED FILE - Do not modify unless discussed with team.

Uses BGE-small-en-v1.5 for fast, quality embeddings.
"""

import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL, EMBEDDING_DIMENSION


class Embedder:
    """
    Generates embeddings from text using sentence-transformers.
    
    Model: BAAI/bge-small-en-v1.5
    Dimension: 384
    
    Usage:
        embedder = Embedder()
        embedding = embedder.embed("Some text to embed")
        # embedding.shape = (384,)
    """
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self.model = None
        self.dimension = EMBEDDING_DIMENSION
    
    def load(self):
        """Load the embedding model into memory"""
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print("✓ Embedding model loaded!")
    
    def unload(self):
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
            print("✓ Embedding model unloaded")
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
        
        Returns:
            numpy array of shape (384,)
        """
        self.load()
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
        
        Returns:
            numpy array of shape (len(texts), 384)
        """
        self.load()
        embeddings = self.model.encode(
            texts, 
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100
        )
        return embeddings.astype(np.float32)
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.
        
        Returns:
            Similarity score between 0 and 1
        """
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        return float(np.dot(emb1, emb2))
