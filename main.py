"""
AI Minds Hackathon - Personal Memory Assistant

Main entry point for the extraction and query pipeline.
"""

import sys
import json
from pathlib import Path

from config.settings import ensure_directories
from storage.json_store import JSONStore
from vectorizer.vector_store import VectorStore


def process_folder(folder_path: str, file_type: str = None):
    """
    Process all files in a folder.
    
    Args:
        folder_path: Path to folder to process
        file_type: Optional filter ("image", "audio", "document")
    """
    ensure_directories()
    
    from config.settings import IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, DOCUMENT_EXTENSIONS
    from extractors.image_extractor import ImageExtractor
    from extractors.audio_extractor import AudioExtractor
    from extractors.document_extractor import DocumentExtractor
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder_path}")
        return
    
    print(f"Processing folder: {folder}")
    print("=" * 60)
    
    # Initialize
    json_store = JSONStore()
    vector_store = VectorStore()
    
    extractors = {
        "image": (ImageExtractor(), IMAGE_EXTENSIONS),
        "audio": (AudioExtractor(), AUDIO_EXTENSIONS),
        "document": (DocumentExtractor(), DOCUMENT_EXTENSIONS)
    }
    
    # Filter if type specified
    if file_type:
        extractors = {file_type: extractors[file_type]}
    
    new_extractions = []
    
    # Process files
    for ext_type, (extractor, extensions) in extractors.items():
        for ext in extensions:
            for file_path in folder.rglob(f"*{ext}"):
                try:
                    print(f"\n[{ext_type.upper()}] {file_path.name}")
                    
                    # Check if already processed
                    if extractor.is_already_extracted(str(file_path), ext_type):
                        print("  → Already extracted, skipping")
                        continue
                    
                    # Extract (handle both tuple and dict returns)
                    result = extractor.extract(str(file_path))
                    extraction = result[0] if isinstance(result, tuple) else result
                    
                    # Save JSON
                    json_path = json_store.save(extraction)
                    print(f"  → Saved: {json_path.name}")
                    
                    new_extractions.append(extraction)
                    
                except NotImplementedError as e:
                    print(f"  → Not implemented: {e}")
                except Exception as e:
                    print(f"  → Error: {e}")
        
        # Unload model after processing type
        extractor.unload_model()
    
    # Vectorize new extractions
    if new_extractions:
        print(f"\n\nVectorizing {len(new_extractions)} extractions...")
        vector_store.add_batch(new_extractions)
        vector_store.save()
        print("✓ Vectorization complete!")
    
    # Print stats
    print("\n" + "=" * 60)
    print("STATS")
    print("=" * 60)
    print(f"JSON Store: {json_store.get_stats()}")
    print(f"Vector Store: {vector_store.get_stats()}")


def search(query: str, top_k: int = 5, file_type: str = None):
    """
    Search the memory store.
    
    Args:
        query: Search query
        top_k: Number of results
        file_type: Optional filter
    """
    vector_store = VectorStore()
    
    print(f"Searching for: '{query}'")
    print("=" * 60)
    
    results = vector_store.search(query, top_k=top_k, file_type=file_type)
    
    if not results:
        print("No results found.")
        return
    
    for i, result in enumerate(results, 1):
        ext = result["extraction"]["extraction"]
        
        print(f"\n{i}. [{result['file_type'].upper()}] {result['file_id']}")
        print(f"   Score: {result['score']:.3f}")
        print(f"   Path: {result['extraction']['file_path']}")
        
        # Show summary or description
        summary = ext.get("summary") or ext.get("description") or ext.get("visual_summary")
        if summary:
            print(f"   Summary: {summary[:200]}...")
        
        # Show key points if available
        if ext.get("key_points"):
            print(f"   Key points: {ext['key_points'][:3]}")


def rebuild_index():
    """Rebuild vector index from JSON files"""
    vector_store = VectorStore()
    vector_store.rebuild()


def show_stats():
    """Show current stats"""
    json_store = JSONStore()
    vector_store = VectorStore()
    
    print("=" * 60)
    print("MEMORY STORE STATS")
    print("=" * 60)
    print(f"\nJSON Extractions: {json.dumps(json_store.get_stats(), indent=2)}")
    print(f"\nVector Index: {json.dumps(vector_store.get_stats(), indent=2)}")


