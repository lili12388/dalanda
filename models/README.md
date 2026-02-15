# Models Directory

Each team member downloads their model to their respective folder.

```
models/
├── image/           <- Laith: Qwen2.5-VL-3B-Instruct
├── audio/           <- Team Member 2: Whisper + Qwen2.5-3B  
└── document/        <- Team Member 3: Qwen2.5-3B
```

## Quick Start

1. Go to your folder: `cd models/{your_folder}`
2. Read the README.md for download instructions
3. Import the system prompt from `prompts.py`

## System Prompts

Each folder has a `prompts.py` file with ready-to-use prompts:

```python
# In your extractor:
from models.image.prompts import IMAGE_SYSTEM_PROMPT
from models.audio.prompts import AUDIO_SYSTEM_PROMPT
from models.document.prompts import DOCUMENT_SYSTEM_PROMPT
```

## Model Storage Options

### Option 1: Local folder (Recommended for hackathon)
Download directly to `models/{type}/` folder. Everything stays in project.

### Option 2: HuggingFace cache (Default)
Models auto-download to `~/.cache/huggingface/`. Shared across projects.

## VRAM Requirements

| Model | Size | VRAM (fp16) |
|-------|------|-------------|
| Qwen2.5-VL-3B | 3B | ~6-8 GB |
| Whisper small | 244M | ~2 GB |
| Qwen2.5-3B | 3B | ~6-8 GB |

**Tip:** Run models sequentially (load → use → unload) to fit in 8GB VRAM.
