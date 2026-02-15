"""
Orchestrator - Routes queries and extracts filters.

Rule-based (NO LLM) filter extraction:
1. Detect if user is asking about THEIR files (not content about dates)
2. Extract date filters (last week, yesterday, etc.)
3. Extract file type filters (photos, documents, audio)
4. Pass clean query to vector search

Speed: ~5ms (just string matching)
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple


class QueryOrchestrator:
    """
    Rule-based query parser that extracts filters without using LLM.
    Only applies date filters when user is asking about their file activity.
    """
    
    # Words that indicate user is asking about THEIR file activity
    PERSONAL_INDICATORS = [
        "i ", "i'", "my ", "me ", "mine ",
        "did i", "have i", "what i", "when i", "where i",
        "show me my", "find my", "list my", "get my"
    ]
    
    # Action words that suggest file operations
    FILE_ACTION_WORDS = [
        "download", "save", "create", "add", "upload", "record",
        "store", "import", "export", "copy", "move", "receive",
        "get", "got", "took", "made", "wrote", "captured"
    ]
    
    # File type mappings
    FILE_TYPE_PATTERNS = {
        "image": [
            "photo", "photos", "image", "images", "picture", "pictures",
            "screenshot", "screenshots", "selfie", "selfies",
            "png", "jpg", "jpeg", "gif", "snap", "snaps"
        ],
        "audio": [
            "audio", "audios", "recording", "recordings", "voice", "voices",
            "sound", "sounds", "music", "mp3", "podcast", "podcasts",
            "memo", "memos", "voice memo", "voice note"
        ],
        "document": [
            "document", "documents", "doc", "docs", "pdf", "pdfs",
            "contract", "contracts", "paper", "papers", "text", "texts",
            "book", "books", "file", "files", "report", "reports",
            "article", "articles", "note", "notes", "letter", "letters"
        ]
    }
    
    # Date patterns with their relative day offsets
    RELATIVE_DATE_PATTERNS = {
        # Exact days
        r"\btoday\b": 0,
        r"\byesterday\b": 1,
        r"\bday before yesterday\b": 2,
        
        # Last X
        r"\blast\s+week\b": 7,
        r"\blast\s+month\b": 30,
        r"\blast\s+year\b": 365,
        r"\bpast\s+week\b": 7,
        r"\bpast\s+month\b": 30,
        r"\bpast\s+year\b": 365,
        
        # This X
        r"\bthis\s+week\b": 7,
        r"\bthis\s+month\b": 30,
        r"\bthis\s+year\b": 365,
        
        # Recent
        r"\brecently\b": 7,
        r"\brecent\b": 7,
        r"\blately\b": 14,
    }
    
    # Pattern for "N days/weeks/months ago"
    N_TIME_AGO_PATTERN = re.compile(
        r"(\d+)\s*(day|days|week|weeks|month|months|year|years)\s*ago",
        re.IGNORECASE
    )
    
    # Pattern for "last N days/weeks"
    LAST_N_PATTERN = re.compile(
        r"last\s+(\d+)\s*(day|days|week|weeks|month|months)",
        re.IGNORECASE
    )
    
    # Pattern for "in the last N days"
    IN_LAST_N_PATTERN = re.compile(
        r"in\s+the\s+last\s+(\d+)\s*(day|days|week|weeks|month|months)",
        re.IGNORECASE
    )
    
    # Pattern for "past N days"
    PAST_N_PATTERN = re.compile(
        r"past\s+(\d+)\s*(day|days|week|weeks|month|months)",
        re.IGNORECASE
    )
    
    # Pattern for "before N days"
    BEFORE_N_PATTERN = re.compile(
        r"before\s+(\d+)\s*(day|days|week|weeks|month|months)",
        re.IGNORECASE
    )
    
    # Pattern for "from N days ago"
    FROM_N_AGO_PATTERN = re.compile(
        r"from\s+(\d+)\s*(day|days|week|weeks|month|months)\s*ago",
        re.IGNORECASE
    )
    
    # Words that suggest date is about CONTENT, not file date
    CONTENT_DATE_INDICATORS = [
        "about", "regarding", "concerning", "related to",
        "how many", "how long", "how much", "what happens",
        "fall", "grow", "last for", "takes", "duration",
        "project", "plan", "schedule", "event", "meeting notes"
    ]
    
    def __init__(self):
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _is_file_query(self, question: str) -> bool:
        """
        Determine if the question is about the user's files vs general content.
        
        Examples:
            "What did I download last week?" → True (file query)
            "How many apples fall in 2 days?" → False (content query)
            "My notes about the meeting" → True (file query)
            "What is deep learning?" → False (content query)
        """
        q = question.lower()
        
        # Check for personal indicators
        has_personal = any(p in q for p in self.PERSONAL_INDICATORS)
        
        # Check for file action words
        has_action = any(a in q for a in self.FILE_ACTION_WORDS)
        
        # Check for content date indicators (suggests date is content, not filter)
        has_content_date = any(c in q for c in self.CONTENT_DATE_INDICATORS)
        
        # If content date indicators present with numbers, likely NOT a file query
        if has_content_date:
            return False
        
        # If personal + action, definitely a file query
        if has_personal and has_action:
            return True
        
        # If just personal with file types mentioned
        if has_personal:
            for file_type, patterns in self.FILE_TYPE_PATTERNS.items():
                if any(p in q for p in patterns):
                    return True
        
        return False
    
    def _extract_date_filter(self, question: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Extract date range from question.
        Returns (date_from, date_to) or (None, None) if no date found.
        """
        q = question.lower()
        
        # Try "N time ago" pattern first (most specific)
        match = self.N_TIME_AGO_PATTERN.search(q)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            days = self._unit_to_days(num, unit)
            date_from = self.today - timedelta(days=days)
            date_to = self.today - timedelta(days=days - 1)  # That specific day
            return (date_from, date_to)
        
        # Try "last N time" pattern
        match = self.LAST_N_PATTERN.search(q)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            days = self._unit_to_days(num, unit)
            date_from = self.today - timedelta(days=days)
            return (date_from, self.today)
        
        # Try "in the last N time" pattern
        match = self.IN_LAST_N_PATTERN.search(q)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            days = self._unit_to_days(num, unit)
            date_from = self.today - timedelta(days=days)
            return (date_from, self.today)
        
        # Try "past N time" pattern
        match = self.PAST_N_PATTERN.search(q)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            days = self._unit_to_days(num, unit)
            date_from = self.today - timedelta(days=days)
            return (date_from, self.today)
        
        # Try "from N time ago" pattern
        match = self.FROM_N_AGO_PATTERN.search(q)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            days = self._unit_to_days(num, unit)
            date_from = self.today - timedelta(days=days)
            return (date_from, self.today)
        
        # Try relative date patterns
        for pattern, days_ago in self.RELATIVE_DATE_PATTERNS.items():
            if re.search(pattern, q, re.IGNORECASE):
                date_from = self.today - timedelta(days=days_ago)
                if days_ago == 0:  # today
                    return (self.today, self.today + timedelta(days=1))
                elif days_ago in [1, 2]:  # yesterday, day before
                    date_to = date_from + timedelta(days=1)
                    return (date_from, date_to)
                else:
                    return (date_from, self.today)
        
        return (None, None)
    
    def _unit_to_days(self, num: int, unit: str) -> int:
        """Convert time unit to days."""
        unit = unit.rstrip('s')  # Remove plural
        multipliers = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365
        }
        return num * multipliers.get(unit, 1)
    
    def _extract_file_type(self, question: str) -> Optional[str]:
        """Extract file type filter from question."""
        q = question.lower()
        
        for file_type, patterns in self.FILE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in q:
                    return file_type
        
        return None
    
    def _clean_query(self, question: str) -> str:
        """
        Remove filter words from query to get clean search terms.
        """
        q = question
        
        # Remove date patterns
        for pattern in self.RELATIVE_DATE_PATTERNS.keys():
            q = re.sub(pattern, "", q, flags=re.IGNORECASE)
        
        # Remove N time ago patterns
        q = self.N_TIME_AGO_PATTERN.sub("", q)
        q = self.LAST_N_PATTERN.sub("", q)
        q = self.IN_LAST_N_PATTERN.sub("", q)
        q = self.PAST_N_PATTERN.sub("", q)
        q = self.FROM_N_AGO_PATTERN.sub("", q)
        
        # Remove common question words
        remove_words = [
            r"\bwhat\b", r"\bwhich\b", r"\bwhere\b", r"\bwhen\b",
            r"\bdid\b", r"\bdo\b", r"\bdoes\b", r"\bhave\b", r"\bhas\b",
            r"\bshow\b", r"\bfind\b", r"\blist\b", r"\bget\b",
            r"\bme\b", r"\bmy\b", r"\bi\b", r"\bthe\b", r"\ba\b", r"\ban\b"
        ]
        for word in remove_words:
            q = re.sub(word, "", q, flags=re.IGNORECASE)
        
        # Clean up whitespace
        q = re.sub(r"\s+", " ", q).strip()
        
        # If query is too short after cleaning, use original
        if len(q) < 3:
            return question
        
        return q
    
    def parse(self, question: str) -> Dict[str, Any]:
        """
        Parse a user question and extract filters.
        
        Returns:
            {
                "original_query": str,
                "search_query": str (cleaned for vector search),
                "is_file_query": bool,
                "filters": {
                    "date_from": datetime or None,
                    "date_to": datetime or None,
                    "file_type": str or None
                },
                "has_filters": bool
            }
        """
        is_file_query = self._is_file_query(question)
        
        # Only extract filters for file queries
        if is_file_query:
            date_from, date_to = self._extract_date_filter(question)
            file_type = self._extract_file_type(question)
            search_query = self._clean_query(question)
        else:
            date_from, date_to = None, None
            file_type = None
            search_query = question  # Use full question for content queries
        
        has_filters = date_from is not None or file_type is not None
        
        return {
            "original_query": question,
            "search_query": search_query,
            "is_file_query": is_file_query,
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
                "file_type": file_type
            },
            "has_filters": has_filters
        }
    
    def describe_filters(self, parsed: Dict[str, Any]) -> str:
        """Generate human-readable description of filters."""
        parts = []
        
        filters = parsed["filters"]
        
        if filters["date_from"]:
            if filters["date_to"]:
                parts.append(f"from {filters['date_from'].strftime('%Y-%m-%d')} to {filters['date_to'].strftime('%Y-%m-%d')}")
            else:
                parts.append(f"since {filters['date_from'].strftime('%Y-%m-%d')}")
        
        if filters["file_type"]:
            parts.append(f"type: {filters['file_type']}")
        
        if parts:
            return "Filters: " + ", ".join(parts)
        else:
            return "No filters applied"


