"""
Document Extractor - Extracts information from PDFs, Word docs, and text files.

╔═══════════════════════════════════════════════════════════════════════════╗
║   OWNER: AI MINDS TEAM                                                    ║
║   MODEL: qwen2.5:3b via Ollama (text analysis) + PyMuPDF/python-docx      ║
║   Run: ollama pull qwen2.5:3b                                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

Supports: .pdf, .docx, .doc, .txt, .md, .rtf

OPTIMIZED Pipeline (fast mode):
1. Extract raw text (PyMuPDF for PDF, python-docx for Word)
2. Regex extraction for dates, money, emails, URLs (no LLM - instant)
3. Global analysis (summary, type, categories) - 1 LLM call
4. Batched chunk analysis for people/orgs/actions - ~2 LLM calls max
5. Merge results and save to data/extractions/documents/

Optimizations:
- Regex for structured entities (dates, money, emails, URLs) - NO LLM needed
- Batch 4 chunks per LLM call - reduces calls by 75%
- Lower token limit (256) - faster responses
- Skip per-chunk for small docs (< 1500 chars)

Dependencies:
    pip install PyMuPDF python-docx requests
"""

import json
import re
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple

from extractors.base_extractor import BaseExtractor
from config.settings import DOCUMENT_EXTENSIONS, MAX_DOCUMENT_PAGES

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:3b"  # Change this if using different model
OLLAMA_OPTIONS = {"num_predict": 1024, "temperature": 0.3}  # More tokens for comprehensive JSON

# Chunking: larger chunks + batching = fewer LLM calls
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
CHUNKS_PER_BATCH = 4  # Batch 4 chunks into 1 LLM call


