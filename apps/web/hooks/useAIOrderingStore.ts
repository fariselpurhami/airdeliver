// file: apps/web/hooks/useAIOrderingStore.ts
'use client';

import { create } from 'zustand';
import { api } from '@/lib/api';

type PaymentDetails = {
  clientSecret: string;
  orderId: number;
  total: number;
};

export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'payment_intent' | 'success_text';
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
  glowingProductId: number | null;
  flyToCartItem: string | null; 
  setOverlayVisible: (isVisible: boolean) => void;
  setSuggestedProductIds: (ids: number[] | null) => void;
  sendMessage: (text: string) => void;
  addProductById: (product: any) => void;
  removeProductById: (productId: number) => void;
  addLocalAIMessage: (content: string, type: 'error' | 'text' | 'success_text') => void;
  fetchInitialSuggestions: () => void;
  clearPayment: () => void;
  resetChat: () => void;
}

let messageId = 1;

const initialWelcomeMessage: Message = {
  id: 0,
  sender: 'ai',
  contentType: 'text',
  content: 'Autonomous Order with air activated. Your order is ready for deployment.',
};

const smartReplies = [
    (name: string) => `Nice pick! ${name} is now in your cart.`,
    (name: string) => `Got it — added ${name}.`,
    (name: string) => `🔥 ${name} added! You’ve got great taste.`,
    (name: string) => `Done! ${name} is ready in your cart.`,
];

const randomSmartReply = (productName: string) => {
    const reply = smartReplies[Math.floor(Math.random() * smartReplies.length)];
    return reply(productName);
};

export const useAIOrderingStore = create<AIOrderingState>((set, get) => ({
  messages: [initialWelcomeMessage],
  isLoading: false,
  isProcessing: false,
  isOverlayVisible: false,
  suggestedProductIds: null,
  paymentDetails: null,
  glowingProductId: null,
  flyToCartItem: null,

  setOverlayVisible: (isVisible) => {
    set({ isOverlayVisible: isVisible });
    
    if (isVisible && get().messages.length === 1) {
      get().fetchInitialSuggestions();
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
      glowingProductId: null,
      flyToCartItem: null,
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

  fetchInitialSuggestions: async () => {
    if (get().isLoading) return;

    const typingIndicator: Message = { id: messageId++, sender: 'ai', contentType: 'typing', content: null };
    set((state) => ({
      messages: [...state.messages, typingIndicator],
      isLoading: true,
    }));

    try {
      const response = await api.post('/ai-ordering/chat', {
          message: "__INTERNAL_GET_INITIAL_SUGGESTIONS__"
      });

      const aiData = response.data;
      const aiMessages: Message[] = (aiData.responses || [])
          .map((res: any) => ({
              id: messageId++,
              sender: 'ai',
              ...res
           }));
      
      set((state) => ({
          messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiMessages],
          isLoading: false,
      }));

    } catch (error) {
       get().addLocalAIMessage('Could not load suggestions right now. What are you looking for?', 'error');
    }
  },

  addProductById: async (product) => {
    if (!product || get().isProcessing) return;

    set({ 
      isProcessing: true,
      glowingProductId: product.id,
      flyToCartItem: product.image || '/images/default.jpeg',
    });
    
    setTimeout(() => set({ glowingProductId: null }), 1500); 

    get().addLocalAIMessage(randomSmartReply(product.name), 'success_text');
    
    try {
      const cartResponse = await api.post('/ai-ordering/chat', {
          message: `__INTERNAL_ADD_BY_ID__:${product.id}`
      });
      
      const cartData = cartResponse.data;
      const cartMessages: Message[] = (cartData.responses || [])
          .map((res: any) => ({
              id: messageId++,
              sender: 'ai',
              ...res
           }));
      
      set((state) => ({
          messages: [...state.messages, ...cartMessages],
      }));

    } catch (error) {
       get().addLocalAIMessage(`I had a slight issue adding ${product.name}. Let's try that again.`, 'error');
       set({ isProcessing: false });
       return;
    }
    
    setTimeout(async () => {
        set({ isLoading: true }); 
        try {
            const suggestionResponse = await api.post('/ai-ordering/chat', {
                message: `__INTERNAL_GET_SUGGESTIONS__:${product.id}`
            });
            
            const suggestionData = suggestionResponse.data;
            const aiMessages: Message[] = (suggestionData.responses || [])
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
            
            set((state) => ({
                messages: [...state.messages.filter(m => m.contentType !== 'typing'), ...aiMessages],
                isLoading: false,
                isProcessing: false,
            }));

        } catch (error) {
            set({ isLoading: false, isProcessing: false });
        }
    }, 800); 
  },

  removeProductById: async (productId) => {
    if (get().isLoading || get().isProcessing) return;

    const localMessageContent = 'Updating cart...';

    set({ isLoading: true, isProcessing: true });
    get().addLocalAIMessage(localMessageContent, 'success_text');

    try {
      const response = await api.post('/ai-ordering/chat', {
        message: `__INTERNAL_REMOVE_BY_ID__:${productId}`
      });

      const aiData = response.data;
      const aiMessages: Message[] = (aiData.responses || [])
          .map((res: any) => ({
              id: messageId++,
              sender: 'ai',
              ...res
           }));

      set((state) => ({
          messages: [...state.messages.filter(m => m.content !== localMessageContent), ...aiMessages],
          isLoading: false,
          isProcessing: false,
      }));

    } catch (error) {
       get().addLocalAIMessage('There was an error removing the item. Please try again.', 'error');
       set({ isLoading: false, isProcessing: false });
    }
  },

  sendMessage: async (text) => {
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
      const response = await api.post('/ai-ordering/chat', {
        message: text 
      });

      const aiData = response.data;
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
