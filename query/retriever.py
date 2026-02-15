"""
Text Agent - Generates answers from retrieved passages.

Model: Phi-3.5 via Ollama (~2.2GB)

This agent:
1. Receives passages from vector search
2. Generates a coherent answer from the passages
3. Includes citations to sources
4. Uses conversation history for context continuity
"""

import requests
from typing import Dict, Any, List, Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3.5"


def generate_answer(
    question: str, 
    passages: List[Dict],
    conversation_history: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an answer from the provided passages.
    
    Args:
        question: The user's question
        passages: List of passage dicts with 'text', 'source', 'page', 'type', 'density'
        conversation_history: Optional formatted string of recent Q&A pairs
    
    Returns:
        {
            "answer": str,
            "sources_used": list of source names,
            "raw_response": str
        }
    """
    if not passages:
        return {
            "answer": "I couldn't find any relevant information in your files to answer this question.",
            "sources_used": [],
            "raw_response": ""
        }
    
    # Build context from passages with clear source names
    context_parts = []
    sources = []
    source_map = []  # For the model to reference
    
    for i, p in enumerate(passages, 1):
        source_name = p.get('source', 'unknown file')
        file_type = p.get('type', 'file')
        
        # Only show page info for documents (PDFs)
        if file_type == 'document' and p.get('page'):
            location_info = f" (page {p['page']})"
            type_label = "document"
        elif file_type == 'audio':
            location_info = " (transcript)"
            type_label = "audio transcript"
        elif file_type == 'image':
            location_info = " (description)"
            type_label = "image description"
        else:
            location_info = ""
            type_label = file_type
        
        # Create clear header for each passage
        header = f"[FROM: {source_name}{location_info}]"
        context_parts.append(f"{header}\n{p['text']}")
        sources.append(source_name)
        source_map.append(f"- {source_name} ({type_label})")
    
    context_str = "\n\n---\n\n".join(context_parts)
    source_list = "\n".join(source_map)
    
    # Build conversation history section
    history_section = ""
    if conversation_history:
        history_section = f"""
RECENT CONVERSATION (for context):
{conversation_history}

"""
    
    prompt = f"""Answer the user's question using ONLY the context below.

RULES:
1. Answer ONLY the question asked - do not generate extra questions or answers
2. Use ONLY information from the provided context
3. Cite sources by filename:
   - PDFs: "According to filename.pdf (page X)..."
   - Audio files (.mp3): "According to filename.mp3..." (no page numbers for audio)
   - Images: "According to filename.jpg..."
4. If context doesn't fully answer the question, say what you CAN answer
5. Be concise - aim for 2-4 sentences
6. Do NOT invent information
7. If the user refers to previous conversation (e.g., "what about...", "can you explain more"), use the conversation history for context
{history_section}
SOURCES:
{source_list}

CONTEXT:
{context_str}

USER QUESTION: {question}

YOUR ANSWER (one answer only, cite sources):"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 512,
                    "temperature": 0.3
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            answer = response.json().get("response", "").strip()
            return {
                "answer": answer,
                "sources_used": list(set(sources)),
                "raw_response": answer
            }
        else:
            return {
                "answer": f"Error generating answer: {response.status_code}",
                "sources_used": sources,
                "raw_response": ""
            }
    
    except requests.exceptions.ConnectionError:
        return {
            "answer": "Error: Cannot connect to Ollama. Make sure it's running (ollama serve).",
            "sources_used": [],
            "raw_response": ""
        }
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "sources_used": [],
            "raw_response": ""
        }


# For testing
if __name__ == "__main__":
    test_passages = [
        {
            "text": "Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process information using connectionist approaches.",
            "source": "deep_learning_book.pdf",
            "page": 15,
            "type": "document",
            "density": 5
        },
        {
            "text": "The most common types are feedforward networks, where information moves in one direction, and recurrent networks, which have feedback connections.",
            "source": "ml_guide.pdf",
            "page": 42,
            "type": "document",
            "density": 3
        }
    ]
    
    result = generate_answer("What is a neural network?", test_passages)
    print("Answer:", result["answer"])
    print("Sources:", result["sources_used"])
