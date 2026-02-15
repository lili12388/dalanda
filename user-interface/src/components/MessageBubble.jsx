import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, Copy, Check, FileText, Image, Music } from 'lucide-react';

export function MessageBubble({ message, isBot, timestamp, index, sources = [], passages = {} }) {
    const [copied, setCopied] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [hoveredSource, setHoveredSource] = useState(null);

    const handleCopy = () => {
        navigator.clipboard.writeText(message);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // Get icon for source type
    const getSourceIcon = (source) => {
        const lower = source.toLowerCase();
        if (lower.endsWith('.pdf') || lower.endsWith('.docx') || lower.endsWith('.txt')) {
            return <FileText className="w-3 h-3" />;
        } else if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.m4a')) {
            return <Music className="w-3 h-3" />;
        } else if (lower.endsWith('.jpg') || lower.endsWith('.png') || lower.endsWith('.jpeg')) {
            return <Image className="w-3 h-3" />;
        }
        return <FileText className="w-3 h-3" />;
    };

    // Extract just filename from source path
    const getSourceName = (source) => {
        // Remove path and just get filename
        const parts = source.split(/[/\\]/);
        return parts[parts.length - 1];
    };

    // Convert string timestamp to Date object if needed, or handle it
    const timeString = timestamp instanceof Date
        ? timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : timestamp;

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
                    className={`relative px-6 py-4 rounded-3xl backdrop-blur-md ${isBot
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
                                className={`absolute inset-0 ${isBot
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
                        className={`absolute -top-3 ${isBot ? '-right-3' : '-left-3'} p-2 rounded-full ${isBot
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
                    {timeString}
                </motion.span>

                {/* Sources display for bot messages */}
                {isBot && sources && sources.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="mt-2 px-2"
                    >
                        <div className="flex flex-wrap gap-2">
                            {sources.map((source, i) => (
                                <div key={i} className="relative">
                                    <motion.span
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: 0.5 + i * 0.1 }}
                                        className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 rounded-full border border-purple-200/50 cursor-pointer hover:from-purple-200 hover:to-pink-200 transition-all"
                                        onMouseEnter={() => setHoveredSource(source)}
                                        onMouseLeave={() => setHoveredSource(null)}
                                    >
                                        {getSourceIcon(source)}
                                        <span className="max-w-[150px] truncate">{getSourceName(source)}</span>
                                    </motion.span>
                                    
                                    {/* Hover popup with passage text */}
                                    <AnimatePresence>
                                        {hoveredSource === source && passages[source] && (
                                            <motion.div
                                                initial={{ opacity: 0, y: 5, scale: 0.95 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                exit={{ opacity: 0, y: 5, scale: 0.95 }}
                                                transition={{ duration: 0.15 }}
                                                className="absolute bottom-full left-0 mb-2 z-50 w-80 max-w-sm"
                                            >
                                                <div className="bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl border border-gray-700">
                                                    <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700">
                                                        {getSourceIcon(source)}
                                                        <span className="font-semibold text-purple-300">{getSourceName(source)}</span>
                                                        {passages[source].page && (
                                                            <span className="text-gray-400">• page {passages[source].page}</span>
                                                        )}
                                                    </div>
                                                    <p className="text-gray-200 leading-relaxed line-clamp-6">
                                                        {passages[source].text?.substring(0, 300)}
                                                        {passages[source].text?.length > 300 && '...'}
                                                    </p>
                                                </div>
                                                {/* Arrow */}
                                                <div className="absolute -bottom-1 left-4 w-2 h-2 bg-gray-900 rotate-45 border-r border-b border-gray-700"></div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
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
