import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, Settings, Palette, Zap, Stars } from 'lucide-react';
import { MessageBubble } from './components/MessageBubble';
import { TypingIndicator } from './components/TypingIndicator';
import { ParticleBackground } from './components/ParticleBackground';
import { Sidebar } from './components/Sidebar';
import { VoiceButton } from './components/VoiceButton';
import { sendMessage } from './services/chatService';
import { conversationStorage } from './services/conversationStorage';

const themes = [
  { name: 'Ocean', gradient: 'from-blue-600 via-cyan-500 to-teal-600', accent: 'from-blue-500 to-cyan-500' },
  { name: 'Sunset', gradient: 'from-orange-500 via-pink-500 to-purple-600', accent: 'from-orange-400 to-pink-500' },
  { name: 'Forest', gradient: 'from-green-600 via-emerald-500 to-teal-600', accent: 'from-green-500 to-emerald-500' },
  { name: 'Galaxy', gradient: 'from-purple-600 via-pink-500 to-purple-700', accent: 'from-purple-500 to-pink-500' },
  { name: 'Fire', gradient: 'from-red-600 via-orange-500 to-yellow-600', accent: 'from-red-500 to-orange-500' },
  { name: 'Midnight', gradient: 'from-indigo-900 via-purple-800 to-pink-800', accent: 'from-indigo-600 to-purple-600' },
];

