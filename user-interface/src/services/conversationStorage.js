// Conversation storage using localStorage
const STORAGE_KEY = 'dalanda_conversations';

export const conversationStorage = {
  // Get all conversations
  getAll() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Error loading conversations:', e);
      return [];
    }
  },

  // Get a specific conversation by ID
  get(id) {
    const conversations = this.getAll();
    return conversations.find(c => c.id === id) || null;
  },

  // Save a conversation (create or update)
  save(conversation) {
    const conversations = this.getAll();
    const index = conversations.findIndex(c => c.id === conversation.id);
    
    const updatedConv = {
      ...conversation,
      updatedAt: new Date().toISOString(),
    };

    if (index >= 0) {
      conversations[index] = updatedConv;
    } else {
      updatedConv.createdAt = new Date().toISOString();
      conversations.unshift(updatedConv);
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    return updatedConv;
  },

  // Create a new conversation
  create(title = 'New Chat') {
    const conversation = {
      id: Date.now().toString(),
      title,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return this.save(conversation);
  },

  // Delete a conversation
  delete(id) {
    const conversations = this.getAll().filter(c => c.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  },

  // Update conversation title based on first user message
  updateTitle(id, messages) {
    const conversation = this.get(id);
    if (!conversation) return;

    // Find first user message
    const firstUserMsg = messages.find(m => !m.isBot);
    if (firstUserMsg && conversation.title === 'New Chat') {
      // Truncate to first 30 chars
      const title = firstUserMsg.text.slice(0, 30) + (firstUserMsg.text.length > 30 ? '...' : '');
      conversation.title = title;
      conversation.messages = messages;
      this.save(conversation);
    } else {
      conversation.messages = messages;
      this.save(conversation);
    }
  },
};
