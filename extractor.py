"""
extractor.py — The Producer (Knowledge Map)  |  AI MINDS Hackathon
====================================================================
Watches  ./raw_inputs/  for .pdf, .txt, .docx files.
Splits text into ~1000-char chunks with 200-char overlap, runs per-chunk
LLM extraction (summary, entities, action_items), and outputs a
multi-level "Knowledge Map" JSON to  ./knowledge_vault/.

Usage:
    python extractor.py
"""

import os
import json
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timezone

import requests

# ── PDF support ──────────────────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# ── DOCX support ─────────────────────────────────────────────────────────────
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ── Watchdog ─────────────────────────────────────────────────────────────────
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
OLLAMA_URL    = "http://localhost:11434/api/chat"
OLLAMA_MODEL  = "qwen2.5:3b"

RAW_DIR       = "./raw_inputs"
OUTPUT_DIR    = "./knowledge_vault"
POLL_INTERVAL = 3
SUPPORTED_EXT = {".pdf", ".txt", ".docx"}

# ── Chunking parameters ─────────────────────────────────────────────────────
CHUNK_SIZE    = 1000    # ~1000 characters per chunk
CHUNK_OVERLAP = 200     # 200-character overlap between chunks

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Track already-processed files (path → mtime)
_processed: dict[str, float] = {}
_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
#  OLLAMA HELPER
# ══════════════════════════════════════════════════════════════════════════════
def chat_ollama(messages: list[dict], retries: int = 3) -> str:
    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=300)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as e:
            if attempt == retries:
                print(f"⚠️  Ollama error after {retries} attempts: {e}")
                return ""
            wait = 2 ** attempt
            print(f"⏳  Ollama retry {attempt}/{retries} in {wait}s …")
            time.sleep(wait)
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  TEXT EXTRACTION  (PDF / DOCX / TXT)
# ══════════════════════════════════════════════════════════════════════════════
def extract_pdf(path: str) -> tuple[str, int]:
    if not HAS_FITZ:
        print("❌  PyMuPDF not installed — pip install PyMuPDF")
        return "", 0
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages), len(pages)


def extract_docx(path: str) -> tuple[str, int]:
    if not HAS_DOCX:
        print("❌  python-docx not installed — pip install python-docx")
        return "", 0
    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs), len(paragraphs)


def extract_txt(path: str) -> tuple[str, int]:
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return text, 1


EXTRACTORS = {
    ".pdf":  extract_pdf,
    ".txt":  extract_txt,
    ".docx": extract_docx,
}


# ══════════════════════════════════════════════════════════════════════════════
#  RECURSIVE CHARACTER CHUNKING
# ══════════════════════════════════════════════════════════════════════════════
def recursive_chunk(text: str, chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into chunks of ~chunk_size characters with overlap.
    Tries to split on paragraph boundaries first, then sentences,
    then falls back to character-level splitting.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    # Try paragraph splits first
    separators = ["\n\n", "\n", ". ", " "]
    return _split_recursive(text, chunk_size, overlap, separators)


def _split_recursive(text: str, chunk_size: int, overlap: int,
                     separators: list[str]) -> list[str]:
    """Recursively split text using progressively finer separators."""
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    # Find the best separator (first one that actually appears)
    sep = ""
    for s in separators:
        if s in text:
            sep = s
            break

    if not sep:
        # Hard split at chunk_size as last resort
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end].strip())
            start = end - overlap
            if start >= len(text):
                break
        return [c for c in chunks if c]

    # Split on the chosen separator
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
            # If a single part is too long, recurse with finer separators
            if len(part) > chunk_size:
                remaining_seps = separators[separators.index(sep) + 1:]
                if remaining_seps:
                    sub_chunks = _split_recursive(part, chunk_size, overlap, remaining_seps)
                    chunks.extend(sub_chunks)
                    current = ""
                else:
                    # Hard split
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

    # Apply overlap: merge short trailing pieces back
    final = []
    for c in chunks:
        if c:
            final.append(c)

    # Re-add overlap between chunks
    if overlap > 0 and len(final) > 1:
        overlapped = [final[0]]
        for i in range(1, len(final)):
            prev = final[i - 1]
            # Prepend last `overlap` chars of previous chunk
            overlap_text = prev[-overlap:] if len(prev) >= overlap else prev
            overlapped.append(overlap_text + final[i])
        return overlapped

    return final


