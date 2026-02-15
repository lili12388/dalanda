"""
Chat Agent - Full RAG pipeline with multi-agent verification.

Pipeline:
1. ORCHESTRATOR: Parse query, extract filters (rule-based, no LLM)
2. SEARCH: Vector search with filters + passage extraction
3. TEXT AGENT (Phi-3.5): Generate answer from passages
4. VERIFIER (Llama-3.2): Check answer is grounded, assign confidence

Models:
- Phi-3.5 (~2.2GB) - Text generation
- Llama-3.2 (~2.0GB) - Verification

Memory:
- Sliding window (last 5 Q&A pairs) for context continuity
"""

import sys
import json
import requests
from datetime import datetime
from typing import Optional
from vectorizer.vector_store import VectorStore
from query.orchestrator import QueryOrchestrator
from query.retriever import generate_answer
from query.verifier import verify_answer
from query.memory import ConversationMemory

OLLAMA_URL = "http://localhost:11434/api/generate"


def preload_models():
    """
    Preload both LLM models into VRAM at startup.
    This avoids cold-start delay during the first query.
    """
    models = [
        ("phi3.5", "TEXT AGENT"),
        ("llama3.2", "VERIFIER")
    ]
    
    print("⏳ Preloading models into VRAM...")
    
    for model_name, agent_name in models:
        try:
            print(f"   Loading {agent_name} ({model_name})...", end=" ", flush=True)
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": model_name,
                    "prompt": "Hi",
                    "stream": False,
                    "options": {"num_predict": 1}  # Generate just 1 token
                },
                timeout=60
            )
            if response.status_code == 200:
                print("✓")
            else:
                print(f"⚠️ (status {response.status_code})")
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to Ollama!")
            print("   Run: ollama serve")
            return False
        except Exception as e:
            print(f"⚠️ ({e})")
    
    print("✅ Models ready!\n")
    return True


