// file: apps/web/hooks/useAIOrdering.ts

import { create } from 'zustand';
import { api } from '@/lib/api';

export type Message = {
  id: string;
  sender: 'user' | 'ai';
  content: any;
  contentType: 'text' | 'cart_preview' | 'error' | 'typing';
};

type AIOrderingState = {
  messages: Message[];
  isLoading: boolean;
  isOverlayVisible: boolean;
  setOverlayVisible: (isVisible: boolean) => void;
  sendMessage: (text: string) => Promise<void>;
};

export const useAIOrderingStore = create<AIOrderingState>((set, get) => ({
  messages: [],
  isLoading: false,
  isOverlayVisible: false,
  setOverlayVisible: (isVisible) => set({ isOverlayVisible: isVisible }),
  sendMessage: async (text) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: text,
      contentType: 'text',
    };
    
    set(state => ({
      messages: [...state.messages, userMessage, { id: 'typing', sender: 'ai', content: '', contentType: 'typing' }],
      isLoading: true,
    }));

    try {
      const response = await api.post('/ai-ordering/chat', { message: text });
      const aiResponses: Message[] = response.data.responses.map((res: any) => ({
        ...res,
        id: Date.now().toString() + Math.random(),
        sender: 'ai',
      }));

      set(state => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiResponses],
      }));
    } catch (error) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        sender: 'ai',
        content: 'I seem to be having trouble connecting. Please try again in a moment.',
        contentType: 'error',
      };
      set(state => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), errorMessage],
      }));
    } finally {
      set({ isLoading: false });
    }
  },
}));