def orchestrate(question: str) -> Dict[str, Any]:
    """
    Main entry point - parse question and prepare for search.
    
    Args:
        question: User's question
        
    Returns:
        Parsed query with filters ready for vector search
    """
    orch = QueryOrchestrator()
    return orch.parse(question)


# For testing
if __name__ == "__main__":
    import sys
    
    test_queries = [
        # File queries (should have filters)
        "What did I download last week?",
        "Show me my photos from yesterday",
        "What contracts did I save 3 days ago?",
        "Find my recordings from the past month",
        "What documents have I created recently?",
        
        # Content queries (should NOT have filters)
        "How many apples fall in 2 days?",
        "What is quantum computing?",
        "Explain neural networks",
        "What happens after 3 weeks of training?",
        "Tell me about the 2-week project plan",
        
        # Edge cases
        "My notes about yesterday's meeting",  # Has "yesterday" but it's content
        "What did I record last Monday?",
        "Show me documents about the last quarter report",  # "last" is content
    ]
    
    orch = QueryOrchestrator()
    
    if len(sys.argv) > 1:
        # Test specific query
        query = " ".join(sys.argv[1:])
        result = orch.parse(query)
        print(f"\nQuery: {query}")
        print(f"Is file query: {result['is_file_query']}")
        print(f"Search query: {result['search_query']}")
        print(f"Filters: {result['filters']}")
        print(orch.describe_filters(result))
    else:
        # Run all tests
        print("=" * 60)
        print("ORCHESTRATOR TEST")
        print("=" * 60)
        
        for query in test_queries:
            result = orch.parse(query)
            print(f"\n📝 \"{query}\"")
            print(f"   File query: {result['is_file_query']}")
            print(f"   Search: \"{result['search_query']}\"")
            if result['has_filters']:
                print(f"   {orch.describe_filters(result)}")
            else:
                print("   No filters")
