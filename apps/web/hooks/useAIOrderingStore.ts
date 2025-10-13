'use client';

import { create } from 'zustand';

// The final, complete interface for all possible message types
export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion';
  content: any;
  options?: string[];   // For interactive buttons
  products?: any[];   // For product carousels
  reason?: string;      // For "Explainable AI"
}

interface AIOrderingState {
  messages: Message[];
  isLoading: boolean;
  isProcessing: boolean; // For the "cinematic" loading animation
  isOverlayVisible: boolean;
  setOverlayVisible: (isVisible: boolean) => void;
  sendMessage: (text: string) => void;
}

let messageId = 0;

export const useAIOrderingStore = create<AIOrderingState>((set, get) => ({
  messages: [],
  isLoading: false,
  isProcessing: false,
  isOverlayVisible: false,
  setOverlayVisible: (isVisible) => set({ isOverlayVisible: isVisible }),
  sendMessage: async (text) => {
    if (!text || get().isLoading) return;

    const userMessage: Message = { id: messageId++, sender: 'user', contentType: 'text', content: text };
    const typingIndicator: Message = { id: messageId++, sender: 'ai', contentType: 'typing', content: null };

    set((state) => ({
      messages: [...state.messages, userMessage, typingIndicator],
      isLoading: true,
      isProcessing: true, // Trigger the cinematic loader
    }));

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/ai-ordering/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const aiData = await response.json();

      // The final mapping function that handles all rich data from the backend
      const aiMessages: Message[] = aiData.responses.map((res: any) => ({
          id: messageId++,
          sender: 'ai',
          contentType: res.contentType,
          content: res.content,
          options: res.options,
          products: res.products,
          reason: res.reason,
      }));

      set((state) => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiMessages],
        isLoading: false,
        isProcessing: false, // Turn off the cinematic loader
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
        isProcessing: false, // Turn off the loader on error too
      }));
    }
  },
}));
