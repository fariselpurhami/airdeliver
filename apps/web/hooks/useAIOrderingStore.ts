'use client';

import { create } from 'zustand';

type PaymentDetails = {
  clientSecret: string;
  orderId: number;
  total: number;
};

export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'payment_intent';
  content: any;
  options?: string[];   
  products?: any[];   
  reason?: string;
  ai_notes?: string;
}

interface AIOrderingState {
  messages: Message[];
  isLoading: boolean;
  isProcessing: boolean; 
  isOverlayVisible: boolean;
  suggestedProductIds: number[] | null;
  paymentDetails: PaymentDetails | null;
  setOverlayVisible: (isVisible: boolean) => void;
  setSuggestedProductIds: (ids: number[] | null) => void;
  sendMessage: (text: string, token: string) => void;
  addLocalAIMessage: (content: string, type: 'error' | 'text') => void;
  clearPayment: () => void;
  resetChat: () => void;
}

let messageId = 1;

const initialWelcomeMessage: Message = {
  id: 0,
  sender: 'ai',
  contentType: 'text',
  content: 'Autonomous AI. Ready to assist your order."',
};

export const useAIOrderingStore = create<AIOrderingState>((set, get) => ({
  messages: [initialWelcomeMessage],
  isLoading: false,
  isProcessing: false,
  isOverlayVisible: false,
  suggestedProductIds: null,
  paymentDetails: null,

  setOverlayVisible: (isVisible) => {
    set({ isOverlayVisible: isVisible });
    if (!isVisible) {
      get().resetChat();
    }
  },
  
  setSuggestedProductIds: (ids) => set({ suggestedProductIds: ids }),

  clearPayment: () => {
    set({ paymentDetails: null });
  },

  resetChat: () => {
    set({
      messages: [initialWelcomeMessage],
      isLoading: false,
      isProcessing: false,
      paymentDetails: null,
      suggestedProductIds: null,
    });
    messageId = 1;
  },

  addLocalAIMessage: (content, type) => {
    const aiMessage: Message = {
      id: messageId++,
      sender: 'ai',
      contentType: type,
      content: content,
    };
    set((state) => ({
      messages: [...state.messages.filter(m => m.contentType !== 'typing'), aiMessage],
      isLoading: false,
      isProcessing: false,
    }));
  },

  sendMessage: async (text, token) => {
    if (!text || get().isLoading) return;

    const userMessage: Message = { id: messageId++, sender: 'user', contentType: 'text', content: text };
    const typingIndicator: Message = { id: messageId++, sender: 'ai', contentType: 'typing', content: null };

    set((state) => ({
      messages: [...state.messages.filter(m => m.contentType !== 'typing'), userMessage, typingIndicator],
      isLoading: true,
      isProcessing: true, 
      suggestedProductIds: null,
    }));

    try {
      const response = await fetch('/api/v1/ai-ordering/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
         get().addLocalAIMessage(`Sorry, I am having trouble connecting. (Error: ${response.status})`, 'error');
         return;
      }

      const aiData = await response.json();
      const rawResponses: any[] = aiData.responses || [];

      const paymentIntentMessage = rawResponses.find(res => res.contentType === 'payment_intent');
      let paymentDetailsFound: PaymentDetails | null = null;
      
      if (paymentIntentMessage) {
        paymentDetailsFound = paymentIntentMessage.content as PaymentDetails;
        set({ paymentDetails: paymentDetailsFound });
      }

      const aiMessages: Message[] = rawResponses
        .filter(res => res.contentType !== 'payment_intent')
        .map((res: any) => ({
          id: messageId++,
          sender: 'ai',
          contentType: res.contentType,
          content: res.content,
          options: res.options,
          products: res.products,
          reason: res.reason,
          ai_notes: res.ai_notes,
      }));

      if (paymentDetailsFound) {
        aiMessages.push({
          id: messageId++,
          sender: 'ai',
          contentType: 'text',
          content: "Great! I've prepared your order. Please complete the secure payment to finalize."
        });
      }

      const suggestions = rawResponses
        .filter((res: any) => res.contentType === 'product_carousel' && res.products)
        .flatMap((res: any) => res.products.map((p: any) => p.id));

      set((state) => ({
        messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiMessages],
        isLoading: false,
        isProcessing: false, 
	      suggestedProductIds: suggestions.length > 0 ? suggestions : null,
      }));

    } catch (error) {
      get().addLocalAIMessage('Sorry, I encountered a critical connection error. Please try again later.', 'error');
    }
  },
}));
