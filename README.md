# Dalanda - AI Personal Memory Assistant

An intelligent RAG-powered personal assistant that converts your files (images, audio, documents) into a searchable memory and answers questions about your data with verified, grounded responses.

## Overview

**Dalanda** is a multi-agent AI system that:

1. **Ingests** files from multiple modalities (images, audio, documents)
2. **Extracts** meaningful information using specialized AI models
3. **Stores** extractions as JSON + FAISS vector embeddings
4. **Enables** semantic search with intelligent filters
5. **Answers** questions using a RAG pipeline with multi-agent verification
6. **Provides** a modern React chat interface with voice input

---

## Key Features

### Multi-Modal File Processing
- **Images**: Vision analysis using Moondream (via Ollama) - extracts objects, scenes, text, people
- **Audio**: Transcription using OpenAI Whisper - supports MP3, WAV, M4A, OGG, FLAC, WebM
- **Documents**: Text extraction using PyMuPDF + Qwen2.5 - supports PDF, DOCX, TXT, MD

### Intelligent RAG Pipeline
- **Orchestrator**: Rule-based query parsing (no LLM overhead, ~5ms)
  - Extracts date filters ("last week", "yesterday", "2 days ago")
  - Extracts file type filters ("photos", "documents", "audio")
  - Detects personal queries vs. content queries
- **Vector Search**: FAISS-powered semantic search with metadata filtering
- **Passage Extraction**: Smart passage selection based on query word density

### Multi-Agent Architecture
- **Text Agent (Phi-3.5)**: Generates answers from retrieved passages with citations
- **Verifier Agent (Llama-3.2)**: Validates answers are grounded, assigns confidence scores
- **Conversation Memory**: Sliding window (5 Q&A pairs) for context continuity

### Modern Web Interface
- React + Vite frontend with Tailwind CSS
- 6 customizable themes (Ocean, Sunset, Forest, Galaxy, Fire, Midnight)
- Voice input support using Whisper
- Animated particle backgrounds
- Conversation history with persistence
- Real-time status indicators (thinking, verifying)

### File Watcher
- Auto-processes new files dropped into monitored folders
- Supports watching multiple directories
- Real-time extraction and vectorization

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                   (React + Vite + Tailwind)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/REST
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                             │
│                          (api.py)                                   │
├─────────────────────────────────────────────────────────────────────┤
│  /chat     - Main chat endpoint                                     │
│  /voice    - Voice input (Whisper transcription)                    │
│  /sources  - List available sources                                 │
│  /upload   - File upload for processing                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CHAT AGENT PIPELINE                          │
│                        (chat_agent.py)                              │
├─────────────────────────────────────────────────────────────────────┤
│  1. ORCHESTRATOR  →  Parse query, extract filters (rule-based)      │
│  2. RETRIEVER     →  Vector search + passage extraction             │
│  3. TEXT AGENT    →  Generate answer (Phi-3.5)                      │
│  4. VERIFIER      →  Check grounding (Llama-3.2)                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│  FAISS Vector Store     │  JSON Extractions      │  Embeddings      │
│  (index.faiss)          │  (data/extractions/)   │  (all-MiniLM)    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
dalanda/
├── api.py                        # FastAPI backend server
├── chat_agent.py                 # Main RAG pipeline with multi-agent
├── main.py                       # CLI entry point for batch processing
├── query_cli.py                  # Interactive CLI for testing queries
├── watch_demo.py                 # File watcher for auto-processing
├── extractor.py                  # Unified extractor interface
├── requirements.txt              # Python dependencies
├── setup.bat                     # Windows setup script
│
├── config/
│   └── settings.py               # Configuration (paths, extensions, limits)
│
├── extractors/                   # Multi-modal extractors
│   ├── base_extractor.py         # Abstract base class
│   ├── image_extractor.py        # Moondream vision model
│   ├── audio_extractor.py        # Whisper transcription
│   └── document_extractor.py     # PDF/DOCX/TXT extraction
│
├── models/                       # Model prompts and configs
│   ├── image/prompts.py
│   ├── audio/prompts.py
│   └── document/prompts.py
│
├── query/                        # Query pipeline components
│   ├── orchestrator.py           # Query parsing & filter extraction
│   ├── retriever.py              # Text Agent (Phi-3.5)
│   ├── verifier.py               # Verifier Agent (Llama-3.2)
│   └── memory.py                 # Conversation memory (sliding window)
│
├── storage/                      # Data persistence
│   ├── json_store.py             # JSON file operations
│   └── schemas.py                # Data schemas
│
├── vectorizer/                   # Vector embeddings & search
│   ├── embedder.py               # Sentence-Transformers embeddings
│   └── vector_store.py           # FAISS index management
│
├── watchers/
│   └── file_watcher.py           # File system monitoring
│
├── data/                         # Generated data
│   ├── extractions/              # JSON extraction files
│   │   ├── images/
│   │   ├── audio/
│   │   └── documents/
│   └── vectors/                  # FAISS index + mapping
│       ├── index.faiss
│       └── index_map.json
│
├── tests/                        # Test files
│   ├── test_images/
│   ├── test_audio/
│   └── test_docs/
│
└── user-interface/               # React frontend
    ├── src/
    │   ├── App.jsx               # Main app component
    │   ├── components/
    │   │   ├── MessageBubble.jsx
    │   │   ├── Sidebar.jsx
    │   │   ├── VoiceButton.jsx
    │   │   ├── TypingIndicator.jsx
    │   │   └── ParticleBackground.jsx
    │   └── services/
    │       ├── chatService.js     # API client
    │       └── conversationStorage.js
    ├── package.json
    └── vite.config.js
