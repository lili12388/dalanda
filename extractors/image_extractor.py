"""
Image Extractor - Simple extraction using moondream via Ollama

╔═══════════════════════════════════════════════════════════════════════════╗
║   OWNER: LAITH                                                            ║
║   MODEL: moondream (1.7GB - fast on 4GB VRAM)                             ║
║   Run: ollama pull moondream                                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import base64
import json
import re
import requests
import time
from pathlib import Path
from typing import Dict, Any, List

from extractors.base_extractor import BaseExtractor
from config.settings import IMAGE_EXTENSIONS, MAX_IMAGE_SIZE
from models.image.prompts import OLLAMA_MODEL, OLLAMA_OPTIONS


class ImageExtractor(BaseExtractor):
    """Simple image extraction using moondream only."""
    
    SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MAX_SIZE = 1024  # Resize large images for speed
    _ollama_checked = False  # Check only once per session
    
    def __init__(self, model_name: str = OLLAMA_MODEL):
        super().__init__()
        self.model_name = model_name
        self.session = requests.Session()  # Reuse connection
    
    def load_model(self):
        """Verify Ollama is running (once per session)"""
        if ImageExtractor._ollama_checked:
            return
        try:
            response = self.session.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                if not any(self.model_name in m for m in models):
                    raise RuntimeError(f"Model {self.model_name} not found. Run: ollama pull {self.model_name}")
                ImageExtractor._ollama_checked = True
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Ollama not running. Start with: ollama serve")
    
    def unload_model(self):
        pass
    
    def _encode_image(self, file_path: str) -> str:
        """Encode image to base64 - resize large images for speed."""
        from PIL import Image
        import io
        
        with Image.open(file_path) as img:
            # Resize if larger than MAX_SIZE
            if max(img.size) > self.MAX_SIZE:
                ratio = self.MAX_SIZE / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=70)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _query_ollama(self, image_b64: str, prompt: str) -> str:
        """Query Ollama vision model"""
        response = self.session.post(
            self.OLLAMA_URL,
            json={
                "model": self.model_name,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": OLLAMA_OPTIONS
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "")
    
    def extract(self, file_path: str, return_time: bool = True):
        """
        Extract information from image using moondream.
        
        Returns:
            If return_time=True: (result_dict, elapsed_seconds)
            If return_time=False: result_dict only
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.is_supported_file(file_path):
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        self.load_model()
        
        metadata = self.get_file_metadata(file_path)
        file_id = self.generate_file_id(file_path, "img")
        
        start_time = time.time()
        image_b64 = self._encode_image(file_path)
        response = self._query_ollama(image_b64, "Describe this image in detail. What do you see?")
        
        # Detect type from response
        image_type = "other"
        type_kw = {
            "screenshot": ["screenshot", "desktop", "screen"],
            "photo": ["photo", "photograph", "portrait", "person"],
            "document": ["document", "pdf", "paper", "text"],
            "meme": ["meme"],
            "receipt": ["receipt", "invoice"],
            "diagram": ["diagram", "flowchart"],
            "chart": ["chart", "graph"],
            "map": ["map", "location"]
        }
        for t, kws in type_kw.items():
            if any(k in response.lower() for k in kws):
                image_type = t
                break
        
        # Get summary from last line
        lines = response.strip().split('\n')
        summary = lines[-1][:100] if lines else ""
        
        extracted = {
            "description": response[:500],
            "image_type": image_type,
            "sentiment": "neutral",
            "contains_text": "text" in response.lower(),
            "contains_faces": any(w in response.lower() for w in ["face", "person", "people", "portrait"]),
            "contains_handwriting": False,
            "visual_summary": summary
        }
        
        # Build rich embedding text (include filename context)
        filename_words = path.stem.replace("_", " ").replace("-", " ")
        embedding_text = f"{response[:300]} Filename: {filename_words} Type: {image_type}"
        
        result = {
            "file_id": file_id,
            "file_path": metadata["file_path"],
            "file_type": "image",
            "file_hash": metadata["file_hash"],
            "file_size_bytes": metadata["file_size_bytes"],
            "created_at": metadata["created_at"],
            "modified_at": metadata["modified_at"],
            "extracted_at": metadata["extracted_at"],
            "extraction": extracted,
            "embedding_text": embedding_text,
            "embedding_id": f"vec_{file_id}"
        }
        
        elapsed = time.time() - start_time
        
        if return_time:
            return result, elapsed
        return result


if __name__ == "__main__":
    import sys
    import os
    import hashlib
    from storage.json_store import JSONStore
    from vectorizer.vector_store import VectorStore
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m extractors.image_extractor <image_path>")
        print("  python -m extractors.image_extractor <folder_path>")
        print("\nOptions:")
        print("  --force    Re-extract even if already processed")
        sys.exit(1)
    
    force = "--force" in sys.argv
    input_path = Path(sys.argv[1])
    extractor = ImageExtractor()
    json_store = JSONStore()
    vector_store = VectorStore()
    
    # Collect image files
    image_files = []
    if input_path.is_dir():
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))
        image_files = sorted(set(image_files))
    elif input_path.is_file():
        image_files = [input_path]
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    if not image_files:
        print("No images found!")
        sys.exit(1)
    
    print(f"Processing {len(image_files)} images...")
    
    # Process all images
    success = 0
    skipped = 0
    total_start = time.time()
    
    for i, img_path in enumerate(image_files, 1):
        try:
            # Check if already processed (skip duplicates)
            if not force:
                file_hash = hashlib.md5(img_path.read_bytes()).hexdigest()
                existing = json_store.find_by_hash(file_hash)
                if existing:
                    print(f"[{i}/{len(image_files)}] ⏭ {img_path.name} (already processed)")
                    skipped += 1
                    continue
            
            result, elapsed = extractor.extract(str(img_path))
            
            # Save JSON
            json_path = json_store.save(result)
            
            # Add to vector store
            vector_store.add(result)
            
            print(f"[{i}/{len(image_files)}] ✓ {img_path.name} ({elapsed:.1f}s)")
            success += 1
        except Exception as e:
            print(f"[{i}/{len(image_files)}] ✗ {img_path.name}: {e}")
    
    # Save vector index
    if success > 0:
        vector_store.save()
    
    total_time = time.time() - total_start
    print(f"\n✓ Processed: {success}/{len(image_files)} in {total_time:.1f}s")
    if skipped > 0:
        print(f"  Skipped: {skipped} (already processed)")
    print(f"  Vectors indexed: {vector_store.index.ntotal} total")
