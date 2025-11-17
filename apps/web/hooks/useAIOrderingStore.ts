// apps/web/hooks/useAIOrderingStore.ts

'use client';

import { create } from 'zustand';
import { api } from '@/lib/api';
import { produce } from 'immer';

type PaymentGateway = {
  provider: string;
  clientSecret?: string;
  approval_url?: string;
  checkoutRequestId?: string;
};

type PaymentDetails = {
  orderId: number;
  total: number;
  gateways: PaymentGateway[];
};

export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'payment_intent' | 'success_text' | 'ORDER_CANCELLED';
  content: any;
  options?: string[];
  products?: any[];
  secondary_suggestions?: any[];
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
  flyToCartItem: { id: number; image: string; startElementId: string } | null;
  socket: WebSocket | null;
  connectSocket: (token: string) => void;
  disconnectSocket: () => void;
  setOverlayVisible: (isVisible: boolean) => void;
  setSuggestedProductIds: (ids: number[] | null) => void;
  sendMessage: (text: string) => void;
  addProductById: (product: any, startElementId: string) => void;
  removeProductById: (productId: number) => void;
  addSocketAIMessage: (message: any) => void;
  fetchInitialSuggestions: () => void;
  clearPayment: () => void;
  clearCart: () => void;
  resetChat: () => void;
  cancelPaymentIntent: () => Promise<void>;
  _sendInternalCommand: (command: string, payload?: any) => void;
}

let messageId = 1;

const initialWelcomeMessage: Message = {
  id: 0,
  sender: 'ai',
  contentType: 'text',
  content: 'Autonomous Order with air activated. Your order is ready for deployment.',
};

const getWebSocketURL = () => {

  const apiURL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
  const url = new URL(apiURL, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');

  url.protocol = url.protocol.replace('http', 'ws');

  let pathname = url.pathname;
  if (pathname.endsWith('/')) {
    pathname = pathname.slice(0, -1);
  }

  url.pathname = `${pathname}/ai-ordering/chat`;

  return url.href;
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
  socket: null,

  connectSocket: (token) => {
    if (get().socket) return;

    const wsUrl = `${getWebSocketURL()}?token=${token}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      set({ socket });
      get()._sendInternalCommand("__INTERNAL_RESET_SESSION__");
      get().fetchInitialSuggestions();
    };

    socket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      get().addSocketAIMessage(response);
    };

    socket.onclose = () => {
      set({ socket: null, isLoading: false, isProcessing: false });
    };

    socket.onerror = (error) => {
      console.error("WebSocket Error:", error);
      get().addSocketAIMessage({ contentType: 'error', content: 'Connection error. Please reconnect.' });
    };
  },

  disconnectSocket: () => {
    get().socket?.close();
    set({ socket: null });
  },

  addSocketAIMessage: (response) => {
    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'typing');
      state.isLoading = false;

      const aiMessage: Message = {
        id: messageId++,
        sender: 'ai',
        contentType: response.type,
        content: response.content,
        products: response.products,
        secondary_suggestions: response.secondary_suggestions,
        options: response.options,
        reason: response.reason,
        ai_notes: response.ai_notes,
      };

      const typesThatEndProcessing = [
          'payment_intent',
          'ORDER_CANCELLED',
          'error',
          'success_text',
          'confirmation_prompt',
          'proactive_suggestion',
      ];

      if (typesThatEndProcessing.includes(response.type)) {
          state.isProcessing = false;
      }

      if (response.type === 'payment_intent') {
        state.paymentDetails = response.content as PaymentDetails;
        aiMessage.contentType = 'text';
        aiMessage.content = "Great! I've prepared your order. Please complete the secure payment to finalize.";
      }

      if (response.type === 'ORDER_CANCELLED') {
        state.paymentDetails = null;
        aiMessage.contentType = 'text';
        aiMessage.content = response.content;
      }
      
      if (response.type === 'cart_preview' && response.content?.items?.length === 0) {
          state.messages = state.messages.filter(m => m.contentType !== 'confirmation_prompt');
      }

      state.messages.push(aiMessage);
    }));
  },

  setOverlayVisible: (isVisible) => {
    set({ isOverlayVisible: isVisible });
  },

  setSuggestedProductIds: (ids) => set({ suggestedProductIds: ids }),

  clearPayment: () => {
    set({ paymentDetails: null });
  },
  
  clearCart: () => {
    get()._sendInternalCommand("__INTERNAL_CLEAR_CART__");
  },

  resetChat: () => {
    get().clearCart();
    set({
      messages: [initialWelcomeMessage],
      isLoading: false,
      isProcessing: false,
      paymentDetails: null,
    });
    messageId = 1;
    get().fetchInitialSuggestions();
  },

  _sendInternalCommand: (command: string, payload: any = {}) => {
    const { socket } = get();
    if (!socket) return;

    set({ isLoading: true, isProcessing: true, suggestedProductIds: null });

    socket.send(JSON.stringify({
      type: "CHAT_MESSAGE",
      message: command,
      ...payload
    }));
  },

  fetchInitialSuggestions: () => {
    get()._sendInternalCommand("__INTERNAL_GET_INITIAL_SUGGESTIONS__");
  },

  addProductById: async (product, startElementId) => {
    set({
      flyToCartItem: {
        id: product.id,
        image: product.image_url,
        startElementId: startElementId,
      },
    });
    get()._sendInternalCommand(`__INTERNAL_ADD_BY_ID__:${product.id}`);
    
    setTimeout(() => {
      set({ flyToCartItem: null });
    }, 1000);
  },

  cancelPaymentIntent: async () => {
    const { paymentDetails, isProcessing, socket } = get();
    if (!paymentDetails || isProcessing || !socket) return;

    set({ isProcessing: true });

    socket.send(JSON.stringify({
      type: "CANCEL_INTENT",
      message: { orderId: paymentDetails.orderId }
    }));
  },

  removeProductById: async (productId) => {
    get()._sendInternalCommand(`__INTERNAL_REMOVE_BY_ID__:${productId}`);
  },

  sendMessage: (text) => {
    if (!text || get().isLoading || !get().socket) return;

    const userMessage: Message = { id: messageId++, sender: 'user', contentType: 'text', content: text };
    const typingIndicator: Message = { id: messageId++, sender: 'ai', contentType: 'typing', content: null };

    set((state) => ({
      messages: [...state.messages.filter(m => m.contentType !== 'typing'), userMessage, typingIndicator],
      isLoading: true,
      isProcessing: true,
      suggestedProductIds: null,
    }));

    get().socket?.send(JSON.stringify({
      type: "CHAT_MESSAGE",
      message: text
    }));
  },
}));
