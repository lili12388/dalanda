"""
JSON Schemas for Extraction Validation

SHARED FILE - Do not modify unless discussed with team.

Each team member's extraction must match these schemas.
Use validate_extraction() to check your output before saving.
"""

from typing import Dict, Any, List


# =============================================================================
# IMAGE EXTRACTION SCHEMA
# Owner: Laith
# Model: Qwen2.5-VL-3B
# =============================================================================
IMAGE_SCHEMA = {
    "required_fields": [
        "file_id",          # Unique ID: img_XXXXXXXX
        "file_path",        # Absolute path to original file
        "file_type",        # Must be "image"
        "file_hash",        # MD5 hash for change detection
        "file_size_bytes",  # File size
        "created_at",       # ISO timestamp
        "modified_at",      # ISO timestamp
        "extracted_at",     # ISO timestamp
        "extraction",       # Extraction data (see below)
        "embedding_text"    # Text for vector embedding
    ],
    "extraction_fields": [
        "description",      # Natural language description
        "image_type",       # screenshot, photo, diagram, etc.
        "ocr_text",         # Extracted text from image
        "objects_detected", # List of detected objects
        "entities",         # Dict: people, locations, orgs, dates, etc.
        "categories",       # List of categories
        "topics",           # List of topics
        "action_items",     # List of {action, confidence}
        "sentiment",        # positive, negative, neutral
        "contains_text",    # Boolean
        "contains_faces",   # Boolean
        "visual_summary"    # One-sentence summary
    ]
}


# =============================================================================
# AUDIO EXTRACTION SCHEMA
# Owner: [Team Member 2]
# Model: Whisper + Qwen2.5-3B
# =============================================================================
AUDIO_SCHEMA = {
    "required_fields": [
        "file_id",          # Unique ID: aud_XXXXXXXX
        "file_path",        # Absolute path to original file
        "file_type",        # Must be "audio"
        "file_hash",        # MD5 hash
        "file_size_bytes",  # File size
        "created_at",       # ISO timestamp
        "modified_at",      # ISO timestamp
        "extracted_at",     # ISO timestamp
        "extraction",       # Extraction data (see below)
        "embedding_text"    # Text for vector embedding
    ],
    "extraction_fields": [
        "transcript_full",      # Full transcription
        "transcript_segments",  # List of {start, end, text, speaker}
        "duration_seconds",     # Audio duration
        "duration_formatted",   # "MM:SS" format
        "language",             # Detected language
        "speakers",             # Dict: count, identified names
        "summary",              # Brief summary
        "key_points",           # List of key points
        "entities",             # Dict: people, dates, money, etc.
        "action_items",         # List of {action, deadline, priority, confidence}
        "topics",               # List of topics
        "categories",           # List of categories
        "audio_type",           # voice_note, meeting, lecture, etc.
        "sentiment",            # positive, negative, neutral
        "urgency"               # high, medium, low
    ]
}


# =============================================================================
# DOCUMENT EXTRACTION SCHEMA
# Owner: [Team Member 3]
# Model: PyMuPDF/python-docx + Qwen2.5-3B
# =============================================================================
DOCUMENT_SCHEMA = {
    "required_fields": [
        "file_id",          # Unique ID: doc_XXXXXXXX
        "file_path",        # Absolute path to original file
        "file_type",        # Must be "document"
        "file_hash",        # MD5 hash
        "file_size_bytes",  # File size
        "created_at",       # ISO timestamp
        "modified_at",      # ISO timestamp
        "extracted_at",     # ISO timestamp
        "extraction",       # Extraction data (see below)
        "embedding_text"    # Text for vector embedding
    ],
    "extraction_fields": [
        "full_text",            # Full document text
        "summary",              # Brief summary
        "key_points",           # List of key points
        "document_metadata",    # Dict: page_count, word_count, author, etc.
        "structure",            # Dict: headings, sections
        "entities",             # Dict: people, orgs, dates, money, etc.
        "tables",               # List of extracted tables
        "action_items",         # List of {action, deadline, assignee, priority}
        "topics",               # List of topics
        "categories",           # List of categories
        "document_type",        # contract, proposal, report, etc.
        "sentiment",            # positive, negative, neutral
        "formality",            # formal, informal
        "confidentiality"       # public, internal, confidential
    ]
}


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================
SCHEMAS = {
    "image": IMAGE_SCHEMA,
    "audio": AUDIO_SCHEMA,
    "document": DOCUMENT_SCHEMA
}


