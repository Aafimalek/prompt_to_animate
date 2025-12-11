/**
 * API Service for Chat Operations
 * 
 * Handles all API calls to the backend for chat history management.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Chat {
    id: string;
    prompt: string;
    length: string;
    video_url: string;
    code: string;
    created_at: string;
}

export interface ChatListResponse {
    chats: Chat[];
    total: number;
}

/**
 * Fetch all chats for a specific user
 */
export async function getUserChats(clerkId: string): Promise<Chat[]> {
    try {
        const response = await fetch(`${API_BASE_URL}/chats/${clerkId}`);

        if (!response.ok) {
            console.error(`Failed to fetch chats: ${response.statusText}`);
            return []; // Return empty array instead of throwing
        }

        const data: ChatListResponse = await response.json();
        return data.chats;
    } catch (error) {
        // Handle network errors gracefully (e.g., backend not running)
        console.error('Error fetching user chats (backend may be unavailable):', error);
        return []; // Return empty array so the app continues to work
    }
}

/**
 * Get a specific chat with a fresh signed URL
 */
export async function getChatDetail(clerkId: string, chatId: string): Promise<Chat> {
    try {
        const response = await fetch(`${API_BASE_URL}/chats/${clerkId}/${chatId}`);

        if (!response.ok) {
            throw new Error(`Failed to fetch chat: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching chat detail:', error);
        throw error;
    }
}

/**
 * Delete a specific chat
 */
export async function deleteChat(clerkId: string, chatId: string): Promise<void> {
    try {
        const response = await fetch(`${API_BASE_URL}/chats/${clerkId}/${chatId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error(`Failed to delete chat: ${response.statusText}`);
        }
    } catch (error) {
        console.error('Error deleting chat:', error);
        throw error;
    }
}