# ══════════════════════════════════════════════════════════════════════════════
#  REGEX PATTERNS (extract without LLM - instant)
# ══════════════════════════════════════════════════════════════════════════════
REGEX_PATTERNS = {
    "dates": [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # 12/25/2026, 25-12-26
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # March 1, 2026
        r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',  # 1 March 2026
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?,? \d{4}\b',  # March 1st, 2026
    ],
    "money": [
        r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|k|K|M|B))?\b',  # $50,000, $1.5M
        r'(?:USD|EUR|GBP|CAD)\s*[\d,]+(?:\.\d{2})?\b',  # USD 1000
        r'\b[\d,]+(?:\.\d{2})?\s*(?:dollars|euros|pounds)\b',  # 1000 dollars
    ],
    "emails": [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    "urls": [
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        r'www\.[^\s<>"{}|\\^`\[\]]+',
    ],
    "phone": [
        r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
#  LLM PROMPTS (optimized - comprehensive summary from samples)
# ══════════════════════════════════════════════════════════════════════════════
# MAX characters to store - this is what the query agent uses to answer
MAX_STORED_TEXT = 500000  # 500KB - enough for most documents

GLOBAL_PROMPT = """\
You are analyzing a document to create a COMPREHENSIVE summary that captures ALL important information.
This summary will be used to answer user questions, so include ALL key facts, data, concepts, and details.

Return ONLY JSON:
{{
  "summary": "<DETAILED 5-10 sentence summary covering ALL main points, data, and conclusions>",
  "document_type": "<report|meeting_notes|email|article|notes|contract|invoice|textbook|manual|other>",
  "categories": ["<broad topic areas>"],
  "topics": ["<specific subjects covered - list ALL major topics>"],
  "key_points": ["<ALL important takeaways, facts, and conclusions - be comprehensive>"],
  "title": "<document title>",
  "people": ["<names of people mentioned>"],
  "organizations": ["<companies, institutions mentioned>"],
  "locations": ["<places mentioned>"]
}}

DOCUMENT SAMPLES (beginning, middle, end):
{text}
"""


class DocumentExtractor(BaseExtractor):
    """
    OPTIMIZED document extractor using qwen2.5:3b via Ollama.
    
    Speed optimizations:
    - Regex for dates/money/emails/URLs (no LLM needed)
    - Batch 4 chunks per LLM call (75% fewer calls)
    - Lower token limit (256 vs 512)
    - Skip per-chunk for small docs
    """
    
    SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS
    _ollama_checked = False  # Check once per session
    
    def __init__(self, model_name: str = OLLAMA_MODEL):
        super().__init__()
        self.model_name = model_name
        self.session = requests.Session()  # Reuse HTTP connection
    
    def load_model(self):
        """Verify Ollama is running with qwen2.5:3b (once per session)"""
        if DocumentExtractor._ollama_checked:
            return
        try:
            response = self.session.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                if not any(self.model_name in m for m in models):
                    raise RuntimeError(f"Model {self.model_name} not found. Run: ollama pull {self.model_name}")
                DocumentExtractor._ollama_checked = True
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Ollama not running. Start with: ollama serve")
    
    def unload_model(self):
        """Nothing to unload - Ollama manages model lifecycle"""
        pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  TEXT EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _extract_pdf_text(self, file_path: str) -> Tuple[str, int]:
        """Extract text from PDF using PyMuPDF"""
        if not HAS_FITZ:
            raise ImportError("PyMuPDF not installed. Run: pip install PyMuPDF")
        doc = fitz.open(file_path)
        pages = [page.get_text() for page in doc]
        page_count = len(doc)
        doc.close()
        return "\n\n".join(pages), page_count
    
    def _extract_docx_text(self, file_path: str) -> Tuple[str, int]:
        """Extract text from Word document"""
        if not HAS_DOCX:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs), len(paragraphs)
    
    def _extract_txt_text(self, file_path: str) -> Tuple[str, int]:
        """Extract text from plain text file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return text, 1
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  REGEX ENTITY EXTRACTION (FAST - no LLM needed)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _extract_regex_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract structured entities using regex - instant, no LLM"""
        entities = {}
        for entity_type, patterns in REGEX_PATTERNS.items():
            matches = set()
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                matches.update(found)
            entities[entity_type] = list(matches)[:20]  # Limit to 20 per type
        return entities
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  CHUNKING (larger chunks for batching)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _recursive_chunk(self, text: str, chunk_size: int = CHUNK_SIZE,
                         overlap: int = CHUNK_OVERLAP) -> List[str]:
        """Split text into overlapping chunks, trying natural boundaries first"""
        text = text.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]
        
        # Try paragraph → newline → sentence → word boundaries
        separators = ["\n\n", "\n", ". ", " "]
        return self._split_recursive(text, chunk_size, overlap, separators)
    
    def _split_recursive(self, text: str, chunk_size: int, overlap: int,
                         separators: List[str]) -> List[str]:
        """Recursively split using finer separators"""
        if len(text) <= chunk_size:
            return [text.strip()] if text.strip() else []
        
        sep = ""
        for s in separators:
            if s in text:
                sep = s
                break
        
        if not sep:
            # Hard split
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end].strip())
                start = end - overlap
                if start >= len(text):
                    break
            return [c for c in chunks if c]
        
        parts = text.split(sep)
        chunks = []
        current = ""
        
        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                if len(part) > chunk_size:
                    remaining = separators[separators.index(sep) + 1:] if sep in separators else []
                    if remaining:
                        chunks.extend(self._split_recursive(part, chunk_size, overlap, remaining))
                    else:
                        start = 0
                        while start < len(part):
                            end = min(start + chunk_size, len(part))
                            chunks.append(part[start:end].strip())
                            start = end - overlap
                    current = ""
                else:
                    current = part
        
        if current.strip():
            chunks.append(current.strip())
        
        return [c for c in chunks if c]
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  LLM HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _chat_ollama(self, prompt: str, retries: int = 2) -> str:
        """Send prompt to Ollama and get response"""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": OLLAMA_OPTIONS
        }
        for attempt in range(1, retries + 1):
            try:
                r = self.session.post(OLLAMA_URL, json=payload, timeout=90)
                r.raise_for_status()
                return r.json()["message"]["content"]
            except Exception as e:
                if attempt == retries:
                    print(f"  ⚠ Ollama error: {e}")
                    return ""
                time.sleep(2 ** attempt)
        return ""
    
    def _parse_llm_json(self, raw: str, debug: bool = False) -> dict:
        """Parse LLM output, handling markdown fences"""
        if debug:
            print(f"  [DEBUG] Raw LLM output ({len(raw)} chars): {raw[:200]}...")
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)
        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON from text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError as e:
                if debug:
                    print(f"  [DEBUG] JSON parse error: {e}")
                    print(f"  [DEBUG] Attempted to parse: {raw[start:start+200]}...")
        return {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  OPTIMIZED EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def extract(self, file_path: str, return_time: bool = True):
        """
        Extract information from document (OPTIMIZED).
        
        Optimizations applied:
        - Regex for dates/money/emails/URLs (no LLM)
        - Batched chunk processing (4 chunks per LLM call)
        - Lower token limit (256)
        
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
        start_time = time.time()
        
        metadata = self.get_file_metadata(file_path)
        file_id = self.generate_file_id(file_path, "doc")
        
        # ── Step 1: Extract raw text ─────────────────────────────────────────
        ext = path.suffix.lower()
        try:
            if ext == ".pdf":
                full_text, page_count = self._extract_pdf_text(file_path)
            elif ext in [".docx", ".doc"]:
                full_text, page_count = self._extract_docx_text(file_path)
            else:  # .txt, .md, .rtf
                full_text, page_count = self._extract_txt_text(file_path)
        except ImportError as e:
            raise RuntimeError(str(e))
        
        if not full_text.strip():
            raise ValueError(f"Empty document: {file_path}")
        
        word_count = len(full_text.split())
        
        # ── Step 2: Regex entities (INSTANT - no LLM) ────────────────────────
        print("  ⚡ Regex extraction (dates, money, emails, URLs)...")
        regex_entities = self._extract_regex_entities(full_text)
        
        # ── Step 3: Global analysis (1 LLM call) ─────────────────────────────
        # Sample from beginning, middle, and end for comprehensive coverage
        text_len = len(full_text)
        sample_size = 2500  # chars per sample
        
        if text_len <= 8000:
            # Small doc - use all
            sampled_text = full_text
            print("  🌐 Global analysis (full doc, 1 LLM call)...")
        else:
            # Large doc - sample strategically
            beginning = full_text[:sample_size]
            middle_start = (text_len // 2) - (sample_size // 2)
            middle = full_text[middle_start:middle_start + sample_size]
            end = full_text[-sample_size:]
            sampled_text = f"[BEGINNING]\n{beginning}\n\n[MIDDLE]\n{middle}\n\n[END]\n{end}"
            print(f"  🌐 Global analysis (sampled {len(sampled_text)} chars from {text_len} total, 1 LLM call)...")
        
        global_prompt = GLOBAL_PROMPT.format(text=sampled_text)
        global_raw = self._chat_ollama(global_prompt)
        global_data = self._parse_llm_json(global_raw)  # Debug disabled
        
        if not global_data:
            print("  ⚠ LLM JSON parsing failed, using fallback...")
            words = full_text.split()
            global_data = {
                "summary": " ".join(words[:100]) + "...",
                "document_type": "other",
                "categories": [],
                "topics": [],
                "key_points": [],
                "sentiment": "neutral",
                "title": path.stem,
                "people": [],
                "organizations": [],
                "locations": []
            }
        
        # ── Step 4: LLM entities extracted from global call ─────────────────
        # NO per-chunk LLM - we extract people/orgs/locations in the global call
        llm_entities = {
            "people": global_data.get("people", []),
            "organizations": global_data.get("organizations", []),
            "locations": global_data.get("locations", [])
        }
        all_action_items = []  # Action items extracted from key_points if needed
        print("  ⚡ Entities from global analysis (no extra LLM calls)")
        
        # ── Step 5: Merge all entities ────────────────────────────────────────
        all_entities = {
            "people": list(set(llm_entities["people"]))[:15],
            "organizations": list(set(llm_entities["organizations"]))[:15],
            "dates": regex_entities.get("dates", []),
            "money": regex_entities.get("money", []),
            "locations": list(set(llm_entities["locations"]))[:15],
            "urls": regex_entities.get("urls", []),
            "emails": regex_entities.get("emails", []),
        }
        
        # ── Step 6: Build result ─────────────────────────────────────────────
        summary = global_data.get("summary", "")
        key_points = global_data.get("key_points", [])
        topics = global_data.get("topics", [])
        
        # Build rich embedding text - include more content for better matching
        embedding_parts = [f"Document: {path.name}", summary]
        if key_points:
            embedding_parts.append("Key points: " + "; ".join(key_points[:10]))
        if topics:
            embedding_parts.append("Topics: " + ", ".join(topics[:10]))
        if all_entities["people"]:
            embedding_parts.append("People: " + ", ".join(all_entities["people"][:10]))
        if all_entities["organizations"]:
            embedding_parts.append("Organizations: " + ", ".join(all_entities["organizations"][:10]))
        # Add some actual content for keyword matching
        embedding_parts.append(full_text[:2000])
        embedding_text = " ".join(embedding_parts)[:4000]  # Larger embedding text
        
        result = {
            "file_id": file_id,
            "file_path": metadata["file_path"],
            "file_type": "document",
            "file_hash": metadata["file_hash"],
            "file_size_bytes": metadata["file_size_bytes"],
            "created_at": metadata["created_at"],
            "modified_at": metadata["modified_at"],
            "extracted_at": metadata["extracted_at"],
            
            "extraction": {
                "full_text": full_text[:MAX_STORED_TEXT],  # Store up to 500KB for accurate answers
                "summary": summary,
                "key_points": key_points,
                "document_metadata": {
                    "page_count": page_count,
                    "word_count": word_count,
                    "author": "",
                    "title": global_data.get("title", path.stem)
                },
                "structure": {
                    "headings": [],
                    "sections": []
                },
                "entities": all_entities,
                "tables": [],
                "action_items": all_action_items,
                "topics": topics,
                "categories": global_data.get("categories", []),
                "document_type": global_data.get("document_type", "other"),
                "sentiment": global_data.get("sentiment", "neutral"),
                "formality": "formal",
                "confidentiality": "internal"
            },
            
            "embedding_text": embedding_text,
            "embedding_id": f"vec_{file_id}"
        }
        
        elapsed = time.time() - start_time
        
        if return_time:
            return result, elapsed
        return result


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import hashlib
    from storage.json_store import JSONStore
    from vectorizer.vector_store import VectorStore
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m extractors.document_extractor <file_or_folder>")
        print("\nOptions:")
        print("  --force    Re-extract even if already processed")
        print("\nExamples:")
        print("  python -m extractors.document_extractor report.pdf")
        print("  python -m extractors.document_extractor ./my_docs/")
        sys.exit(1)
    
    force = "--force" in sys.argv
    input_path = Path(sys.argv[1])
    extractor = DocumentExtractor()
    json_store = JSONStore()
    vector_store = VectorStore()
    
    # Collect document files
    doc_files = []
    if input_path.is_dir():
        for ext in DOCUMENT_EXTENSIONS:
            doc_files.extend(input_path.glob(f"*{ext}"))
            doc_files.extend(input_path.glob(f"*{ext.upper()}"))
        doc_files = sorted(set(doc_files))
    elif input_path.is_file():
        doc_files = [input_path]
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    if not doc_files:
        print("No documents found!")
        sys.exit(1)
    
    print(f"Processing {len(doc_files)} documents...\n")
    
    success = 0
    skipped = 0
    total_start = time.time()
    
    for i, doc_path in enumerate(doc_files, 1):
        print(f"[{i}/{len(doc_files)}] 📄 {doc_path.name}")
        try:
            # Check if already processed (skip duplicates)
            if not force:
                file_hash = hashlib.md5(doc_path.read_bytes()).hexdigest()
                existing = json_store.find_by_hash(file_hash)
                if existing:
                    print(f"  ⏭ Already processed, skipping\n")
                    skipped += 1
                    continue
            
            result, elapsed = extractor.extract(str(doc_path))
            
            # Save JSON
            json_path = json_store.save(result)
            
            # Add to vector store
            vector_store.add(result)
            
            print(f"  ✓ {elapsed:.1f}s → {json_path.name}")
            print(f"    Summary: {result['extraction']['summary'][:80]}...")
            print(f"    Type: {result['extraction']['document_type']}")
            print(f"    Entities: {sum(len(v) for v in result['extraction']['entities'].values())} found")
            print(f"    Actions: {len(result['extraction']['action_items'])} items\n")
            success += 1
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    # Save vector index
    if success > 0:
        vector_store.save()
    
    total_time = time.time() - total_start
    print(f"✓ Processed: {success}/{len(doc_files)} in {total_time:.1f}s")
    if skipped > 0:
        print(f"  Skipped: {skipped} (already processed)")
    print(f"  Vectors indexed: {vector_store.index.ntotal} total")
