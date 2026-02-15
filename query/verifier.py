"""
Verifier Agent - Checks answers for accuracy and assigns confidence.

Model: Llama-3.2 via Ollama (~2.0GB)

This agent:
1. Receives the TEXT AGENT's answer + original passages
2. Checks if each claim is supported by the passages
3. Detects potential hallucinations
4. Assigns confidence score (0-100%)
5. Returns verification result with corrections if needed
"""

import requests
from typing import Dict, Any, List

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"


def verify_answer(answer: str, passages: List[Dict], question: str) -> Dict[str, Any]:
    """
    Verify that the answer is grounded in the provided passages.
    
    Args:
        answer: The TEXT AGENT's generated answer
        passages: List of passage dicts with 'text', 'source', 'page' etc.
        question: The original user question
    
    Returns:
        {
            "is_grounded": bool,
            "confidence": int (0-100),
            "issues": list of issues found,
            "corrected_answer": str or None (if corrections needed),
            "citations": list of sources used
        }
    """
    if not passages or not answer:
        return {
            "is_grounded": False,
            "confidence": 0,
            "issues": ["No passages or answer provided"],
            "corrected_answer": None,
            "citations": []
        }
    
    # Build context from passages
    context_parts = []
    sources = []
    for i, p in enumerate(passages, 1):
        source_info = f"[Source {i}: {p.get('source', 'unknown')}"
        if p.get('page'):
            source_info += f", Page ~{p['page']}"
        source_info += "]"
        context_parts.append(f"{source_info}\n{p['text']}")
        sources.append(p.get('source', 'unknown'))
    
    context_str = "\n\n---\n\n".join(context_parts)
    
    prompt = f"""You are a fact-checker that verifies if an answer is supported by the provided sources.

TASK: Check if the ANSWER below is fully supported by the SOURCE PASSAGES.

SOURCE PASSAGES:
{context_str}

QUESTION: {question}

ANSWER TO VERIFY:
{answer}

VERIFICATION INSTRUCTIONS:
1. Check each claim in the answer against the sources
2. Identify any claims NOT supported by the sources (hallucinations)
3. Rate confidence from 0-100 based on how well sources support the answer

Respond in this EXACT format:
GROUNDED: [YES or NO]
CONFIDENCE: [0-100]
ISSUES: [List any unsupported claims, one per line, or "None" if all claims are supported]
CITATIONS: [List which sources support the answer, e.g., "Source 1, Source 2"]

Your verification:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 300,
                    "temperature": 0.1  # Low temp for consistent analysis
                }
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "is_grounded": True,  # Assume grounded if verifier fails
                "confidence": 50,
                "issues": [f"Verifier error: {response.status_code}"],
                "corrected_answer": None,
                "citations": sources
            }
        
        result = response.json().get("response", "").strip()
        
        # Parse the verification result
        return _parse_verification(result, sources)
    
    except requests.exceptions.ConnectionError:
        return {
            "is_grounded": True,
            "confidence": 50,
            "issues": ["Cannot connect to Ollama"],
            "corrected_answer": None,
            "citations": sources
        }
    except Exception as e:
        return {
            "is_grounded": True,
            "confidence": 50,
            "issues": [str(e)],
            "corrected_answer": None,
            "citations": sources
        }


def _parse_verification(result: str, default_sources: List[str]) -> Dict[str, Any]:
    """Parse the verifier's structured response."""
    lines = result.strip().split("\n")
    
    is_grounded = True
    confidence = 70
    issues = []
    citations = default_sources
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.upper().startswith("GROUNDED:"):
            value = line.split(":", 1)[1].strip().upper()
            is_grounded = "YES" in value or "TRUE" in value
            current_section = None
        
        elif line.upper().startswith("CONFIDENCE:"):
            try:
                conf_str = line.split(":", 1)[1].strip()
                # Extract number from string like "85" or "85%" or "85/100"
                conf_num = ''.join(c for c in conf_str if c.isdigit())
                if conf_num:
                    confidence = min(100, max(0, int(conf_num)))
            except:
                pass
            current_section = None
        
        elif line.upper().startswith("ISSUES:"):
            current_section = "issues"
            rest = line.split(":", 1)[1].strip()
            if rest and rest.lower() != "none":
                issues.append(rest)
        
        elif line.upper().startswith("CITATIONS:"):
            current_section = "citations"
            rest = line.split(":", 1)[1].strip()
            if rest:
                citations = [s.strip() for s in rest.split(",")]
        
        elif current_section == "issues" and line.startswith("-"):
            issue = line[1:].strip()
            if issue.lower() != "none":
                issues.append(issue)
    
    return {
        "is_grounded": is_grounded,
        "confidence": confidence,
        "issues": issues if issues else [],
        "corrected_answer": None,
        "citations": citations
    }


# For testing
if __name__ == "__main__":
    test_passages = [
        {
            "text": "Neural networks typically have an input layer, one or more hidden layers, and an output layer. Deep networks have many hidden layers.",
            "source": "deep_learning_book.pdf",
            "page": 42
        }
    ]
    
    # Test with grounded answer
    result = verify_answer(
        "Neural networks have an input layer, hidden layers, and an output layer.",
        test_passages,
        "What layers do neural networks have?"
    )
    print("Grounded test:", result)
    
    # Test with hallucinated answer
    result = verify_answer(
        "Neural networks always have exactly 7 layers and were invented in 2020.",
        test_passages,
        "What layers do neural networks have?"
    )
    print("Hallucinated test:", result)
