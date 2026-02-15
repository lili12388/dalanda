"""
Shared Configuration Settings
All team members use these settings.
"""

from pathlib import Path

# =============================================================================
# BASE PATHS
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

# =============================================================================
# EXTRACTION STORAGE (JSON files)
# =============================================================================
EXTRACTIONS_DIR = DATA_DIR / "extractions"
IMAGES_EXTRACTIONS_DIR = EXTRACTIONS_DIR / "images"
AUDIO_EXTRACTIONS_DIR = EXTRACTIONS_DIR / "audio"
DOCUMENTS_EXTRACTIONS_DIR = EXTRACTIONS_DIR / "documents"

# =============================================================================
# VECTOR STORAGE (FAISS)
# =============================================================================
VECTORS_DIR = DATA_DIR / "vectors"
FAISS_INDEX_PATH = VECTORS_DIR / "index.faiss"
INDEX_MAP_PATH = VECTORS_DIR / "index_map.json"

# =============================================================================
# TRACKED FOLDERS
# =============================================================================
TRACKED_FOLDERS_PATH = DATA_DIR / "tracked_folders.json"

# =============================================================================
# SUPPORTED FILE TYPES
# =============================================================================
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"}

# =============================================================================
# MODEL SETTINGS
# =============================================================================
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384

# Model paths (download these locally)
QWEN_VL_MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"      # For images
WHISPER_MODEL = "small"                              # For audio
QWEN_INSTRUCT_MODEL = "Qwen/Qwen2.5-3B-Instruct"   # For text analysis

# =============================================================================
# LIMITS
# =============================================================================
MAX_IMAGE_SIZE = 20 * 1024 * 1024   # 20 MB
MAX_AUDIO_DURATION = 600             # 10 minutes (seconds)
MAX_DOCUMENT_PAGES = 100


_dirs_created = False

def ensure_directories(silent: bool = False):
    """Create all required directories if they don't exist"""
    global _dirs_created
    
    directories = [
        DATA_DIR,
        EXTRACTIONS_DIR,
        IMAGES_EXTRACTIONS_DIR,
        AUDIO_EXTRACTIONS_DIR,
        DOCUMENTS_EXTRACTIONS_DIR,
        VECTORS_DIR,
        MODELS_DIR
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    if not silent and not _dirs_created:
        print(f"✓ All directories ready at: {DATA_DIR}")
        _dirs_created = True
