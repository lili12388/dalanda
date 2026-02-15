import { motion } from 'motion/react';
import { Bot } from 'lucide-react';

export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.8 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.8 }}
      className="flex gap-4 justify-start"
    >
      <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-xl">
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
      </div>
      
      <div className="px-6 py-4 rounded-3xl bg-gradient-to-br from-white/95 to-gray-50/95 border border-gray-200/60 rounded-tl-md shadow-xl backdrop-blur-md">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2.5 h-2.5 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full"
              animate={{
                y: [0, -12, 0],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 0.9,
                repeat: Infinity,
                delay: i * 0.15,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