# ══════════════════════════════════════════════════════════════════════════════
#  PER-CHUNK LLM EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════
_CHUNK_PROMPT = """\
You are a document analysis engine. Analyse the text chunk below and return \
a JSON object with EXACTLY these keys (no markdown, no explanation, only valid JSON):

{{
  "chunk_summary": "<2 sentence summary of THIS chunk only>",
  "entities": ["<people, dates, locations, organisations mentioned>"],
  "action_items": [
    {{"task": "<what>", "deadline": "<when or unknown>", "assignee": "<who or unknown>"}}
  ]
}}

Rules:
- chunk_summary must be exactly 2 sentences about THIS specific chunk.
- entities: list all people, dates, locations, and organisations mentioned.
- If no action items exist, return an empty list.
- Return ONLY valid JSON, nothing else.

CHUNK TEXT:
{text}
"""

_GLOBAL_PROMPT = """\
You are a document analysis engine. Based on the following text (first ~3000 chars \
of a document), return a JSON object with EXACTLY these keys:

{{
  "global_summary": "<3-4 sentence summary of the ENTIRE document>",
  "document_type": "<one of: report, proposal, meeting_notes, article, book, memo, research_paper, other>",
  "categories": ["<topic categories>"]
}}

Return ONLY valid JSON.

TEXT:
{text}
"""


