import { useState } from 'react';
import { motion } from 'motion/react';
import { Bot, User, Copy, Check } from 'lucide-react';

interface MessageBubbleProps {
  message: string;
  isBot: boolean;
  timestamp: Date;
  index: number;
}

export function MessageBubble({ message, isBot, timestamp, index }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: isBot ? -50 : 50, scale: 0.8 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ 
        duration: 0.5, 
        delay: index * 0.1,
        type: "spring",
        stiffness: 100
      }}
      className={`flex gap-4 ${isBot ? 'justify-start' : 'justify-end'} group`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {isBot && (
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-xl"
        >
          {/* Animated glow effect */}
          <motion.div
            className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-400 to-pink-400"
            animate={{
              opacity: [0.5, 1, 0.5],
              scale: [1, 1.1, 1],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <Bot className="w-6 h-6 text-white relative z-10" />
        </motion.div>
      )}
      
      <div className={`flex flex-col ${isBot ? 'items-start' : 'items-end'} max-w-[75%] relative`}>
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          transition={{ type: "spring", stiffness: 300 }}
          className={`relative px-6 py-4 rounded-3xl backdrop-blur-md ${
            isBot
              ? 'bg-gradient-to-br from-white/95 to-gray-50/95 border border-gray-200/60 text-gray-800 rounded-tl-md shadow-xl'
              : 'bg-gradient-to-br from-blue-500 via-blue-600 to-purple-600 text-white rounded-tr-md shadow-xl'
          }`}
        >
          {/* Shimmer effect on hover */}
          {isHovered && (
            <motion.div
              className="absolute inset-0 rounded-3xl overflow-hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <motion.div
                className={`absolute inset-0 ${
                  isBot 
                    ? 'bg-gradient-to-r from-transparent via-purple-100/50 to-transparent'
                    : 'bg-gradient-to-r from-transparent via-white/20 to-transparent'
                }`}
                animate={{
                  x: ['-100%', '100%'],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            </motion.div>
          )}

          <p className="text-sm leading-relaxed whitespace-pre-wrap relative z-10">{message}</p>
          
          {/* Floating particles inside bubble */}
          {isBot && (
            <>
              {[...Array(3)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-purple-400/30 rounded-full"
                  style={{
                    left: `${20 + i * 30}%`,
                    top: `${30 + i * 20}%`,
                  }}
                  animate={{
                    y: [-10, 10, -10],
                    opacity: [0.3, 0.6, 0.3],
                  }}
                  transition={{
                    duration: 2 + i * 0.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              ))}
            </>
          )}
          
          {/* Copy button */}
          <motion.button
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: isHovered ? 1 : 0, scale: isHovered ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            onClick={handleCopy}
            className={`absolute -top-3 ${isBot ? '-right-3' : '-left-3'} p-2 rounded-full ${
              isBot 
                ? 'bg-gradient-to-br from-purple-500 to-pink-500' 
                : 'bg-white/30 backdrop-blur-md'
            } shadow-lg hover:scale-110 transition-transform`}
          >
            {copied ? (
              <Check className={`w-4 h-4 ${isBot ? 'text-white' : 'text-white'}`} />
            ) : (
              <Copy className={`w-4 h-4 ${isBot ? 'text-white' : 'text-white'}`} />
            )}
          </motion.button>
        </motion.div>

        <motion.span 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-xs text-gray-500 mt-2 px-2"
        >
          {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </motion.span>
      </div>

      {!isBot && (
        <motion.div
          initial={{ scale: 0, rotate: 180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-xl"
        >
          {/* Animated glow effect */}
          <motion.div
            className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-400 to-cyan-400"
            animate={{
              opacity: [0.5, 1, 0.5],
              scale: [1, 1.1, 1],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <User className="w-6 h-6 text-white relative z-10" />
        </motion.div>
      )}
    </motion.div>
  );
}
