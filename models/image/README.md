# Image Model - Qwen2.5-VL-3B via Ollama

**Owner:** Laith

## Model Download

```bash
# Pull the model with Ollama (already done!)
ollama pull qwen2.5vl:3b

# Verify it's installed
ollama list
```

## System Prompt

See `prompts.py` for the full extraction prompt. It extracts:
- description, image_type, ocr_text
- objects_detected, entities (people, locations, orgs, dates, software, urls, emails, phones)
- categories, topics, action_items
- sentiment, contains_text, contains_faces, contains_handwriting
- visual_summary

## Usage Example

```python
from extractors.image_extractor import ImageExtractor

extractor = ImageExtractor()
result = extractor.extract("path/to/image.png")

print(result["extraction"]["description"])
print(result["extraction"]["ocr_text"])
print(result["extraction"]["action_items"])
```

## Testing

```bash
# Add a test image
cp your_image.png tests/test_images/test_sample.png

# Run the test
python extractors/image_extractor.py
```

## Dependencies

```bash
pip install requests pillow
```

Ollama handles model loading - no torch/transformers needed!

## Model Size

- **Parameters:** 3B
- **Disk Space:** ~3.2 GB (via Ollama)
- **VRAM:** Managed by Ollama
