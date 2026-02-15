# AI Minds Hackathon - Personal Memory Assistant

An intelligent system that converts raw personal data into a structured, searchable memory.

## 🎯 Project Overview

This system:
1. **Ingests** files from multiple modalities (images, audio, documents)
2. **Extracts** meaningful information using AI models
3. **Stores** extractions as JSON + vector embeddings
4. **Enables** semantic search over your personal data
5. **Answers** questions with grounded, verified responses

---

## 📁 Project Structure

```
nxp_cup/
├── config/
│   └── settings.py              # Shared configuration
│
├── extractors/                   # 🔥 EACH TEAM MEMBER OWNS ONE FILE
│   ├── base_extractor.py        # Shared base class (DO NOT MODIFY)
│   ├── image_extractor.py       # 👤 LAITH
│   ├── audio_extractor.py       # 👤 TEAM MEMBER 2
│   └── document_extractor.py    # 👤 TEAM MEMBER 3
│
├── storage/                      # JSON file operations (SHARED)
│   ├── json_store.py            
│   └── schemas.py               
│
├── vectorizer/                   # Embedding & search (SHARED)
│   ├── embedder.py              
│   └── vector_store.py          
│
├── watchers/                     # File monitoring (SHARED)
│   └── file_watcher.py          
│
├── query/                        # Query pipeline (TODO: LATER)
│   ├── orchestrator.py          
│   ├── retriever.py             
│   └── verifier.py              
│
├── data/                         # Generated data (gitignored)
│   ├── extractions/             # JSON extraction files
│   └── vectors/                 # FAISS index
│
├── tests/                        # Test files
│
├── main.py                       # CLI entry point
└── requirements.txt              # Dependencies
```

---

## 👥 Team Assignments

| Team Member | File to Implement | Model |
|-------------|-------------------|-------|
| **Laith** | `extractors/image_extractor.py` | Qwen2.5-VL-3B |
| **Member 2** | `extractors/audio_extractor.py` | Whisper + Qwen2.5-3B |
| **Member 3** | `extractors/document_extractor.py` | PyMuPDF + Qwen2.5-3B |

### What Each Person Does:

1. Open your assigned file
2. Look for `TODO` comments
3. Implement the `extract()` method
4. Test with sample files
5. Commit and push

---

## 🚀 Getting Started

### 1. Clone & Setup

```bash
git clone https://github.com/Ahmedd-Ben-Salah/Ai-Minds-Hackathon.git
cd Ai-Minds-Hackathon

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Test Your Setup

```bash
# Check if everything imports correctly
python -c "from config.settings import ensure_directories; ensure_directories(); print('✓ Setup OK')"
```

### 3. Run Your Extractor Test

```bash
# For Laith (images):
python -m extractors.image_extractor

# For Member 2 (audio):
python -m extractors.audio_extractor

# For Member 3 (documents):
python -m extractors.document_extractor
```

---

## 📋 Output Format

Each extractor outputs JSON files with this structure:

```json
{
  "file_id": "img_a1b2c3d4",
  "file_path": "/path/to/original/file",
  "file_type": "image",
  "file_hash": "md5hash...",
  "extracted_at": "2026-02-14T10:30:00",
  
  "extraction": {
    "description": "...",
    "entities": { "people": [], "dates": [], ... },
    "action_items": [ ... ],
    ...
  },
  
  "embedding_text": "Text used for vector search..."
}
```

See `storage/schemas.py` for full schema details.

---

## 🔧 CLI Commands

```bash
# Extract all files from a folder
python main.py extract ./my_files

# Extract only images
python main.py extract ./pictures --type image

# Search your memory
python main.py search "meeting notes about project"

# Search with filters
python main.py search "contracts" --type document --top 10

# Show statistics
python main.py stats

# Rebuild vector index
python main.py rebuild
```

---

## 📂 Data Flow

```
Original Files          →    Extractors    →    JSON Files    →    Vectors
─────────────────            ──────────         ──────────         ───────
photo.jpg                    ImageExtractor     img_xxx.json       FAISS
voice_note.mp3               AudioExtractor     aud_xxx.json       index
report.pdf                   DocExtractor       doc_xxx.json
```

---

## ⚠️ Important Rules

1. **DO NOT modify shared files** without team discussion:
   - `base_extractor.py`
   - `json_store.py`
   - `schemas.py`
   - `embedder.py`
   - `vector_store.py`

2. **Follow the schema** in `storage/schemas.py`

3. **Test locally** before pushing

4. **Use `embedding_text`** - this is what gets vectorized for search!

---

## 🧪 Testing

Put test files in:
- `tests/test_images/` - for image testing
- `tests/test_audio/` - for audio testing
- `tests/test_docs/` - for document testing

---

## 📦 Models to Download

Each team member downloads their model:

```python
# Laith (Images):
# Qwen2.5-VL-3B downloads automatically via transformers

# Member 2 (Audio):
# Whisper downloads automatically via openai-whisper

# All (Embeddings):
# BGE-small downloads automatically via sentence-transformers
```

---

## 🤝 Contributing

1. Pull latest: `git pull origin main`
2. Create branch: `git checkout -b feature/your-name`
3. Make changes
4. Test: `python -m extractors.your_extractor`
5. Commit: `git commit -am "Implement X"`
6. Push: `git push origin feature/your-name`
7. Create Pull Request

---

## 📞 Contact

- **Repo**: https://github.com/Ahmedd-Ben-Salah/Ai-Minds-Hackathon
- **Team**: AI Minds

Good luck! 🚀