def extract_and_watch(folder_path: str):
    """
    Extract all existing files in folder, then watch for new ones.
    
    This is the recommended mode for demos - shows real-time processing!
    """
    from watchers.file_watcher import FileWatcher
    from config.settings import IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, DOCUMENT_EXTENSIONS
    from extractors.image_extractor import ImageExtractor
    from extractors.audio_extractor import AudioExtractor
    from extractors.document_extractor import DocumentExtractor
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder_path}")
        return
    
    print("\n" + "=" * 60)
    print("DALANDA - EXTRACT & WATCH MODE")
    print("=" * 60)
    print(f"\nFolder: {folder.absolute()}")
    
    # Step 1: Extract existing files
    print("\n[PHASE 1] Extracting existing files...")
    print("-" * 40)
    process_folder(folder_path)
    
    # Step 2: Start watching for new files
    print("\n" + "=" * 60)
    print("[PHASE 2] Now watching for new files...")
    print("=" * 60)
    print("\nSupported formats:")
    print(f"  Images: {', '.join(IMAGE_EXTENSIONS)}")
    print(f"  Audio: {', '.join(AUDIO_EXTENSIONS)}")
    print(f"  Docs: {', '.join(DOCUMENT_EXTENSIONS)}")
    print("\nPress Ctrl+C to stop.\n")
    
    def process_new_file(file_path: str):
        """Process a newly detected file"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        print(f"\n{'='*60}")
        print(f"[NEW FILE] {path.name}")
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
            print(f"  → Unsupported: {ext}")
            return
        
        try:
            if extractor.is_already_extracted(file_path, file_type):
                print("  → Already processed")
                return
            
            print(f"  → Extracting {file_type}...")
            result = extractor.extract(file_path)
            extraction = result[0] if isinstance(result, tuple) else result
            
            json_store = JSONStore()
            json_path = json_store.save(extraction)
            print(f"  → Saved: {json_path.name}")
            
            print("  → Vectorizing...")
            vector_store = VectorStore()
            vector_store.add_batch([extraction])
            vector_store.save()
            
            extractor.unload_model()
            
            print(f"\n✓ Ready! Ask the bot about: {path.name}")
            
        except Exception as e:
            print(f"  → Error: {e}")
    
    # Setup and start watcher
    watcher = FileWatcher()
    watcher.add_folder(folder_path)
    watcher.on_new_file = process_new_file
    
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        watcher.stop()
        print("Done!")


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("""
AI Minds - Personal Memory Assistant
=====================================

Usage:
    python main.py <folder_path>           <- Extract + Watch (recommended!)
    python main.py extract <folder_path> [--type image|audio|document]
    python main.py search <query> [--top 5] [--type image|audio|document]
    python main.py chat                    <- Interactive mode (FAST!)
    python main.py rebuild
    python main.py stats

Examples:
    python main.py ./my_files              <- Extract all then watch for new files
    python main.py extract ./my_files
    python main.py extract ./pictures --type image
    python main.py search "meeting notes about project"
    python main.py search "contracts" --type document --top 10
    python main.py stats
        """)
        return
    
    command = sys.argv[1]
    
    # Check if first arg is a folder path (not a command) -> Extract + Watch mode
    if Path(command).exists() and Path(command).is_dir():
        extract_and_watch(command)
        return
    
    if command == "extract":
        if len(sys.argv) < 3:
            print("Usage: python main.py extract <folder_path>")
            return
        
        folder = sys.argv[2]
        file_type = None
        
        if "--type" in sys.argv:
            idx = sys.argv.index("--type")
            if idx + 1 < len(sys.argv):
                file_type = sys.argv[idx + 1]
        
        process_folder(folder, file_type)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python main.py search <query>")
            return
        
        query = sys.argv[2]
        top_k = 5
        file_type = None
        
        if "--top" in sys.argv:
            idx = sys.argv.index("--top")
            if idx + 1 < len(sys.argv):
                top_k = int(sys.argv[idx + 1])
        
        if "--type" in sys.argv:
            idx = sys.argv.index("--type")
            if idx + 1 < len(sys.argv):
                file_type = sys.argv[idx + 1]
        
        search(query, top_k, file_type)
    
    elif command == "rebuild":
        rebuild_index()
    
    elif command == "stats":
        show_stats()
    
    elif command == "chat":
        # Interactive mode - keeps model loaded for fast queries
        interactive_chat()
    
    else:
        print(f"Unknown command: {command}")


def interactive_chat():
    """Interactive chat mode - model stays loaded for instant queries"""
    from vectorizer.vector_store import VectorStore
    
    print("\n" + "="*60)
    print("AI MEMORY ASSISTANT - Interactive Mode")
    print("="*60)
    print("Model loading (one-time)...")
    
    vector_store = VectorStore()
    # Pre-load embedding model
    vector_store.embedder.load()
    
    print("\n✓ Ready! Type queries. Commands: 'quit', 'stats'")
    print("  Tip: Add number for results, e.g. 'apple 10'")
    print("-"*60)
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            if query.lower() == 'stats':
                print(f"Vectors: {vector_store.get_stats()}")
                continue
            
            # Parse top_k from query (e.g., "apple 10")
            parts = query.rsplit(' ', 1)
            top_k = 5
            if len(parts) == 2 and parts[1].isdigit():
                query = parts[0]
                top_k = int(parts[1])
            
            # Search (instant - model already loaded)
            import time
            start = time.time()
            results = vector_store.search(query, top_k=top_k, min_score=0.55)
            elapsed = time.time() - start
            
            if not results:
                print("No results found.")
                continue
            
            print(f"\n{len(results)} results ({elapsed*1000:.0f}ms):\n")
            
            for i, r in enumerate(results, 1):
                ext = r["extraction"]["extraction"]
                desc = ext.get("description", "") or ext.get("visual_summary", "")
                desc = desc[:120].replace("\n", " ").strip()
                fname = r['extraction']['file_path'].split(chr(92))[-1]
                print(f"{i}. [{r['score']:.2f}] {fname}")
                if desc:
                    print(f"   {desc}...")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
