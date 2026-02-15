# Document Model - PyMuPDF + Qwen2.5-3B-Instruct

**Owner:** [Team Member 3]

## Models/Tools Required

1. **PyMuPDF (fitz)** - PDF text extraction
2. **python-docx** - Word document extraction
3. **Qwen2.5-3B-Instruct** - Document analysis

## Installation

### Text Extraction Libraries
```bash
pip install PyMuPDF python-docx openpyxl  # PDF, DOCX, XLSX
```

### Qwen2.5-3B (for document analysis)
```bash
# Using huggingface-cli
huggingface-cli download Qwen/Qwen2.5-3B-Instruct --local-dir ./models/document/qwen2.5-3b

# Or in Python (auto-downloads to cache)
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
```

## System Prompt (for Qwen2.5-3B document analysis)

Use this after extracting text from the document:

```
You are a document memory assistant that analyzes text documents to extract structured information.

Given document text, extract:
1. TITLE: The document title or a generated one if not found
2. SUMMARY: A concise summary of the document (2-4 sentences)
3. DOCUMENT TYPE: Classify as: report, email, notes, article, code, spreadsheet, form, contract, resume, invoice, other
4. KEY POINTS: Main takeaways or important information
5. ENTITIES: People, organizations, dates, money amounts, locations mentioned
6. TOPICS: Main subjects or themes
7. ACTION ITEMS: Any tasks, to-dos, or follow-ups mentioned
8. METADATA: Language, approximate word count, structure (sections/paragraphs)

Respond in JSON format only:
{
    "title": "...",
    "summary": "...",
    "document_type": "report",
    "key_points": ["point1", "point2"],
    "entities": {
        "people": ["name1"],
        "organizations": ["org1"],
        "dates": ["2024-01-15"],
        "money": ["$1,000"],
        "locations": ["New York"]
    },
    "topics": ["topic1", "topic2"],
    "action_items": [
        {"action": "...", "deadline": null, "priority": "medium"}
    ],
    "language": "en",
    "structure": {
        "has_headings": true,
        "sections": ["Introduction", "Body", "Conclusion"]
    }
}
```

## Usage Example

### Step 1: Extract Text

#### PDF Files
```python
import fitz  # PyMuPDF

def extract_pdf(file_path: str) -> dict:
    doc = fitz.open(file_path)
    
    pages = []
    full_text = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page": page_num + 1,
            "text": text
        })
        full_text.append(text)
    
    return {
        "text": "\n\n".join(full_text),
        "pages": pages,
        "page_count": len(doc),
        "metadata": doc.metadata  # title, author, etc.
    }
```

#### Word Documents (.docx)
```python
from docx import Document

def extract_docx(file_path: str) -> dict:
    doc = Document(file_path)
    
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    
    # Extract headings
    headings = [
        p.text for p in doc.paragraphs 
        if p.style.name.startswith('Heading')
    ]
    
    return {
        "text": "\n\n".join(paragraphs),
        "paragraphs": paragraphs,
        "headings": headings,
        "paragraph_count": len(paragraphs)
    }
```

#### Plain Text Files
```python
def extract_txt(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    return {
        "text": text,
        "line_count": len(text.splitlines()),
        "word_count": len(text.split())
    }
```

### Step 2: Analyze with Qwen2.5-3B
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load model
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

# Truncate text if too long (keep first and last parts)
MAX_CHARS = 8000
if len(text) > MAX_CHARS:
    text = text[:MAX_CHARS//2] + "\n\n[...truncated...]\n\n" + text[-MAX_CHARS//2:]

# Prepare prompt
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"Analyze this document:\n\n{text}"}
]

text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text_input, return_tensors="pt").to(model.device)

# Generate
output_ids = model.generate(**inputs, max_new_tokens=1024)
response = tokenizer.decode(output_ids[0], skip_special_tokens=True)
```

## Dependencies

```bash
pip install PyMuPDF python-docx openpyxl torch transformers accelerate
```

## Supported File Types

| Extension | Library | Notes |
|-----------|---------|-------|
| `.pdf` | PyMuPDF | Text extraction, metadata |
| `.docx` | python-docx | Full support |
| `.doc` | antiword/textract | Legacy format, may need system tools |
| `.txt` | Built-in | Plain text |
| `.md` | Built-in | Markdown as plain text |
| `.xlsx` | openpyxl | Spreadsheets |
| `.csv` | Built-in csv | Tabular data |

## Model Size

### Qwen2.5-3B-Instruct
- **Parameters:** 3B
- **VRAM:** ~6-8 GB (float16)
- **Disk:** ~6 GB

**Note:** Text extraction (PyMuPDF, python-docx) uses minimal memory - only the LLM needs GPU.
