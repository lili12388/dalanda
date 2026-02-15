"""
Demo Watcher - Auto-processes new files for the demo.

Run this script, then download an image/document, and ask the bot about it!

Usage:
    python watch_demo.py                    # Watch default Downloads folder
    python watch_demo.py "C:\Custom\Path"   # Watch custom folder
"""

import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from watchers.file_watcher import FileWatcher
from config.settings import ensure_directories, IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, DOCUMENT_EXTENSIONS
from storage.json_store import JSONStore
from vectorizer.vector_store import VectorStore


def get_default_downloads():
    """Get the user's Downloads folder"""
    if os.name == 'nt':  # Windows
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                downloads = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                return downloads
        except:
            pass
        return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:  # Linux/Mac
        return os.path.join(os.path.expanduser('~'), 'Downloads')


def process_file(file_path: str):
    """Process a new file - extract and vectorize"""
    from extractors.image_extractor import ImageExtractor
    from extractors.audio_extractor import AudioExtractor
    from extractors.document_extractor import DocumentExtractor
    
    path = Path(file_path)
    ext = path.suffix.lower()
    
    print(f"\n{'='*60}")
    print(f"[PROCESSING] {path.name}")
    print('='*60)
    
    # Determine extractor
    if ext in IMAGE_EXTENSIONS:
        extractor = ImageExtractor()
        file_type = "image"
    elif ext in AUDIO_EXTENSIONS:
        extractor = AudioExtractor()
        file_type = "audio"
    elif ext in DOCUMENT_EXTENSIONS:
        extractor = DocumentExtractor()
        file_type = "document"
    else:
        print(f"  → Unsupported file type: {ext}")
        return
    
    try:
        # Check if already processed
        if extractor.is_already_extracted(file_path, file_type):
            print("  → Already processed, skipping")
            return
        
        # Extract
        print(f"  → Extracting {file_type}...")
        result = extractor.extract(file_path)
        extraction = result[0] if isinstance(result, tuple) else result
        
        # Save to JSON store
        json_store = JSONStore()
        json_path = json_store.save(extraction)
        print(f"  → Saved: {json_path.name}")
        
        # Vectorize
        print("  → Vectorizing...")
        vector_store = VectorStore()
        vector_store.add_batch([extraction])
        vector_store.save()
        
        # Cleanup
        extractor.unload_model()
        
        print(f"\n✓ Done! You can now ask the bot about: {path.name}")
        print("-"*60)
        
    except Exception as e:
        print(f"  → Error: {e}")


def main():
    ensure_directories()
    
    # Get folder to watch
    if len(sys.argv) > 1:
        watch_folder = sys.argv[1]
    else:
        watch_folder = get_default_downloads()
    
    print("\n" + "="*60)
    print("DALANDA - FILE WATCHER DEMO")
    print("="*60)
    print(f"\nWatching: {watch_folder}")
    print("\nDownload any image, audio, or document file and it will be")
    print("automatically processed and available for querying!")
    print("\nSupported formats:")
    print(f"  Images: {', '.join(IMAGE_EXTENSIONS)}")
    print(f"  Audio: {', '.join(AUDIO_EXTENSIONS)}")
    print(f"  Docs: {', '.join(DOCUMENT_EXTENSIONS)}")
    print("\nPress Ctrl+C to stop watching.")
    print("="*60 + "\n")
    
    # Setup watcher
    watcher = FileWatcher()
    watcher.add_folder(watch_folder)
    watcher.on_new_file = process_file
    
    # Start watching
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        watcher.stop()
        print("Done!")


if __name__ == "__main__":
    main()
