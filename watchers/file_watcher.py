"""
File Watcher - Monitors folders for new and modified files.

SHARED FILE - Implement together as a team.

Uses watchdog library to monitor file system events.
"""

import json
import time
from pathlib import Path
from typing import List, Callable, Dict, Any
from datetime import datetime

from config.settings import TRACKED_FOLDERS_PATH, ensure_directories


class FileWatcher:
    """
    Watches folders for file changes and triggers processing.
    
    Usage:
        watcher = FileWatcher()
        watcher.add_folder("/path/to/watch")
        watcher.on_new_file = my_callback
        watcher.start()
    
    TODO: Implement using watchdog library
    pip install watchdog
    """
    
    def __init__(self):
        ensure_directories()
        self.tracked_folders: List[str] = []
        self.on_new_file: Callable[[str], None] = None
        self.on_modified_file: Callable[[str], None] = None
        self.on_deleted_file: Callable[[str], None] = None
        self._running = False
        
        # Load previously tracked folders
        self._load_tracked_folders()
    
    def _load_tracked_folders(self):
        """Load tracked folders from config"""
        if TRACKED_FOLDERS_PATH.exists():
            with open(TRACKED_FOLDERS_PATH, 'r') as f:
                data = json.load(f)
                self.tracked_folders = data.get("folders", [])
    
    def _save_tracked_folders(self):
        """Save tracked folders to config"""
        with open(TRACKED_FOLDERS_PATH, 'w') as f:
            json.dump({
                "folders": self.tracked_folders,
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def add_folder(self, folder_path: str) -> bool:
        """
        Add a folder to watch.
        
        Args:
            folder_path: Path to the folder to watch
        
        Returns:
            True if added, False if already tracked or invalid
        """
        path = Path(folder_path).absolute()
        
        if not path.exists():
            print(f"Folder does not exist: {path}")
            return False
        
        if not path.is_dir():
            print(f"Not a directory: {path}")
            return False
        
        path_str = str(path)
        
        if path_str in self.tracked_folders:
            print(f"Already tracking: {path}")
            return False
        
        self.tracked_folders.append(path_str)
        self._save_tracked_folders()
        print(f"✓ Now tracking: {path}")
        return True
    
    def remove_folder(self, folder_path: str) -> bool:
        """Remove a folder from watch list"""
        path_str = str(Path(folder_path).absolute())
        
        if path_str in self.tracked_folders:
            self.tracked_folders.remove(path_str)
            self._save_tracked_folders()
            print(f"✓ Stopped tracking: {path_str}")
            return True
        
        return False
    
    def list_folders(self) -> List[str]:
        """Get list of tracked folders"""
        return self.tracked_folders.copy()
    
    def start(self):
        """
        Start watching for file changes using watchdog library.
        """
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        from config.settings import (
            IMAGE_EXTENSIONS, 
            AUDIO_EXTENSIONS, 
            DOCUMENT_EXTENSIONS
        )
        
        all_extensions = IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS
        watcher = self
        
        class Handler(FileSystemEventHandler):
            def __init__(self):
                super().__init__()
                self.recently_processed = {}  # Debounce duplicate events
            
            def _should_process(self, path):
                """Check if file has valid extension"""
                ext = Path(path).suffix.lower()
                return ext in all_extensions
            
            def _debounce(self, path):
                """Prevent duplicate processing within 2 seconds"""
                import time
                now = time.time()
                if path in self.recently_processed:
                    if now - self.recently_processed[path] < 2:
                        return False
                self.recently_processed[path] = now
                return True
            
            def on_created(self, event):
                if not event.is_directory and self._should_process(event.src_path):
                    if self._debounce(event.src_path) and watcher.on_new_file:
                        print(f"[WATCHER] New file detected: {Path(event.src_path).name}")
                        watcher.on_new_file(event.src_path)
            
            def on_modified(self, event):
                if not event.is_directory and self._should_process(event.src_path):
                    if self._debounce(event.src_path) and watcher.on_modified_file:
                        watcher.on_modified_file(event.src_path)
        
        handler = Handler()
        self._observer = Observer()
        
        for folder in self.tracked_folders:
            if Path(folder).exists():
                self._observer.schedule(handler, folder, recursive=True)
                print(f"[WATCHER] Watching: {folder}")
        
        self._running = True
        self._observer.start()
        print("[WATCHER] Started monitoring for new files...")
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop watching"""
        self._running = False
        if hasattr(self, '_observer'):
            self._observer.stop()
            self._observer.join()
            print("[WATCHER] Stopped.")
    
    def scan_existing(self) -> List[str]:
        """
        Scan all tracked folders for existing files.
        
        Returns:
            List of all file paths found
        """
        from config.settings import (
            IMAGE_EXTENSIONS, 
            AUDIO_EXTENSIONS, 
            DOCUMENT_EXTENSIONS
        )
        
        all_extensions = IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS
        files = []
        
        for folder in self.tracked_folders:
            folder_path = Path(folder)
            if folder_path.exists():
                for ext in all_extensions:
                    files.extend(folder_path.rglob(f"*{ext}"))
        
        return [str(f) for f in files]


# =============================================================================
# TESTING
# =============================================================================

def test_file_watcher():
    """Test the file watcher"""
    print("=" * 60)
    print("FILE WATCHER TEST")
    print("=" * 60)
    
    watcher = FileWatcher()
    
    # Add test folder
    test_folder = Path("tests/test_watch")
    test_folder.mkdir(parents=True, exist_ok=True)
    
    watcher.add_folder(str(test_folder))
    
    print(f"\nTracked folders: {watcher.list_folders()}")
    
    # Scan existing
    files = watcher.scan_existing()
    print(f"Files found: {len(files)}")
    
    # Test callbacks
    def on_new(path):
        print(f"NEW FILE: {path}")
    
    def on_modified(path):
        print(f"MODIFIED: {path}")
    
    watcher.on_new_file = on_new
    watcher.on_modified_file = on_modified
    
    try:
        print("\nStarting watcher...")
        watcher.start()
    except NotImplementedError as e:
        print(f"\n⚠ {e}")


if __name__ == "__main__":
    test_file_watcher()
