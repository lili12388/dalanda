"""
Conversation Memory - Sliding window approach for chat context.

Keeps last N Q&A pairs in memory for context continuity.
Zero LLM overhead - just string formatting.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class ConversationMemory:
    """
    Manages conversation history using a sliding window.
    
    Features:
    - Keeps last N exchanges (default 5)
    - Zero latency overhead
    - Optional persistence to JSON
    """
    
    def __init__(self, max_history: int = 5, session_file: Optional[str] = None):
        """
        Args:
            max_history: Maximum number of Q&A pairs to keep
            session_file: Optional path to save/load session
        """
        self.max_history = max_history
        self.session_file = session_file
        self.history: List[Dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load existing session if provided
        if session_file and os.path.exists(session_file):
            self._load_session()
    
    def add(self, question: str, answer: str, sources: List[str] = None):
        """
        Add a Q&A exchange to memory.
        
        Args:
            question: User's question
            answer: Bot's answer
            sources: Optional list of source files used
        """
        exchange = {
            "question": question,
            "answer": answer,
            "sources": sources or [],
            "timestamp": datetime.now().isoformat()
        }
        
        self.history.append(exchange)
        
        # Slide window - keep only last N
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_context_string(self, max_chars: int = 2000) -> str:
        """
        Format recent history as context string for LLM.
        
        Args:
            max_chars: Maximum characters to include
        
        Returns:
            Formatted string of recent Q&A pairs
        """
        if not self.history:
            return ""
        
        parts = []
        total_chars = 0
        
        # Start from most recent, work backwards
        for exchange in reversed(self.history):
            q = exchange["question"]
            # Truncate long answers
            a = exchange["answer"][:300] + "..." if len(exchange["answer"]) > 300 else exchange["answer"]
            
            entry = f"User: {q}\nAssistant: {a}"
            
            if total_chars + len(entry) > max_chars:
                break
            
            parts.insert(0, entry)  # Insert at beginning to maintain order
            total_chars += len(entry)
        
        if not parts:
            return ""
        
        return "\n\n".join(parts)
    
    def get_last_exchange(self) -> Optional[Dict]:
        """Get the most recent Q&A exchange."""
        return self.history[-1] if self.history else None
    
    def get_last_answer(self) -> Optional[str]:
        """Get just the last answer (for follow-up context)."""
        last = self.get_last_exchange()
        return last["answer"] if last else None
    
    def get_last_sources(self) -> List[str]:
        """Get sources from the last answer."""
        last = self.get_last_exchange()
        return last.get("sources", []) if last else []
    
    def clear(self):
        """Clear conversation history."""
        self.history = []
    
    def save_session(self, filepath: Optional[str] = None):
        """
        Save conversation to JSON file.
        
        Args:
            filepath: Path to save (uses session_file if not provided)
        """
        path = filepath or self.session_file
        if not path:
            # Default to data/sessions/
            sessions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            path = os.path.join(sessions_dir, f"session_{self.session_id}.json")
        
        data = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "exchanges": self.history
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return path
    
    def _load_session(self):
        """Load session from file."""
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.history = data.get("exchanges", [])
                self.session_id = data.get("session_id", self.session_id)
        except Exception as e:
            print(f"Warning: Could not load session: {e}")
            self.history = []
    
    def __len__(self):
        return len(self.history)
    
    def __bool__(self):
        return len(self.history) > 0
