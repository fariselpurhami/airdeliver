// In apps/web/hooks/useAIOrdering.ts

import { create } from 'zustand';

export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart' | 'error' | 'typing';
  content: any;
}

interface AIOrderingState {
  messages: Message[];
  isLoading: boolean;
  isOverlayVisible: boolean;
  setOverlayVisible: (isVisible: boolean) => void;
  sendMessage: (text: string) => void;
}

let messageId = 0;

export const useAIOrderingStore = create<AIOrderingState>((set, get) => ({
  messages: [],
  isLoading: false,
  isOverlayVisible: false,
  setOverlayVisible: (isVisible) => set({ isOverlayVisible: isVisible }),
  sendMessage: async (text) => {
    if (!text || get().isLoading) return;

    const userMessage: Message = {
      id: messageId++,
      sender: 'user',
      contentType: 'text',
      content: text,
    };

    const typingIndicator: Message = {
        id: messageId++,
        sender: 'ai',
        contentType: 'typing',
        content: null,
    };

    set((state) => ({
      messages: [...state.messages, userMessage, typingIndicator],
      isLoading: true,
    }));

    // --- Backend API Call ---
    try {
      // This is where you would call your real AI backend API
      const response = await fetch('/api/v1/ai-ordering/chat', { // NOTE: Make sure this is the correct API endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const aiData = await response.json();
      
      // Assuming the backend returns a list of response parts
      const aiMessages: Message[] = aiData.responses.map((res: any) => ({
          id: messageId++,
          sender: 'ai',
          contentType: res.type, // e.g., 'text' or 'cart'
          content: res.content,
      }));

      set((state) => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiMessages],
        isLoading: false,
      }));

    } catch (error) {
      const errorMessage: Message = {
        id: messageId++,
        sender: 'ai',
        contentType: 'error',
        content: 'Sorry, I am having trouble connecting. Please try again later.',
      };
      set((state) => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), errorMessage],
        isLoading: false,
      }));
    }
  },
}));