def find_best_passages(text: str, query: str, passage_size: int = 600, max_passages: int = 2) -> list:
    """Find passages in text that contain query words, ranked by density."""
    if not text or not query:
        return []
    
    # Common stop words to filter out (they cause false density matches)
    STOP_WORDS = {
        'the', 'and', 'for', 'that', 'this', 'with', 'are', 'was', 'were', 'been',
        'have', 'has', 'had', 'will', 'would', 'could', 'should', 'can', 'may',
        'what', 'how', 'why', 'when', 'where', 'who', 'which', 'whom',
        'from', 'into', 'about', 'your', 'you', 'use', 'used', 'using',
        'but', 'not', 'all', 'any', 'some', 'more', 'most', 'other',
        'than', 'then', 'they', 'them', 'their', 'there', 'here',
        'also', 'just', 'very', 'really', 'actually', 'does', 'did'
    }
    
    text_lower = text.lower()
    # Get query words, filter stop words, then generate variations (stems)
    raw_words = [w.lower() for w in query.split() if len(w) > 2 and w.lower() not in STOP_WORDS]
    query_words = []
    for w in raw_words:
        query_words.append(w)
        # Add simple stemming variations
        if w.endswith('s'):
            query_words.append(w[:-1])  # routines -> routine
        else:
            query_words.append(w + 's')  # routine -> routines
        if w.endswith('ing'):
            query_words.append(w[:-3])  # running -> runn (partial)
        if w.endswith('ed'):
            query_words.append(w[:-2])  # played -> play
    
    query_words = list(set(query_words))  # Remove duplicates
    
    if not query_words:
        return []
    
    scored = []
    step = 80
    
    for pos in range(0, max(1, len(text) - passage_size), step):
        window = text_lower[pos:pos + passage_size]
        density = sum(window.count(word) for word in query_words)
        
        if density > 0:
            page = (pos // 2000) + 1
            scored.append((pos, density, page))
    
    if not scored:
        return []
    
    # Sort by density
    scored.sort(key=lambda x: -x[1])
    
    # Select non-overlapping
    selected = []
    used = []
    
    for pos, density, page in scored:
        if any(abs(pos - u) < passage_size for u in used):
            continue
        
        passage = text[max(0, pos-30):pos + passage_size + 30].strip()
        selected.append({"text": passage, "page": page, "density": density})
        used.append(pos)
        
        if len(selected) >= max_passages:
            break
    
    return selected


def get_context_from_results(results: list, query: str, max_contexts: int = 3) -> list:
    """
    Extract the best passages from search results.
    Returns list of context dicts with source info.
    """
    contexts = []
    
    for r in results[:10]:  # Check top 10 results
        ext = r["extraction"]
        file_type = r["file_type"]
        score = r["score"]
        file_path = ext.get("file_path", "unknown")
        filename = file_path.split("\\")[-1].split("/")[-1]
        
        if file_type == "document":
            full_text = ext.get("extraction", {}).get("full_text", "")
            if full_text:
                passages = find_best_passages(full_text, query, passage_size=800, max_passages=2)
                if passages:
                    for p in passages:
                        contexts.append({
                            "text": p["text"],
                            "source": filename,
                            "page": p["page"],
                            "type": "document",
                            "score": score,
                            "density": p["density"]
                        })
                else:
                    # Fallback: use summary or beginning of document
                    summary = ext.get("extraction", {}).get("summary", full_text[:800])
                    contexts.append({
                        "text": summary[:800],
                        "source": filename,
                        "page": 1,
                        "type": "document",
                        "score": score,
                        "density": 0
                    })
        
        elif file_type == "audio":
            transcript = ext.get("extraction", {}).get("transcript", "")
            if transcript:
                passages = find_best_passages(transcript, query, passage_size=600, max_passages=1)
                if passages:
                    for p in passages:
                        contexts.append({
                            "text": p["text"],
                            "source": filename,
                            "type": "audio",
                            "score": score,
                            "density": p["density"]
                        })
                else:
                    # Fallback: use full transcript since vector search found it relevant
                    contexts.append({
                        "text": transcript[:800],
                        "source": filename,
                        "type": "audio",
                        "score": score,
                        "density": 0  # Low density since no keyword match
                    })
        
        elif file_type == "image":
            desc = ext.get("extraction", {}).get("description", "")
            if desc and any(w.lower() in desc.lower() for w in query.split() if len(w) > 2):
                contexts.append({
                    "text": desc[:800],
                    "source": filename,
                    "type": "image",
                    "score": score,
                    "density": 1
                })
        
        if len(contexts) >= max_contexts:
            break
    
    # Sort by: vector score first (semantic match), then density (keyword match)
    # High vector score means semantically relevant even if no exact keyword match
    contexts.sort(key=lambda x: (-x.get("score", 0), -x.get("density", 0)))
    return contexts[:max_contexts]


def chat(
    question: str, 
    verbose: bool = False, 
    skip_verification: bool = False,
    memory: Optional[ConversationMemory] = None
) -> dict:
    """
    Main chat function - full RAG pipeline with multi-agent verification.
    
    Pipeline:
    1. Orchestrator parses query, extracts filters (rule-based)
    2. Vector search with filters
    3. Extract best passages
    4. TEXT AGENT (Phi-3.5) generates answer (with conversation history)
    5. VERIFIER (Llama-3.2) checks answer is grounded
    
    Args:
        question: User's question
        verbose: Show detailed progress
        skip_verification: Skip verifier for faster response
        memory: ConversationMemory instance for context continuity
    
    Returns dict with:
    - answer: The final response
    - sources: List of sources used
    - confidence: Verification confidence (0-100)
    - is_grounded: Whether answer is supported by sources
    - filters_applied: What filters were detected
    """
    # Step 1: Parse query with orchestrator
    orchestrator = QueryOrchestrator()
    parsed = orchestrator.parse(question)
    
    if verbose:
        print(f"\n🔎 ORCHESTRATOR:")
        print(f"   Original: \"{parsed['original_query']}\"")
        print(f"   Search: \"{parsed['search_query']}\"")
        if parsed['has_filters']:
            print(f"   {orchestrator.describe_filters(parsed)}")
        else:
            print(f"   No filters")
    
    # Step 2: Vector search
    vs = VectorStore()
    
    filters = parsed['filters']
    search_kwargs = {
        "query": parsed['search_query'],
        "top_k": 20,
        "min_score": 0.5
    }
    
    if filters['file_type']:
        search_kwargs['file_type'] = filters['file_type']
    if filters['date_from']:
        search_kwargs['date_from'] = filters['date_from']
    if filters['date_to']:
        search_kwargs['date_to'] = filters['date_to']
    
    results = vs.search(**search_kwargs)
    
    if not results and parsed['has_filters']:
        if verbose:
            print("   ⚠️ No results with filters, trying without...")
        search_kwargs.pop('date_from', None)
        search_kwargs.pop('date_to', None)
        results = vs.search(**search_kwargs)
    
    if not results:
        return {
            "answer": "I couldn't find any relevant information in your personal files.",
            "sources": [],
            "confidence": 0,
            "is_grounded": False,
            "filters_applied": orchestrator.describe_filters(parsed)
        }
    
    # Step 3: Extract passages
    contexts = get_context_from_results(results, question, max_contexts=3)
    
    if verbose:
        print(f"\n📚 SEARCH RESULTS ({len(contexts)} passages):")
        for i, ctx in enumerate(contexts, 1):
            print(f"   {i}. [{ctx['type']}] {ctx['source']} (density: {ctx['density']})")
            print(f"      \"{ctx['text'][:80]}...\"")
    
    # Step 4: TEXT AGENT (Phi-3.5) - Generate answer
    if verbose:
        print(f"\n🤖 TEXT AGENT (Phi-3.5):")
        print(f"   Generating answer...")
    
    # Get conversation history for context
    conversation_history = memory.get_context_string() if memory else None
    
    text_result = generate_answer(question, contexts, conversation_history)
    answer = text_result["answer"]
    
    if verbose:
        print(f"   Answer: {answer[:100]}...")
    
    # Step 5: VERIFIER (Llama-3.2) - Check answer
    if skip_verification:
        verification = {
            "is_grounded": True,
            "confidence": 70,
            "issues": [],
            "citations": text_result["sources_used"]
        }
    else:
        if verbose:
            print(f"\n✅ VERIFIER (Llama-3.2):")
            print(f"   Checking answer...")
        
        verification = verify_answer(answer, contexts, question)
        
        if verbose:
            print(f"   Grounded: {verification['is_grounded']}")
            print(f"   Confidence: {verification['confidence']}%")
            if verification['issues']:
                print(f"   Issues: {verification['issues']}")
    
    # Build final result
    result = {
        "answer": answer,
        "sources": text_result["sources_used"],
        "confidence": verification["confidence"],
        "is_grounded": verification["is_grounded"],
        "issues": verification.get("issues", []),
        "filters_applied": orchestrator.describe_filters(parsed)
    }
    
    # Always include passages for UI hover popups
    result["passages"] = [
        {
            "source": ctx["source"],
            "text": ctx["text"],
            "type": ctx["type"],
            "page": ctx.get("page")
        }
        for ctx in contexts
    ]
    
    if verbose:
        result["contexts"] = contexts
        result["parsed_query"] = parsed
    
    return result


def interactive_mode():
    """Interactive chat mode with multi-agent pipeline and conversation memory."""
    print("\n" + "=" * 55)
    print("🧠 AI MINDS - Personal Memory Chat (Multi-Agent)")
    print("=" * 55)
    print("Pipeline: Orchestrator → Search → Phi-3.5 → Llama-3.2")
    print("Commands: 'quit', 'verbose', 'fast', 'clear', 'save'\n")
    
    # Preload models into VRAM at startup
    if not preload_models():
        print("⚠️ Warning: Models not preloaded. First query will be slow.\n")
    
    # Initialize conversation memory (keeps last 5 Q&A pairs)
    memory = ConversationMemory(max_history=5)
    
    verbose = False
    skip_verify = False
    
    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n💾 Saving conversation...")
            if memory:
                path = memory.save_session()
                print(f"   Saved to: {path}")
            print("Goodbye!")
            break
        
        if not question:
            continue
        
        if question.lower() in ["quit", "exit", "q"]:
            if memory:
                path = memory.save_session()
                print(f"💾 Conversation saved to: {path}")
            print("Goodbye!")
            break
        
        if question.lower() == "verbose":
            verbose = not verbose
            print(f"Verbose mode: {'ON' if verbose else 'OFF'}\n")
            continue
        
        if question.lower() == "fast":
            skip_verify = not skip_verify
            print(f"Fast mode (skip verifier): {'ON' if skip_verify else 'OFF'}\n")
            continue
        
        if question.lower() == "clear":
            memory.clear()
            print("🗑️ Conversation memory cleared.\n")
            continue
        
        if question.lower() == "save":
            path = memory.save_session()
            print(f"💾 Conversation saved to: {path}\n")
            continue
        
        # Show memory indicator
        if len(memory) > 0:
            print(f"\n🔍 Processing query... (context: {len(memory)} previous exchanges)")
        else:
            print("\n🔍 Processing query...")
        
        result = chat(question, verbose=verbose, skip_verification=skip_verify, memory=memory)
        
        # Show confidence indicator
        conf = result.get("confidence", 0)
        if conf >= 80:
            conf_icon = "🟢"
        elif conf >= 50:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"
        
        print(f"\n🤖 Answer: {result['answer']}")
        print(f"\n{conf_icon} Confidence: {conf}% | Grounded: {result.get('is_grounded', 'N/A')}")
        
        if result.get("issues"):
            print(f"⚠️ Issues: {', '.join(result['issues'])}")
        
        if result.get("sources"):
            sources = result["sources"]
            if isinstance(sources[0], dict):
                source_names = [s.get('file', str(s)) for s in sources]
            else:
                source_names = sources
            print(f"📎 Sources: {', '.join(source_names)}")
        else:
            source_names = []
        
        # Add to conversation memory
        memory.add(question, result['answer'], source_names)
        print()


def main():
    if len(sys.argv) < 2:
        interactive_mode()
    else:
        question = " ".join(sys.argv[1:])
        print(f"\n🔍 Question: {question}")
        result = chat(question, verbose=True)
        
        # Show result
        conf = result.get("confidence", 0)
        if conf >= 80:
            conf_icon = "🟢"
        elif conf >= 50:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"
        
        print(f"\n{'='*55}")
        print(f"🤖 Answer: {result['answer']}")
        print(f"\n{conf_icon} Confidence: {conf}% | Grounded: {result.get('is_grounded', 'N/A')}")
        
        if result.get("sources"):
            sources = result["sources"]
            if isinstance(sources[0], dict):
                print(f"📎 Sources: {', '.join(s.get('file', str(s)) for s in sources)}")
            else:
                print(f"📎 Sources: {', '.join(sources)}")


if __name__ == "__main__":
    main()