def _parse_llm_json(raw: str) -> dict:
    """Best-effort parse of LLM output that may contain markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return {}


def extract_chunk_metadata(chunk_text: str, chunk_id: int) -> dict:
    """Send a single chunk to the LLM for per-chunk extraction."""
    prompt = _CHUNK_PROMPT.format(text=chunk_text[:2000])
    raw = chat_ollama([{"role": "user", "content": prompt}])
    if not raw:
        return _fallback_chunk(chunk_text)
    parsed = _parse_llm_json(raw)
    if not parsed:
        return _fallback_chunk(chunk_text)
    return {
        "chunk_summary": parsed.get("chunk_summary", ""),
        "entities":      parsed.get("entities", []),
        "action_items":  parsed.get("action_items", []),
    }


def extract_global_metadata(full_text: str) -> dict:
    """Send first portion of text to LLM for document-level metadata."""
    prompt = _GLOBAL_PROMPT.format(text=full_text[:3000])
    raw = chat_ollama([{"role": "user", "content": prompt}])
    if not raw:
        return _fallback_global(full_text)
    parsed = _parse_llm_json(raw)
    if not parsed:
        return _fallback_global(full_text)
    return {
        "global_summary": parsed.get("global_summary", ""),
        "document_type":  parsed.get("document_type", "other"),
        "categories":     parsed.get("categories", ["uncategorised"]),
    }


def _fallback_chunk(chunk_text: str) -> dict:
    words = chunk_text.split()
    return {
        "chunk_summary": " ".join(words[:40]) + ("…" if len(words) > 40 else ""),
        "entities": [],
        "action_items": [],
    }


def _fallback_global(full_text: str) -> dict:
    words = full_text.split()
    return {
        "global_summary": " ".join(words[:80]) + ("…" if len(words) > 80 else ""),
        "document_type": "other",
        "categories": ["uncategorised"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD KNOWLEDGE MAP JSON  &  SAVE
# ══════════════════════════════════════════════════════════════════════════════
def build_knowledge_map(
    full_text: str,
    source_path: str,
    page_count: int,
) -> dict:
    """
    Build the multi-level Knowledge Map JSON:
      1. Chunk the text locally (fast, no LLM)
      2. Extract global metadata (1 LLM call)
      3. Extract per-chunk metadata (1 LLM call per chunk)
    """
    # ── Step 1: Local chunking ───────────────────────────────────────────
    chunks = recursive_chunk(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
    total_chunks = len(chunks)
    print(f"   📐  Split into {total_chunks} chunks "
          f"({CHUNK_SIZE} chars, {CHUNK_OVERLAP} overlap)")

    # ── Step 2: Global metadata (1 LLM call) ────────────────────────────
    print(f"   🌐  Extracting global metadata …")
    global_meta = extract_global_metadata(full_text)

    # ── Step 3: Per-chunk extraction (N LLM calls) ──────────────────────
    sections = []
    for i, chunk in enumerate(chunks):
        print(f"   🔍  Chunk {i + 1}/{total_chunks} …", end=" ", flush=True)
        chunk_meta = extract_chunk_metadata(chunk, i)
        sections.append({
            "chunk_id":      i,
            "chunk_text":    chunk,
            "chunk_summary": chunk_meta.get("chunk_summary", ""),
            "entities":      chunk_meta.get("entities", []),
            "action_items":  chunk_meta.get("action_items", []),
        })
        print("✓")

    # ── Assemble Knowledge Map ───────────────────────────────────────────
    return {
        "document_metadata": {
            "file_path":     source_path,
            "total_pages":   page_count,
            "total_chunks":  total_chunks,
            "chunk_size":    CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "extracted_at":  datetime.now(timezone.utc).isoformat(),
        },
        "global_summary":  global_meta.get("global_summary", ""),
        "document_type":   global_meta.get("document_type", "other"),
        "categories":      global_meta.get("categories", []),
        "sections":        sections,
    }


def save_json(data: dict, source_name: str):
    stem = Path(source_name).stem
    h = hashlib.md5(
        (data.get("global_summary", "") + str(data.get("document_metadata", {})))
        .encode()
    ).hexdigest()[:8]
    out_name = f"{stem}_{h}.json"
    out_path = Path(OUTPUT_DIR) / out_name
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"📦  Saved → {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  PROCESS A SINGLE FILE
# ══════════════════════════════════════════════════════════════════════════════
def process_file(path: str):
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXT:
        return

    mtime = p.stat().st_mtime
    with _lock:
        if _processed.get(str(p)) == mtime:
            return
        _processed[str(p)] = mtime

    print(f"\n{'='*55}")
    print(f"📄  Processing {p.name}")
    print(f"{'='*55}")

    # Step 1 — Raw text extraction (local, fast)
    extractor_fn = EXTRACTORS.get(ext)
    if not extractor_fn:
        print(f"⚠️  No extractor for {ext}")
        return

    try:
        full_text, page_count = extractor_fn(str(p))
    except Exception as e:
        print(f"❌  Extraction failed for {p.name}: {e}")
        return

    if not full_text.strip():
        print(f"⚠️  Empty content in {p.name}, skipping")
        return

    print(f"   📝  {len(full_text)} chars, {page_count} page(s)")

    # Step 2 — Build Knowledge Map (chunking + LLM calls)
    knowledge_map = build_knowledge_map(full_text, str(p), page_count)

    # Step 3 — Save
    save_json(knowledge_map, p.name)

    n_actions = sum(len(s.get("action_items", [])) for s in knowledge_map["sections"])
    n_entities = sum(len(s.get("entities", [])) for s in knowledge_map["sections"])
    print(f"✅  {p.name} → {len(knowledge_map['sections'])} chunks, "
          f"{n_entities} entities, {n_actions} action items\n")


# ══════════════════════════════════════════════════════════════════════════════
#  WATCHER
# ══════════════════════════════════════════════════════════════════════════════
if HAS_WATCHDOG:
    class _RawHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                time.sleep(0.5)
                process_file(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                time.sleep(0.5)
                process_file(event.src_path)


def start_watcher():
    if HAS_WATCHDOG:
        observer = Observer()
        observer.schedule(_RawHandler(), RAW_DIR, recursive=False)
        observer.daemon = True
        observer.start()
        print(f"👁️  Watching {RAW_DIR}/ (watchdog)")
    else:
        def _poll():
            seen: dict[str, float] = {}
            while True:
                try:
                    for p in Path(RAW_DIR).iterdir():
                        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
                            mt = p.stat().st_mtime
                            if str(p) not in seen or seen[str(p)] != mt:
                                seen[str(p)] = mt
                                process_file(str(p))
                except Exception:
                    pass
                time.sleep(POLL_INTERVAL)
        threading.Thread(target=_poll, daemon=True).start()
        print(f"👁️  Watching {RAW_DIR}/ (polling)")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  📥  AI MINDS Extractor — Knowledge Map Builder")
    print(f"  Model      : {OLLAMA_MODEL}")
    print(f"  Input      : {RAW_DIR}/")
    print(f"  Output     : {OUTPUT_DIR}/")
    print(f"  Chunk size : {CHUNK_SIZE} chars, {CHUNK_OVERLAP} overlap")
    print("=" * 55)

    # Process existing files
    for p in sorted(Path(RAW_DIR).iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
            process_file(str(p))

    # Start live watcher
    start_watcher()

    print("\n✅  Extractor running. Drop .pdf / .txt / .docx into "
          f"{RAW_DIR}/")
    print("    Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋  Extractor stopped.")


if __name__ == "__main__":
    main()
