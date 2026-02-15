import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Loader2 } from 'lucide-react';

/**
 * Voice input button that records audio and sends to local Whisper for transcription.
 * 
 * Flow:
 * 1. User clicks mic ΓåÆ starts recording
 * 2. User clicks again ΓåÆ stops recording
 * 3. Audio sent to /api/transcribe (local Whisper)
 * 4. Transcribed text returned via onTranscript callback
 */
export function VoiceButton({ onTranscript, onStateChange, disabled, theme }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // Notify parent of state changes
  useEffect(() => {
    if (onStateChange) {
      if (isRecording) {
        onStateChange('recording');
      } else if (isProcessing) {
        onStateChange('transcribing');
      } else {
        onStateChange(null);
      }
    }
  }, [isRecording, isProcessing, onStateChange]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Create audio blob
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        
        // Send to backend for transcription
        setIsProcessing(true);
        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          
          const response = await fetch('http://localhost:8000/api/transcribe', {
            method: 'POST',
            body: formData,
          });
          
          if (!response.ok) {
            throw new Error('Transcription failed');
          }
          
          const data = await response.json();
          if (data.text && data.text.trim()) {
            onTranscript(data.text);
          }
        } catch (error) {
          console.error('Transcription error:', error);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('Please allow microphone access to use voice input.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleClick = () => {
    if (isProcessing) return;
    
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={handleClick}
      disabled={disabled || isProcessing}
      className={`relative p-4 rounded-2xl transition-all overflow-hidden ${
        isRecording
          ? 'bg-red-500 text-white shadow-xl shadow-red-500/30'
          : isProcessing
          ? 'bg-yellow-500/80 text-white cursor-wait'
          : disabled
          ? 'bg-white/10 text-white/30 cursor-not-allowed'
          : `bg-gradient-to-r ${theme} text-white shadow-xl hover:shadow-2xl`
      }`}
      title={isRecording ? 'Stop recording' : isProcessing ? 'Processing...' : 'Voice input'}
    >
      {/* Recording pulse animation */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            initial={{ scale: 1, opacity: 0.5 }}
            animate={{ scale: 2, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1, repeat: Infinity }}
            className="absolute inset-0 bg-red-500 rounded-2xl"
          />
        )}
      </AnimatePresence>

      {/* Icon */}
      {isProcessing ? (
        <Loader2 className="w-6 h-6 relative z-10 animate-spin" />
      ) : isRecording ? (
        <MicOff className="w-6 h-6 relative z-10" />
      ) : (
        <Mic className="w-6 h-6 relative z-10" />
      )}
    </motion.button>
  );
}
