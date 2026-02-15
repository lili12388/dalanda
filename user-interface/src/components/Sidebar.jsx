import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Plus, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';

export function Sidebar({ 
  conversations, 
  currentConversationId, 
  onSelectConversation, 
  onNewConversation, 
  onDeleteConversation,
  isOpen,
  onToggle,
  theme
}) {
  return (
    <>
      {/* Toggle button when sidebar is closed */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            onClick={onToggle}
            className={`fixed left-4 top-1/2 -translate-y-1/2 z-50 p-2 bg-gradient-to-r ${theme?.gradient || 'from-purple-600 via-pink-500 to-purple-700'} rounded-xl border border-white/20 text-white hover:opacity-90 transition-opacity shadow-lg`}
          >
            <ChevronRight className="w-5 h-5" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed left-0 top-0 h-full w-[260px] bg-slate-900/80 backdrop-blur-xl border-r border-white/10 z-50 flex flex-col overflow-hidden"
          >
            {/* Theme gradient overlay */}
            <motion.div
              className={`absolute inset-0 bg-gradient-to-b ${theme?.gradient || 'from-purple-600 via-pink-500 to-purple-700'} opacity-10 pointer-events-none`}
              animate={{ opacity: [0.05, 0.15, 0.05] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            />
            {/* Header */}
            <div className="relative p-4 border-b border-white/10 flex items-center justify-between z-10">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onNewConversation}
                className={`flex-1 flex items-center gap-3 px-4 py-3 bg-gradient-to-r ${theme?.accent || 'from-purple-500 to-pink-500'} hover:opacity-90 rounded-xl border border-white/20 text-white transition-opacity shadow-lg`}
              >
                <Plus className="w-5 h-5" />
                <span className="font-medium">New Chat</span>
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onToggle}
                className="ml-2 p-2 hover:bg-white/10 rounded-lg transition-colors text-white/70 hover:text-white"
              >
                <ChevronLeft className="w-5 h-5" />
              </motion.button>
            </div>

            {/* Conversations List */}
            <div className="relative flex-1 overflow-y-auto p-2 space-y-1 z-10">
              <AnimatePresence>
                {conversations.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center text-white/40 py-8 px-4"
                  >
                    <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">No conversations yet</p>
                    <p className="text-xs mt-1">Start a new chat!</p>
                  </motion.div>
                ) : (
                  conversations.map((conv, index) => (
                    <motion.div
                      key={conv.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ delay: index * 0.02 }}
                      className="group relative"
                    >
                      <motion.button
                        whileHover={{ x: 4 }}
                        onClick={() => onSelectConversation(conv.id)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-all ${
                          currentConversationId === conv.id
                            ? `bg-gradient-to-r ${theme?.accent || 'from-purple-500 to-pink-500'} bg-opacity-30 text-white shadow-md`
                            : 'text-white/70 hover:bg-white/10 hover:text-white'
                        }`}
                      >
                        <MessageSquare className="w-4 h-4 flex-shrink-0" />
                        <div className="flex-1 overflow-hidden">
                          <p className="text-sm font-medium truncate">{conv.title}</p>
                          <p className="text-xs text-white/40 truncate">
                            {formatDate(conv.updatedAt || conv.createdAt)}
                          </p>
                        </div>
                      </motion.button>
                      
                      {/* Delete button */}
                      <motion.button
                        initial={{ opacity: 0 }}
                        whileHover={{ scale: 1.1 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(conv.id);
                        }}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-white/50 hover:text-red-400 transition-all"
                      >
                        <Trash2 className="w-4 h-4" />
                      </motion.button>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="relative p-4 border-t border-white/10 z-10">
              <p className="text-xs text-white/50 text-center">
                {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overlay for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          />
        )}
      </AnimatePresence>
    </>
  );
}

function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    return 'Today';
  } else if (days === 1) {
    return 'Yesterday';
  } else if (days < 7) {
    return `${days} days ago`;
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
}
