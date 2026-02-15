/**
 * AI MINDS Chat Service
 * Connects to the FastAPI backend for RAG-powered responses.
 */

const API_URL = 'http://localhost:8000/api';

/**
 * Send a message to the AI MINDS backend.
 * 
 * @param {string} message - The user's input message.
 * @param {string} sessionId - Optional session ID for conversation memory.
 * @returns {Promise<{text: string, sources: string[], confidence: number, isGrounded: boolean}>}
 */
export const sendMessage = async (message, sessionId = 'default') => {
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                skip_verification: false
            }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        
        // Build passages map: source -> passage text
        const passagesMap = {};
        if (data.passages) {
            data.passages.forEach(p => {
                passagesMap[p.source] = {
                    text: p.text,
                    type: p.type,
                    page: p.page
                };
            });
        }
        
        return {
            text: data.answer,
            sources: data.sources || [],
            passages: passagesMap,
            confidence: data.confidence || 0,
            isGrounded: data.is_grounded || false,
            issues: data.issues || [],
            timestamp: new Date().toISOString(),
        };
    } catch (error) {
        console.error('Chat service error:', error);
        
        // Return error message if API fails
        return {
            text: "Sorry, I couldn't connect to the AI backend. Make sure the server is running (python api.py).",
            sources: [],
            passages: {},
            confidence: 0,
            isGrounded: false,
            issues: [error.message],
            timestamp: new Date().toISOString(),
        };
    }
};

/**
 * Clear the conversation memory for a session.
 * 
 * @param {string} sessionId - The session ID to clear.
 */
export const clearSession = async (sessionId = 'default') => {
    try {
        await fetch(`${API_URL}/clear?session_id=${sessionId}`, {
            method: 'POST',
        });
    } catch (error) {
        console.error('Failed to clear session:', error);
    }
};
