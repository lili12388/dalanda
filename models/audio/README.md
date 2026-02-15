# Audio Model - Whisper + Qwen2.5-3B-Instruct

**Owner:** [Team Member 2]

## Models Required

1. **Whisper (small)** - Speech-to-text
2. **Qwen2.5-3B-Instruct** - Transcript analysis

## Model Download

### Whisper
```bash
# Whisper downloads automatically on first use
pip install openai-whisper

# Or pre-download:
import whisper
model = whisper.load_model("small")  # Downloads to ~/.cache/whisper/
```

### Qwen2.5-3B (for transcript analysis)
```bash
# Using huggingface-cli
huggingface-cli download Qwen/Qwen2.5-3B-Instruct --local-dir ./models/audio/qwen2.5-3b

# Or in Python (auto-downloads to cache)
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
```

## System Prompt (for Qwen2.5-3B transcript analysis)

Use this system prompt after transcription:

```
You are an audio memory assistant that analyzes transcripts to extract structured information.

Given a transcript, extract:
1. SUMMARY: A concise summary of what was discussed (2-3 sentences)
2. KEY POINTS: Main takeaways or important statements
3. ENTITIES: People mentioned, dates, money amounts, organizations, locations
4. ACTION ITEMS: Tasks, to-dos, or follow-ups mentioned (with deadlines if stated)
5. TOPICS: Main subjects or themes discussed
6. AUDIO TYPE: Classify as: voice_note, meeting, lecture, interview, conversation, podcast
7. SENTIMENT: Overall tone (positive, negative, neutral)
8. URGENCY: Is this time-sensitive? (high, medium, low)

Respond in JSON format only:
{
    "summary": "...",
    "key_points": ["point1", "point2"],
    "entities": {
        "people": ["name1", "name2"],
        "dates": ["date1"],
        "money": ["$100"],
        "organizations": ["org1"],
        "locations": ["place1"]
    },
    "action_items": [
        {"action": "...", "deadline": null, "priority": "medium"}
    ],
    "topics": ["topic1", "topic2"],
    "audio_type": "voice_note",
    "sentiment": "neutral",
    "urgency": "medium"
}
```

## Usage Example

### Step 1: Transcribe with Whisper
```python
import whisper

# Load model
model = whisper.load_model("small")

# Transcribe
result = model.transcribe("path/to/audio.mp3", word_timestamps=True)

transcript = result["text"]
segments = result["segments"]  # [{start, end, text}, ...]
language = result["language"]
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

# Prepare prompt
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"Analyze this transcript:\n\n{transcript}"}
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

# Generate
output_ids = model.generate(**inputs, max_new_tokens=1024)
response = tokenizer.decode(output_ids[0], skip_special_tokens=True)
```

## Dependencies

```bash
pip install openai-whisper torch transformers accelerate
pip install ffmpeg-python  # For audio processing
```

Also install FFmpeg system-wide:
- Windows: `winget install ffmpeg` or download from https://ffmpeg.org/
- Linux: `sudo apt install ffmpeg`
- Mac: `brew install ffmpeg`

## Model Sizes

### Whisper Small
- **Parameters:** 244M
- **VRAM:** ~2 GB
- **Disk:** ~500 MB

### Qwen2.5-3B-Instruct
- **Parameters:** 3B
- **VRAM:** ~6-8 GB (float16)
- **Disk:** ~6 GB

**Total VRAM needed:** ~8-10 GB (can run sequentially to reduce)