```

---

##  Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama (for LLM inference)

### 1. Clone & Setup

```bash
git clone https://github.com/lili12388/dalanda.git
cd dalanda

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Install Ollama & Models

```bash
# Install Ollama from https://ollama.ai/download

# Pull required models
ollama pull phi3.5      # Text Agent (~2.2GB)
ollama pull llama3.2    # Verifier (~2.0GB)
ollama pull moondream   # Image extraction (~1.7GB)
ollama pull qwen2.5:3b  # Document analysis (~2GB)

# Start Ollama server (keep running)
ollama serve
```

### 3. Setup Frontend

```bash
cd user-interface
npm install
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
python api.py
# Server starts on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd user-interface
npm run dev
# UI available at http://localhost:5173
```

### 5. (Optional) Start File Watcher

```bash
# Watch Downloads folder
python watch_demo.py

# Watch custom folder
python watch_demo.py "C:\path\to\folder"
```

---

##  Usage

### Chat Interface
1. Open http://localhost:5173 in your browser
2. Type questions about your files
3. Use voice input by clicking the microphone button
4. View confidence scores and source citations

### Example Queries
- "What documents did I download last week?"
- "Summarize the PDF about machine learning"
- "What's in my recent photos?"
- "Find audio recordings from yesterday"

### CLI Mode
```bash
# Interactive query mode
python query_cli.py

# Process files in a folder
python main.py process /path/to/folder

# Process specific file type
python main.py process /path/to/folder --type image
```

---

##  API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send message and get response |
| `/voice` | POST | Upload audio for transcription |
| `/sources` | GET | List all indexed sources |
| `/upload` | POST | Upload file for processing |
| `/health` | GET | Health check |

### Example API Call
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What files did I add today?", "session_id": "user1"}'
```

---

##  Models Used

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| Text Agent | Phi-3.5 | ~2.2GB | Answer generation |
| Verifier | Llama-3.2 | ~2.0GB | Answer verification |
| Image Extraction | Moondream | ~1.7GB | Vision analysis |
| Document Analysis | Qwen2.5:3b | ~2GB | Text summarization |
| Audio Transcription | Whisper (base) | ~150MB | Speech-to-text |
| Embeddings | all-MiniLM-L6-v2 | ~90MB | Vector embeddings |

---

##  Tech Stack

**Backend:**
- Python 3.10+
- FastAPI + Uvicorn
- FAISS (vector search)
- Sentence-Transformers
- PyMuPDF, python-docx
- OpenAI Whisper
- Ollama (LLM inference)

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- Framer Motion
- Lucide Icons

---

##  Configuration

Edit `config/settings.py` to customize:
- Supported file extensions
- Max file sizes
- Extraction paths
- Vector store settings

---

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

##  License

This project was created for the AI Minds Hackathon.

---