def validate_extraction(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate an extraction against its schema.
    
    Args:
        extraction: The extraction dictionary to validate
    
    Returns:
        Dict with:
            - valid (bool): Whether extraction is valid
            - errors (list): List of error messages
            - warnings (list): List of warning messages
    
    Example:
        result = validate_extraction(my_extraction)
        if not result["valid"]:
            print("Errors:", result["errors"])
    """
    errors = []
    warnings = []
    
    # Check file_type exists
    file_type = extraction.get("file_type")
    if not file_type:
        return {
            "valid": False, 
            "errors": ["Missing 'file_type' field"],
            "warnings": []
        }
    
    # Check file_type is known
    if file_type not in SCHEMAS:
        return {
            "valid": False, 
            "errors": [f"Unknown file_type: '{file_type}'. Must be one of: {list(SCHEMAS.keys())}"],
            "warnings": []
        }
    
    schema = SCHEMAS[file_type]
    
    # Check required top-level fields
    for field in schema["required_fields"]:
        if field not in extraction:
            errors.append(f"Missing required field: '{field}'")
        elif extraction[field] is None:
            warnings.append(f"Field '{field}' is None")
        elif extraction[field] == "":
            if field != "embedding_text":  # embedding_text being empty is an error
                warnings.append(f"Field '{field}' is empty string")
            else:
                errors.append("'embedding_text' is empty - required for search")
    
    # Check extraction sub-fields
    ext = extraction.get("extraction", {})
    if not isinstance(ext, dict):
        errors.append("'extraction' must be a dictionary")
    else:
        for field in schema["extraction_fields"]:
            if field not in ext:
                warnings.append(f"Missing extraction field: '{field}'")
    
    # Check file_id format
    file_id = extraction.get("file_id", "")
    expected_prefix = {"image": "img_", "audio": "aud_", "document": "doc_"}.get(file_type)
    if expected_prefix and not file_id.startswith(expected_prefix):
        errors.append(f"file_id should start with '{expected_prefix}', got: '{file_id}'")
    
    # Check embedding_text is meaningful
    embedding_text = extraction.get("embedding_text", "")
    if len(embedding_text) < 10:
        errors.append("'embedding_text' is too short (< 10 chars)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def get_example_extraction(file_type: str) -> Dict[str, Any]:
    """
    Get an example extraction structure for reference.
    
    Useful for team members to see the expected format.
    """
    if file_type == "image":
        return {
            "file_id": "img_a1b2c3d4",
            "file_path": "/path/to/image.png",
            "file_type": "image",
            "file_hash": "abc123...",
            "file_size_bytes": 245000,
            "created_at": "2026-02-14T10:30:00",
            "modified_at": "2026-02-14T10:30:00",
            "extracted_at": "2026-02-14T10:35:00",
            "extraction": {
                "description": "A screenshot of...",
                "image_type": "screenshot",
                "ocr_text": "Text from image...",
                "objects_detected": ["computer", "text"],
                "entities": {
                    "people": [],
                    "locations": [],
                    "organizations": [],
                    "dates": [],
                    "software": ["VS Code"],
                    "urls": [],
                    "emails": [],
                    "phone_numbers": []
                },
                "categories": ["work", "programming"],
                "topics": ["coding", "development"],
                "action_items": [],
                "sentiment": "neutral",
                "contains_text": True,
                "contains_faces": False,
                "visual_summary": "Code editor screenshot"
            },
            "embedding_text": "Screenshot of code editor with Python code..."
        }
    
    elif file_type == "audio":
        return {
            "file_id": "aud_b2c3d4e5",
            "file_path": "/path/to/audio.mp3",
            "file_type": "audio",
            "file_hash": "def456...",
            "file_size_bytes": 5200000,
            "created_at": "2026-02-14T14:00:00",
            "modified_at": "2026-02-14T14:00:00",
            "extracted_at": "2026-02-14T14:05:00",
            "extraction": {
                "transcript_full": "Hey, this is a voice note...",
                "transcript_segments": [
                    {"start": 0.0, "end": 5.0, "text": "Hey, this is...", "speaker": "speaker_1"}
                ],
                "duration_seconds": 120,
                "duration_formatted": "2:00",
                "language": "en",
                "speakers": {"count": 1, "identified": ["speaker_1"]},
                "summary": "Voice note about project update",
                "key_points": ["Deadline is Friday", "Need to email John"],
                "entities": {
                    "people": ["John"],
                    "dates": [{"text": "Friday", "normalized": "2026-02-21"}],
                    "money": [],
                    "organizations": [],
                    "locations": []
                },
                "action_items": [
                    {"action": "Email John", "deadline": None, "priority": "medium", "confidence": 0.9}
                ],
                "topics": ["project", "deadlines"],
                "categories": ["work", "voice_note"],
                "audio_type": "voice_note",
                "sentiment": "neutral",
                "urgency": "medium"
            },
            "embedding_text": "Voice note about project. Deadline Friday. Need to email John."
        }
    
    elif file_type == "document":
        return {
            "file_id": "doc_c3d4e5f6",
            "file_path": "/path/to/document.pdf",
            "file_type": "document",
            "file_hash": "ghi789...",
            "file_size_bytes": 1250000,
            "created_at": "2026-02-10T09:00:00",
            "modified_at": "2026-02-14T11:00:00",
            "extracted_at": "2026-02-14T11:05:00",
            "extraction": {
                "full_text": "Project Proposal...",
                "summary": "Proposal for AI project with $50k budget",
                "key_points": ["Budget: $50,000", "Timeline: 6 months"],
                "document_metadata": {
                    "page_count": 12,
                    "word_count": 3500,
                    "author": "John Doe",
                    "title": "AI Project Proposal"
                },
                "structure": {
                    "headings": [
                        {"level": 1, "text": "Executive Summary", "page": 1}
                    ]
                },
                "entities": {
                    "people": ["John Doe"],
                    "organizations": ["Acme Corp"],
                    "dates": [{"text": "March 2026", "normalized": "2026-03-01"}],
                    "money": [{"text": "$50,000", "normalized": 50000, "currency": "USD"}],
                    "locations": []
                },
                "tables": [],
                "action_items": [
                    {"action": "Submit proposal", "deadline": "2026-02-28", "assignee": "John", "priority": "high"}
                ],
                "topics": ["AI", "project management", "budget"],
                "categories": ["work", "proposal"],
                "document_type": "proposal",
                "sentiment": "positive",
                "formality": "formal",
                "confidentiality": "internal"
            },
            "embedding_text": "AI Project Proposal. Budget $50,000. Timeline 6 months. Categories: work, proposal."
        }
    
    return {}