export default function App() {
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);

  const [messages, setMessages] = useState([
    {
      id: '1',
      text: "3aslema ena Dalanda",
      isBot: true,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [botState, setBotState] = useState(null); // 'thinking' | 'verifying' | null
  const [voiceState, setVoiceState] = useState(null); // 'recording' | 'transcribing' | null
  const [showSettings, setShowSettings] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(3);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load conversations on mount
  useEffect(() => {
    const savedConversations = conversationStorage.getAll();
    setConversations(savedConversations);
    
    // Load the most recent conversation or create a new one
    if (savedConversations.length > 0) {
      const recent = savedConversations[0];
      setCurrentConversationId(recent.id);
      if (recent.messages && recent.messages.length > 0) {
        setMessages(recent.messages.map(m => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })));
      }
    } else {
      // Create initial conversation
      const newConv = conversationStorage.create('New Chat');
      setConversations([newConv]);
      setCurrentConversationId(newConv.id);
    }
  }, []);

  // Save messages to current conversation when they change
  useEffect(() => {
    if (currentConversationId && messages.length > 0) {
      const messagesToSave = messages.map(m => ({
        ...m,
        timestamp: m.timestamp.toISOString()
      }));
      conversationStorage.updateTitle(currentConversationId, messagesToSave);
      
      // Update local state
      setConversations(conversationStorage.getAll());
    }
  }, [messages, currentConversationId]);

  const handleNewConversation = useCallback(() => {
    const newConv = conversationStorage.create('New Chat');
    setConversations(conversationStorage.getAll());
    setCurrentConversationId(newConv.id);
    setMessages([{
      id: '1',
      text: "3aslema ena Dalanda",
      isBot: true,
      timestamp: new Date(),
    }]);
  }, []);

  const handleSelectConversation = useCallback((id) => {
    const conv = conversationStorage.get(id);
    if (conv) {
      setCurrentConversationId(id);
      if (conv.messages && conv.messages.length > 0) {
        setMessages(conv.messages.map(m => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })));
      } else {
        setMessages([{
          id: '1',
          text: "3aslema ena Dalanda",
          isBot: true,
          timestamp: new Date(),
        }]);
      }
    }
  }, []);

  const handleDeleteConversation = useCallback((id) => {
    conversationStorage.delete(id);
    const remaining = conversationStorage.getAll();
    setConversations(remaining);
    
    if (id === currentConversationId) {
      if (remaining.length > 0) {
        handleSelectConversation(remaining[0].id);
      } else {
        handleNewConversation();
      }
    }
  }, [currentConversationId, handleSelectConversation, handleNewConversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (inputValue.trim() === '') return;

    const userMessage = {
      id: Date.now().toString(),
      text: inputValue,
      isBot: false,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);
    setBotState('thinking');

    try {
      // Start API call
      const responsePromise = sendMessage(userMessage.text);
      
      // After 1s switch to 'verifying' state (matches backend pipeline timing)
      const verifyingTimer = setTimeout(() => {
        setBotState('verifying');
      }, 1000);
      
      // Wait for the response
      const response = await responsePromise;
      
      // Ensure "verifying" state is visible for at least 500ms
      clearTimeout(verifyingTimer);
      setBotState('verifying');
      await new Promise(resolve => setTimeout(resolve, 500));

      const botMessage = {
        id: (Date.now() + 1).toString(),
        text: response.text,
        isBot: true,
        timestamp: new Date(),
        sources: response.sources || [],
        passages: response.passages || {},
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error getting response", error);
    } finally {
      setIsTyping(false);
      setBotState(null);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle voice transcription - auto-send after receiving text
  const handleVoiceTranscript = async (text) => {
    if (text && text.trim()) {
      setInputValue(text);
      // Auto-send after a brief delay to show the text
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const userMessage = {
        id: Date.now().toString(),
        text: text,
        isBot: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue('');
      setIsTyping(true);
      setBotState('thinking');

      try {
        // Start API call
        const responsePromise = sendMessage(text);
        
        // After 1s switch to 'verifying' state
        const verifyingTimer = setTimeout(() => {
          setBotState('verifying');
        }, 1000);
        
        // Wait for response
        const response = await responsePromise;
        
        // Ensure "verifying" state shows briefly
        clearTimeout(verifyingTimer);
        setBotState('verifying');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const botMessage = {
          id: (Date.now() + 1).toString(),
          text: response.text,
          isBot: true,
          timestamp: new Date(),
          sources: response.sources || [],
          passages: response.passages || {},
        };
        setMessages((prev) => [...prev, botMessage]);
      } catch (error) {
        console.error("Error getting response", error);
      } finally {
        setIsTyping(false);
        setBotState(null);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        theme={themes[currentTheme]}
      />

      <ParticleBackground />

      {/* Animated background gradient */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        animate={{
          background: [
            'radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
            'radial-gradient(circle at 80% 50%, rgba(236, 72, 153, 0.1) 0%, transparent 50%)',
            'radial-gradient(circle at 50% 80%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)',
            'radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
          ],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ 
          opacity: 1, 
          scale: 1, 
          y: 0,
          marginLeft: sidebarOpen ? '140px' : '0px'
        }}
        transition={{ duration: 0.6, type: "spring", stiffness: 100 }}
        className="w-full max-w-5xl h-[92vh] bg-white/10 backdrop-blur-2xl rounded-3xl shadow-2xl flex flex-col min-h-0 overflow-hidden border border-white/20 relative z-10"
      >
        {/* Animated border glow */}
        <motion.div
          className={`absolute inset-0 rounded-3xl bg-gradient-to-r ${themes[currentTheme].gradient} opacity-20 blur-xl pointer-events-none`}
          animate={{
            opacity: [0.1, 0.3, 0.1],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Header */}
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className={`relative bg-gradient-to-r ${themes[currentTheme].gradient} p-6 text-white overflow-hidden`}
        >
          {/* Animated pattern overlay */}
          <motion.div
            className="absolute inset-0 opacity-10 pointer-events-none"
            animate={{
              backgroundPosition: ['0% 0%', '100% 100%'],
            }}
            transition={{
              duration: 20,
              repeat: Infinity,
              repeatType: "reverse",
            }}
            style={{
              backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
              backgroundSize: '30px 30px',
            }}
          />

          {/* Floating stars */}
          {[...Array(10)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 bg-white rounded-full"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
              animate={{
                opacity: [0, 1, 0],
                scale: [0, 1.5, 0],
              }}
              transition={{
                duration: 2 + Math.random() * 2,
                repeat: Infinity,
                delay: Math.random() * 2,
              }}
            />
          ))}

          <div className="flex items-center justify-between relative z-10">
            <div className="flex items-center gap-4">
              <motion.div
                className="relative"
                animate={{
                  rotate: [0, 360],
                }}
                transition={{
                  rotate: { duration: 4, repeat: Infinity, ease: "linear" },
                }}
              >
                <Sparkles className="w-12 h-12" />
                <motion.div
                  className="absolute inset-0"
                  animate={{
                    opacity: [0, 1, 0],
                    scale: [0.8, 1.5, 0.8],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                >
                  <Stars className="w-12 h-12" />
                </motion.div>
              </motion.div>
              <div>
                <motion.h1
                  className="text-3xl font-bold flex items-center gap-3"
                  animate={{
                    textShadow: [
                      '0 0 20px rgba(255,255,255,0.5)',
                      '0 0 30px rgba(255,255,255,0.8)',
                      '0 0 20px rgba(255,255,255,0.5)',
                    ],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                >
                  Dalanda
                  <motion.div
                    animate={{ rotate: [0, 10, 0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Zap className="w-7 h-7 text-yellow-300" />
                  </motion.div>
                </motion.h1>
                <p className="text-white/90 text-sm mt-1">7adher Docteur ✨</p>
              </div>
            </div>

            <motion.button
              whileHover={{ scale: 1.1, rotate: 90 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowSettings(!showSettings)}
              className="p-3 rounded-2xl bg-white/20 hover:bg-white/30 backdrop-blur-sm transition-colors border border-white/30"
            >
              <Settings className="w-6 h-6" />
            </motion.button>
          </div>

          {/* Theme selector */}
          <AnimatePresence>
            {showSettings && (
              <motion.div
                initial={{ opacity: 0, height: 0, y: -20 }}
                animate={{ opacity: 1, height: 'auto', y: 0 }}
                exit={{ opacity: 0, height: 0, y: -20 }}
                className="mt-6 overflow-hidden"
              >
                <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/20">
                  <div className="flex items-center gap-3 mb-3">
                    <Palette className="w-5 h-5" />
                    <span className="font-medium">Choose Your Theme</span>
                  </div>
                  <div className="flex gap-3 flex-wrap">
                    {themes.map((theme, index) => (
                      <motion.button
                        key={index}
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: index * 0.05 }}
                        whileHover={{ scale: 1.15, y: -5 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setCurrentTheme(index)}
                        className={`relative w-12 h-12 rounded-xl bg-gradient-to-r ${theme.gradient} shadow-lg ${currentTheme === index
                            ? 'ring-4 ring-white/50 ring-offset-2 ring-offset-transparent scale-110'
                            : ''
                          }`}
                      >
                        {currentTheme === index && (
                          <motion.div
                            layoutId="activeTheme"
                            className="absolute inset-0 rounded-xl bg-white/20"
                          />
                        )}
                      </motion.button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6 overscroll-contain" style={{ touchAction: 'auto' }}>
          <AnimatePresence mode="popLayout">
            {messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message.text}
                isBot={message.isBot}
                timestamp={message.timestamp}
                index={index}
                sources={message.sources}
                passages={message.passages}
              />
            ))}
            {voiceState && <TypingIndicator key="voice" state={voiceState} />}
            {isTyping && <TypingIndicator key="typing" state={botState || 'thinking'} />}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="border-t border-white/10 p-5 bg-white/5 backdrop-blur-xl"
        >
          <div className="flex gap-4 items-end">
            <div className="flex-1 relative">
              <motion.div
                className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${themes[currentTheme].accent} opacity-20 blur-xl pointer-events-none`}
                animate={{
                  opacity: inputValue ? [0.2, 0.4, 0.2] : 0.1,
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  repeatType: "reverse",
                }}
              />
              <motion.input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="relative w-full px-6 py-4 border-2 border-white/20 rounded-2xl focus:border-white/40 focus:outline-none transition-all bg-white/10 backdrop-blur-md text-white placeholder-white/50"
                whileFocus={{ scale: 1.01 }}
              />
              <AnimatePresence>
                {inputValue && (
                  <motion.div
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    exit={{ scale: 0, rotate: 180 }}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full"
                  >
                    {inputValue.length}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <VoiceButton 
              onTranscript={handleVoiceTranscript}
              onStateChange={setVoiceState}
              disabled={isTyping}
              theme={themes[currentTheme]}
            />

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSend}
              disabled={inputValue.trim() === ''}
              className={`relative p-4 rounded-2xl transition-all overflow-hidden ${inputValue.trim() === ''
                  ? 'bg-white/10 text-white/30 cursor-not-allowed'
                  : `bg-gradient-to-r ${themes[currentTheme].gradient} text-white shadow-xl`
                }`}
            >
              {inputValue.trim() !== '' && (
                <>
                  <motion.div
                    className="absolute inset-0 bg-white"
                    initial={{ x: '-100%', opacity: 0.3 }}
                    whileHover={{ x: '100%' }}
                    transition={{ duration: 0.6 }}
                  />
                  <motion.div
                    className={`absolute inset-0 bg-gradient-to-r ${themes[currentTheme].gradient}`}
                    animate={{
                      opacity: [0.5, 1, 0.5],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                    }}
                  />
                </>
              )}
              <Send className="w-6 h-6 relative z-10" />
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
