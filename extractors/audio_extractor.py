"""
Audio Extractor - Extracts information from audio files using Whisper.

╔═══════════════════════════════════════════════════════════════════════════╗
║   OWNER: [TEAM MEMBER 2]                                                  ║
║   MODEL: Whisper (base) - fast, runs on CPU/GPU                           ║
║   Run: pip install openai-whisper                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝

Supported formats: .mp3, .wav, .m4a, .ogg, .flac, .webm
"""

import time
import warnings
from pathlib import Path
from typing import Dict, Any, Tuple

from extractors.base_extractor import BaseExtractor
from config.settings import AUDIO_EXTENSIONS

warnings.filterwarnings("ignore")

# Whisper model size - "tiny", "base", "small", "medium"
# tiny: ~1GB VRAM, fast, less accurate
# base: ~1GB VRAM, good balance (recommended)
# small: ~2GB VRAM, better accuracy
WHISPER_SIZE = "base"


class AudioExtractor(BaseExtractor):
    """
    Extract transcripts and metadata from audio files using Whisper.
    
    Pipeline:
    1. Whisper: Audio → Transcript + Language detection
    2. Generate summary from first ~500 chars
    3. Create embedding_text for vector search
    """
    
    SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS
    _whisper_model = None  # Cached across instances
    
    def __init__(self, whisper_size: str = WHISPER_SIZE):
        super().__init__()
        self.whisper_size = whisper_size
    
    def load_model(self):
        """Load Whisper model (cached)"""
        if AudioExtractor._whisper_model is None:
            import whisper
            print(f"Loading Whisper ({self.whisper_size})...")
            AudioExtractor._whisper_model = whisper.load_model(self.whisper_size)
            print("✓ Whisper loaded!")
    
    def unload_model(self):
        """Unload Whisper to free memory"""
        if AudioExtractor._whisper_model is not None:
            del AudioExtractor._whisper_model
            AudioExtractor._whisper_model = None
            print("✓ Whisper unloaded")
    
    def _get_duration(self, file_path: str) -> float:
        """Get audio duration in seconds using ffprobe"""
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True, text=True, timeout=10
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def _transcribe(self, file_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        result = AudioExtractor._whisper_model.transcribe(
            file_path,
            language=None,  # Auto-detect
            task="transcribe"
        )
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "segments": len(result.get("segments", []))
        }
    
    def _create_summary(self, transcript: str, max_len: int = 200) -> str:
        """Create summary from transcript (first N chars, clean)"""
        if not transcript:
            return ""
        # Clean and truncate
        summary = transcript.replace("\n", " ").strip()
        if len(summary) > max_len:
            summary = summary[:max_len].rsplit(" ", 1)[0] + "..."
        return summary
    
    def extract(self, file_path: str, return_time: bool = True):
        """
        Extract information from audio file.
        
        Args:
            file_path: Path to audio file
            return_time: If True, return (result, elapsed_seconds)
        
        Returns:
            Extraction dictionary compatible with JSONStore and VectorStore
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.is_supported_file(file_path):
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        self.load_model()
        
        metadata = self.get_file_metadata(file_path)
        file_id = self.generate_file_id(file_path, "aud")
        
        start_time = time.time()
        
        # Transcribe
        transcription = self._transcribe(file_path)
        transcript = transcription["text"]
        language = transcription["language"]
        
        # Get duration
        duration = self._get_duration(file_path)
        
        # Detect topics from keywords
        topics = []
        topic_keywords = {
            "meeting": ["meeting", "agenda", "discuss", "action item"],
            "music": ["song", "music", "melody", "beat"],
            "lecture": ["lecture", "lesson", "class", "professor"],
            "conversation": ["said", "asked", "replied", "told"],
            "voice_memo": ["reminder", "note to self", "remember"],
        }
        text_lower = transcript.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
        
        # Sentiment (simple)
        sentiment = "neutral"
        if any(w in text_lower for w in ["happy", "great", "excellent", "love", "wonderful"]):
            sentiment = "positive"
        elif any(w in text_lower for w in ["sad", "angry", "terrible", "hate", "awful"]):
            sentiment = "negative"
        
        extracted = {
            "transcript": transcript,  # Full transcript - passage finder handles search
            "language": language,
            "duration_seconds": round(duration, 1),
            "topics": topics,
            "sentiment": sentiment,
            "segment_count": transcription["segments"]
        }
        
        # Create rich embedding text for vector search
        # Use more transcript for longer recordings to capture key points
        transcript_limit = min(1000, max(500, len(transcript) // 3))  # Up to 1000 chars
        filename_words = path.stem.replace("_", " ").replace("-", " ")
        embedding_parts = [transcript[:transcript_limit]]  # More transcript for context
        if topics:
            embedding_parts.append(f"Topics: {' '.join(topics)}")
        embedding_parts.append(f"Filename: {filename_words}")
        embedding_parts.append(f"Language: {language}")
        embedding_text = " ".join(embedding_parts)[:1200]  # Expanded to 1200 chars
        
        result = {
            "file_id": file_id,
            "file_path": metadata["file_path"],
            "file_type": "audio",
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
    import hashlib
    from storage.json_store import JSONStore
    from vectorizer.vector_store import VectorStore
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m extractors.audio_extractor <audio_path>")
        print("  python -m extractors.audio_extractor <folder_path>")
        print("\nOptions:")
        print("  --force    Re-extract even if already processed")
        sys.exit(1)
    
    force = "--force" in sys.argv
    input_path = Path(sys.argv[1])
    extractor = AudioExtractor()
    json_store = JSONStore()
    vector_store = VectorStore()
    
    # Collect audio files
    audio_files = []
    if input_path.is_dir():
        for ext in AUDIO_EXTENSIONS:
            audio_files.extend(input_path.glob(f"*{ext}"))
            audio_files.extend(input_path.glob(f"*{ext.upper()}"))
        audio_files = sorted(set(audio_files))
    elif input_path.is_file():
        audio_files = [input_path]
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    if not audio_files:
        print("No audio files found!")
        sys.exit(1)
    
    print(f"Processing {len(audio_files)} audio files...")
    
    success = 0
    skipped = 0
    total_start = time.time()
    
    for i, audio_path in enumerate(audio_files, 1):
        try:
            # Check if already processed (skip duplicates)
            if not force:
                file_hash = hashlib.md5(audio_path.read_bytes()).hexdigest()
                existing = json_store.find_by_hash(file_hash)
                if existing:
                    print(f"[{i}/{len(audio_files)}] ⏭ {audio_path.name} (already processed)")
                    skipped += 1
                    continue
            
            result, elapsed = extractor.extract(str(audio_path))
            
            # Save JSON
            json_path = json_store.save(result)
            
            # Add to vector store
            vector_store.add(result)
            
            duration = result["extraction"].get("duration_seconds", 0)
            print(f"[{i}/{len(audio_files)}] ✓ {audio_path.name} ({elapsed:.1f}s, {duration:.0f}s audio)")
            success += 1
        except Exception as e:
            print(f"[{i}/{len(audio_files)}] ✗ {audio_path.name}: {e}")
    
    # Save vector index
    if success > 0:
        vector_store.save()
    
    total_time = time.time() - total_start
    print(f"\n✓ Processed: {success}/{len(audio_files)} in {total_time:.1f}s")
    if skipped > 0:
        print(f"  Skipped: {skipped} (already processed)")
    print(f"  Vectors indexed: {vector_store.index.ntotal} total")
