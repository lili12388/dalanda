"""
FastAPI Backend for AI MINDS Chat
Connects the React UI to the RAG pipeline.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import tempfile
import os

# Set up FFmpeg path from imageio-ffmpeg (bundled)
FFMPEG_PATH = None
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    # Add the directory to PATH and also create an alias
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    print(f"Γ£à FFmpeg found: {FFMPEG_PATH}")
except ImportError:
    print("ΓÜá∩╕Å imageio-ffmpeg not installed, voice input may not work")

# Import our chat pipeline
from chat_agent import chat, preload_models
from query.memory import ConversationMemory

# Whisper model (lazy loaded)
whisper_model = None

def get_whisper_model():
    """Load whisper model on first use (saves VRAM until needed)."""
    global whisper_model
    if whisper_model is None:
        print("≡ƒÄñ Loading Whisper model (first voice request)...")
        import whisper
        whisper_model = whisper.load_model("base")  # ~150MB, good balance
        print("Γ£à Whisper model ready!")
    return whisper_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models into VRAM when server starts."""
    print("\n≡ƒÜÇ Starting Dalanda API...")
    preload_models()  # Load Phi-3.5 and Llama-3.2 into VRAM
    print("Γ£à Models ready! Server accepting requests.\n")
    yield
    print("\n≡ƒæï Shutting down...")


app = FastAPI(title="AI MINDS API", version="1.0.0", lifespan=lifespan)

# Allow CORS for React frontend (multiple ports in case of conflicts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session memory storage (in production, use Redis or database)
sessions: dict[str, ConversationMemory] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    skip_verification: bool = False


class SourcePassage(BaseModel):
    source: str
    text: str
    type: str
    page: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    passages: List[SourcePassage]
    confidence: int
    is_grounded: bool
    issues: Optional[List[str]] = None


@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI MINDS API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint.
    
    Request:
        - message: User's question
        - session_id: Optional session ID for conversation memory
        - skip_verification: Skip verifier for faster response
    
    Response:
        - answer: The bot's response
        - sources: List of source file names
        - confidence: 0-100 confidence score
        - is_grounded: Whether answer is supported by sources
        - issues: Any detected issues with the answer
    """
    try:
        # Get or create session memory
        if request.session_id not in sessions:
            sessions[request.session_id] = ConversationMemory(max_history=5)
        memory = sessions[request.session_id]
        
        # Call the chat pipeline
        result = chat(
            question=request.message,
            verbose=False,
            skip_verification=request.skip_verification,
            memory=memory
        )
        
        # Extract source names
        sources = result.get("sources", [])
        if sources and isinstance(sources[0], dict):
            source_names = [s.get("file", str(s)) for s in sources]
        else:
            source_names = sources if sources else []
        
        # Get passages for hover popups
        passages = result.get("passages", [])
        
        # If the answer indicates "I don't know", don't show sources
        answer_lower = result["answer"].lower()
        idk_phrases = [
            "i couldn't find", "i could not find", "unable to provide",
            "i don't have", "i do not have", "no relevant information",
            "not contain this information", "does not include",
            "i'm unable to", "i am unable to", "cannot answer",
            "don't have information", "no information about",
            "i'm sorry", "i am sorry", "i cannot provide",
            "do not contain information", "doesn't contain",
            "cannot provide an answer", "therefore, i cannot",
            "not contain information regarding"
        ]
        if any(phrase in answer_lower for phrase in idk_phrases):
            source_names = []
            passages = []
        
        # Add to conversation memory
        memory.add(request.message, result["answer"], source_names)
        
        return ChatResponse(
            answer=result["answer"],
            sources=source_names,
            passages=passages,
            confidence=result.get("confidence", 0),
            is_grounded=result.get("is_grounded", False),
            issues=result.get("issues", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear")
def clear_session(session_id: str = "default"):
    """Clear conversation memory for a session."""
    if session_id in sessions:
        sessions[session_id].clear()
    return {"status": "cleared", "session_id": session_id}


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using local Whisper model.
    
    Accepts audio file (webm, wav, mp3, etc.) and returns transcribed text.
    """
    tmp_path = None
    wav_path = None
    try:
        # Save uploaded file to temp location
        content = await audio.read()
        print(f"≡ƒÄñ Received audio: {len(content)} bytes")
        
        if len(content) < 100:
            return {"text": "", "success": False, "error": "Audio too short"}
        
        # Create temp files
        import uuid
        import subprocess
        
        tmp_id = uuid.uuid4().hex
        tmp_path = os.path.join(tempfile.gettempdir(), f"whisper_{tmp_id}.webm")
        wav_path = os.path.join(tempfile.gettempdir(), f"whisper_{tmp_id}.wav")
        
        with open(tmp_path, "wb") as f:
            f.write(content)
        
        print(f"≡ƒôü Saved to: {tmp_path}")
        
        # Convert webm to wav using ffmpeg (imageio_ffmpeg provides the binary)
        if FFMPEG_PATH:
            print(f"≡ƒöä Converting to WAV using: {FFMPEG_PATH}")
            result = subprocess.run(
                [FFMPEG_PATH, "-i", tmp_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Γ¥î FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg conversion failed: {result.stderr[:200]}")
            print(f"Γ£à Converted to: {wav_path}")
            audio_file = wav_path
        else:
            audio_file = tmp_path
        
        # Load whisper model (lazy load on first request)
        model = get_whisper_model()
        
        # Load audio as numpy array (avoids Whisper calling ffmpeg internally)
        print("≡ƒöä Loading audio data...")
        import wave
        import numpy as np
        
        with wave.open(audio_file, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe using numpy array (bypasses ffmpeg)
        print("≡ƒöä Transcribing...")
        result = model.transcribe(audio_data, fp16=False, language="en")
        text = result["text"].strip()
        print(f"Γ£à Transcription: {text[:100]}...")
        
        return {"text": text, "success": True}
        
    except Exception as e:
        import traceback
        print(f"Γ¥î Transcription error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up temp files
        for path in [tmp_path, wav_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("≡ƒºá AI MINDS API Server")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /api/chat  - Send a message")
    print("  POST /api/clear - Clear conversation")
    print("  GET  /health    - Health check")
    print("\nStarting server on http://localhost:8000")
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
