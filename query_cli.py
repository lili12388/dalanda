"""
Simple Query CLI - Search your personal memories.

Usage:
    python query_cli.py                    # Interactive mode
    python query_cli.py "your query"       # Single query mode
"""
import sys
import re
from vectorizer.vector_store import VectorStore

def find_best_passages(text: str, query: str, passage_size: int = 600, max_passages: int = 3, chars_per_page: int = 2000, require_all_words: bool = True) -> list:
    """
    Find the most relevant passages in text for the query.
    Scores by DENSITY (count of word occurrences), not just presence.
    Returns list of (passage, start_position, density_score, matched_words, estimated_page)
    
    If require_all_words=True and no passages match all words, falls back to any-word matching.
    """
    if not text or not query:
        return []
    
    # Normalize
    text_lower = text.lower()
    query_words = [w.lower() for w in query.split() if len(w) > 2]
    
    if not query_words:
        return []
    
    def find_passages_internal(require_all: bool):
        """Internal function to find passages with all/any word matching"""
        scored_positions = []
        step = 80
        
        for pos in range(0, max(1, len(text) - passage_size), step):
            window = text_lower[pos:pos + passage_size]
            
            matched_words = []
            density = 0
            for word in query_words:
                count = window.count(word)
                if count > 0:
                    matched_words.append(word)
                    density += count
            
            # Apply filter based on mode
            if require_all and len(query_words) >= 2:
                if len(matched_words) < len(query_words):
                    continue
            
            if matched_words:
                page = (pos // chars_per_page) + 1
                scored_positions.append((pos, density, matched_words, page))
        
        if not scored_positions:
            return []
        
        # Sort by density (highest first)
        scored_positions.sort(key=lambda x: -x[1])
        
        # Select non-overlapping passages
        selected = []
        used_ranges = []
        
        for pos, density, matched, page in scored_positions:
            overlaps = False
            for used_start, used_end in used_ranges:
                if not (pos + passage_size < used_start or pos > used_end):
                    overlaps = True
                    break
            
            if not overlaps:
                start = max(0, pos - 50)
                passage = text[start:start + passage_size + 50]
                
                if start > 0:
                    first_period = passage.find('. ')
                    if 0 < first_period < 80:
                        passage = passage[first_period + 2:]
                
                last_period = passage.rfind('.')
                if last_period > len(passage) - 80 and last_period > 150:
                    passage = passage[:last_period + 1]
                
                selected.append((passage.strip(), pos, density, matched, page))
                used_ranges.append((pos - 50, pos + passage_size + 50))
                
                if len(selected) >= max_passages:
                    break
        
        return selected
    
    # Try with all words first
    if require_all_words and len(query_words) >= 2:
        results = find_passages_internal(require_all=True)
        if results:
            return results
        # Fallback to any word matching
        return find_passages_internal(require_all=False)
    else:
        return find_passages_internal(require_all=False)

def search_and_print(vs, query, min_score=0.6):
    """Search and show all results with score >= min_score"""
    results = vs.search(query, top_k=50, min_score=min_score)
    
    if not results:
        print("  ❌ No results found above threshold.\n")
        return
    
    print(f"\n  ✅ Found {len(results)} results (score >= {min_score}):\n")
    
    for i, r in enumerate(results, 1):
        icon = {"image": "🖼️", "audio": "🎵", "document": "📄"}.get(r["file_type"], "📎")
        ext = r["extraction"]
        score = r["score"]
        
        print(f"  {i}. {icon} [{r['file_type'].upper()}] (score: {score:.2f})")
        
        if r["file_type"] == "document":
            summary = ext.get("extraction", {}).get("summary", "")[:120]
            print(f"     Summary: {summary}...")
            
            # Find multiple best passages ranked by density
            full_text = ext.get("extraction", {}).get("full_text", "")
            if full_text:
                passages = find_best_passages(full_text, query, passage_size=600, max_passages=3)
                if passages:
                    print(f"     📍 Found {len(passages)} relevant sections:")
                    for j, (passage, pos, density, matched, page) in enumerate(passages):
                        # Show page number and which words matched
                        words_info = f"[{', '.join(matched)}]" if len(matched) < len(query.split()) else ""
                        print(f"        [{j+1}] Page ~{page} | Density: {density} {words_info}")
                        print(f"            \"{passage[:200]}...\"")
                else:
                    print(f"     ⚠️ No matching passages found")  # Longer preview
                    
        elif r["file_type"] == "audio":
            transcript = ext.get("extraction", {}).get("transcript", "")
            passages = find_best_passages(transcript, query, passage_size=400, max_passages=2)
            if passages:
                for passage, pos, density, matched, page in passages:
                    # Audio doesn't have pages, show timestamp hint
                    time_hint = f"~{pos // 150}s" if pos > 0 else "start"
                    print(f"     🎵 Transcript at {time_hint} (density: {density}): {passage[:200]}...")
            else:
                print(f"     🎵 Transcript: {transcript[:180]}...")
            
        elif r["file_type"] == "image":
            desc = ext.get("extraction", {}).get("description", "")[:150]
            print(f"     {desc}...")
        print()

def interactive_mode():
    print("\n" + "=" * 50)
    print("🧠 AI MINDS - Personal Memory Search")
    print("=" * 50)
    print("Type your query and press Enter.")
    print("Commands: 'quit' to exit, 'min 0.5' to change threshold")
    print("Shows all results with score >= 0.6 (sorted by relevance)")
    print()
    
    vs = VectorStore()
    min_score = 0.6
    
    while True:
        try:
            query = input("🔍 Search: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not query:
            continue
        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        if query.lower().startswith("min "):
            try:
                min_score = float(query.split()[1])
                print(f"  Threshold set to {min_score}\n")
            except:
                print("  Usage: min 0.5\n")
            continue
        
        search_and_print(vs, query, min_score)

def main():
    if len(sys.argv) < 2:
        interactive_mode()
    else:
        query = sys.argv[1]
        file_type = None
        min_score = 0.6
        
        for i, arg in enumerate(sys.argv):
            if arg == "--type" and i + 1 < len(sys.argv):
                file_type = sys.argv[i + 1]
            if arg == "--min" and i + 1 < len(sys.argv):
                min_score = float(sys.argv[i + 1])
        
        print(f"\n🔍 Searching for: \"{query}\" (min score: {min_score})")
        vs = VectorStore()
        results = vs.search(query, top_k=50, file_type=file_type, min_score=min_score)
        
        if not results:
            print("❌ No results found.")
            return
        
        print(f"✅ Found {len(results)} results:\n")
        for i, r in enumerate(results, 1):
            icon = {"image": "🖼️", "audio": "🎵", "document": "📄"}.get(r["file_type"], "📎")
            ext = r["extraction"]
            
            print(f"{i}. {icon} [{r['file_type'].upper()}] (score: {r['score']:.3f})")
            print(f"   File: {ext.get('file_path', 'unknown')}")
            
            if r["file_type"] == "document":
                summary = ext.get("extraction", {}).get("summary", "")[:150]
                print(f"   Summary: {summary}...")
                full_text = ext.get("extraction", {}).get("full_text", "")
                if full_text:
                    passages = find_best_passages(full_text, query, passage_size=600, max_passages=3)
                    if passages:
                        print(f"   📍 Top {len(passages)} relevant sections (sorted by density):")
                        for j, (passage, pos, density, matched, page) in enumerate(passages):
                            words_info = f"[{', '.join(matched)}]" if len(matched) < len(query.split()) else ""
                            print(f"      [{j+1}] Page ~{page} | Density: {density} {words_info}")
                            print(f"          \"{passage[:220]}...\"")
                    else:
                        print(f"   ⚠️ No matching passages found")
                            
            elif r["file_type"] == "audio":
                transcript = ext.get("extraction", {}).get("transcript", "")
                passages = find_best_passages(transcript, query, 400, 2)
                if passages:
                    for passage, pos, density, matched, page in passages:
                        time_hint = f"~{pos // 150}s" if pos > 0 else "start"
                        print(f"   🎵 At {time_hint} (density: {density}): {passage[:220]}...")
                else:
                    print(f"   🎵 Transcript: {transcript[:200]}...")
                    
            elif r["file_type"] == "image":
                desc = ext.get("extraction", {}).get("description", "")[:200]
                print(f"   Description: {desc}...")
            print("-" * 60)

if __name__ == "__main__":
    main()
