//** apps/web/hooks/useAIOrderingStore.ts **//

'use client';

import { create } from 'zustand';
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

type FlyItem = {
  animationId: string;
  productId: number;
  image: string;
  startElementId: string;
};

export interface Message {
  id: number;
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'payment_intent' | 'success_text' | 'ORDER_CANCELLED' | 'recovery_prompt' | 'reset_prompt';
  content: any;
  options?: string[];
  products?: any[];
  secondary_suggestions?: any[];
  reason?: string;
  ai_notes?: string;
  timestamp?: number;
}

interface AIOrderingState {
  messages: Message[];
  paymentDetails: PaymentDetails | null;
  recoveryOrderDetails: PaymentDetails | null;
  suggestedProductIds: number[] | null;

  isLoading: boolean;
  isProcessing: boolean;
  isOverlayVisible: boolean;
  recoveryMode: boolean;
  recoveryReason: string;
  glowingProductId: number | null;
  flyQueue: FlyItem[];

  socket: WebSocket | null;
  socketStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  reconnectAttempts: number;

  connectSocket: (token: string) => Promise<void>;
  disconnectSocket: () => void;
  sendMessage: (text: string, isButtonCommand?: boolean) => void;

  setOverlayVisible: (isVisible: boolean) => void;
  addProductById: (product: any, startElementId: string) => void;
  removeFlyItem: (animationId: string) => void;
  removeProductById: (productId: number) => void;

  addSocketAIMessage: (message: any) => void;
  fetchInitialSuggestions: () => void;
  clearPayment: () => void;
  clearCart: () => void;
  confirmCurrentOrder: () => void;
  triggerResetConfirmation: () => void;
  cancelReset: () => void;
  resetChat: () => void;
  initiateCheckoutRecovery: () => void;
  restoreCheckout: () => void;
  saveForLater: () => void;
  hardCancelOrder: (reason: any) => void;
  setRecoveryReason: (reason: string) => void;
  cancelPaymentIntent: () => Promise<void>;

  _sendInternalCommand: (command: string, payload?: any, silent?: boolean) => void;
}

let messageIdCounter = 1;
const generateMessageId = () => Date.now() + messageIdCounter++;

const initialWelcomeMessage: Message = {
  id: 0,
  sender: 'ai',
  contentType: 'text',
  content: 'Hey 👋, order with air: from cart to door, fast and easy.',
  timestamp: Date.now(),
};

const getWebSocketURL = () => {
  if (typeof window === 'undefined') return '';
  const apiURL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
  const url = new URL(apiURL, window.location.origin);
  url.protocol = url.protocol.replace('http', 'ws');

  let pathname = url.pathname;
  if (pathname.endsWith('/')) pathname = pathname.slice(0, -1);
  url.pathname = `${pathname}/ai-ordering/chat`;

  return url.href;
};

export const useAIOrderingStore = create<AIOrderingState>()(
  (set, get) => ({
    messages: [initialWelcomeMessage],
    paymentDetails: null,
    recoveryOrderDetails: null,
    suggestedProductIds: null,
    isLoading: false,
    isProcessing: false,
    isOverlayVisible: false,
    recoveryMode: false,
    recoveryReason: 'price',
    glowingProductId: null,
    flyQueue: [],
    socket: null,
    socketStatus: 'disconnected',
    reconnectAttempts: 0,

    connectSocket: async (token) => {
      const { socket, socketStatus } = get();
      if (socket?.readyState === WebSocket.OPEN || socketStatus === 'connecting') return;

      set({ socketStatus: 'connecting' });

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
        const ticketRes = await fetch(`${apiBase}/ai-ordering/ticket`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!ticketRes.ok) {
            set({ socketStatus: 'error' });
            return;
        }

        const { ticket } = await ticketRes.json();
        const wsUrl = `${getWebSocketURL()}?ticket=${ticket}`;
        const newSocket = new WebSocket(wsUrl);

        newSocket.onopen = () => {
            set({ socket: newSocket, socketStatus: 'connected', reconnectAttempts: 0 });

            const hasHistory = get().messages.length > 1;
            if (!hasHistory) {
               get()._sendInternalCommand('__INTERNAL_RESET_SESSION__', {}, true);
               get().fetchInitialSuggestions();
            }
        };

        newSocket.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);
                get().addSocketAIMessage(response);
            } catch (e) {
                console.error(e);
            }
        };

        newSocket.onclose = (event) => {
            set({ socket: null, socketStatus: 'disconnected', isLoading: false, isProcessing: false });

            if (!event.wasClean) {
                const { reconnectAttempts } = get();
                const maxAttempts = 5;

                if (reconnectAttempts < maxAttempts) {
                    const timeout = Math.min(1000 * (2 ** reconnectAttempts), 10000);
                    set({ reconnectAttempts: reconnectAttempts + 1 });

                    setTimeout(() => {
                        if (get().isOverlayVisible) {
                            get().connectSocket(token);
                        }
                    }, timeout);
                } else {
                    set({ socketStatus: 'error' });
                    get().addSocketAIMessage({
                        type: 'error',
                        content: 'Connection lost. Please refresh the page to reconnect.'
                    });
                }
            }
        };

        newSocket.onerror = () => {
            set({ socketStatus: 'error' });
        };

      } catch (e) {
          set({ socketStatus: 'error' });
      }
    },

    disconnectSocket: () => {
      const { socket } = get();
      if (socket) {
          socket.onclose = null;
          socket.close();
      }
      set({ socket: null, socketStatus: 'disconnected', reconnectAttempts: 0 });
    },

    addSocketAIMessage: (response) => {
      set(produce((state: AIOrderingState) => {
        state.messages = state.messages.filter(m => m.contentType !== 'typing');
        state.isLoading = false;

        const aiMessage: Message = {
          id: generateMessageId(),
          sender: 'ai',
          contentType: response.type,
          content: response.content,
          products: response.products,
          secondary_suggestions: response.secondary_suggestions,
          options: response.options,
          reason: response.reason,
          ai_notes: response.ai_notes,
          timestamp: Date.now(),
        };

        const typesThatEndProcessing = [
          'payment_intent', 'ORDER_CANCELLED', 'error',
          'success_text', 'confirmation_prompt', 'proactive_suggestion', 'recovery_prompt', 'product_carousel'
        ];

        if (typesThatEndProcessing.includes(response.type)) {
          state.isProcessing = false;
        }

        if (response.type === 'payment_intent') {
          state.paymentDetails = response.content as PaymentDetails;
          state.recoveryMode = false;
          aiMessage.contentType = 'text';
          aiMessage.content = "Great! I've prepared your order. Please complete the secure payment to finalize.";
        }

        if (response.type === 'ORDER_CANCELLED') {
          state.paymentDetails = null;
          state.recoveryOrderDetails = null;
          state.recoveryMode = false;
          aiMessage.contentType = 'text';
          aiMessage.content = response.content;
        }

        if (response.type === 'cart_preview') {
            const lastMsg = state.messages[state.messages.length - 1];
            const isDuplicate = lastMsg &&
                                lastMsg.contentType === 'cart_preview' &&
                                JSON.stringify(lastMsg.content) === JSON.stringify(response.content);

            if (isDuplicate) return;

            if (response.content?.items?.length === 0) {
              state.messages = state.messages.filter(m => m.contentType !== 'confirmation_prompt');
            }
        }

        state.messages.push(aiMessage);
      }));
    },

    sendMessage: (text, isButtonCommand = false) => {
      if (!text) return;
      if (get().isLoading && !isButtonCommand) return;

      set(produce((state: AIOrderingState) => {
        state.messages = state.messages.filter(m => m.contentType !== 'typing');

        if (!isButtonCommand) {
          state.messages.push({
              id: generateMessageId(),
              sender: 'user',
              contentType: 'text',
              content: text,
              timestamp: Date.now()
          });
        }

        state.messages.push({
            id: generateMessageId(),
            sender: 'ai',
            contentType: 'typing',
            content: null,
            timestamp: Date.now()
        });

        state.isLoading = true;
        state.isProcessing = true;
        state.suggestedProductIds = null;
      }));

      get()._sendInternalCommand(text, {}, true);
    },

    _sendInternalCommand: (command, payload: any = {}, silent: boolean = false) => {
        const { socket } = get();

        if (!socket || socket.readyState !== WebSocket.OPEN) return;

        if (!silent) {
            set({ isLoading: true, isProcessing: true, suggestedProductIds: null });
        }

        socket.send(JSON.stringify({
            type: 'CHAT_MESSAGE',
            message: command,
            ...payload
        }));
    },

    setOverlayVisible: (isVisible) => set({ isOverlayVisible: isVisible }),

    setSuggestedProductIds: (ids) => set({ suggestedProductIds: ids }),

    addProductById: (product, startElementId) => {
        const { recoveryMode, messages } = get();

        if (recoveryMode) {
            const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
            const previousItems = lastCartMessage?.content?.items || [];

            set({ recoveryMode: false, paymentDetails: null, recoveryOrderDetails: null });

            previousItems.forEach((item: any) => {
                 get()._sendInternalCommand(`__INTERNAL_ADD_BY_ID__:${item.product_id}`, {}, true);
            });
        } else {
            set({ recoveryMode: false, paymentDetails: null, recoveryOrderDetails: null });
        }

        const newFlyItem: FlyItem = {
            animationId: `${product.id}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            productId: product.id,
            image: product.image_url || product.image,
            startElementId: startElementId,
        };

        set(produce((state: AIOrderingState) => {
            state.flyQueue.push(newFlyItem);
        }));

        get()._sendInternalCommand(`__INTERNAL_ADD_BY_ID__:${product.id}`);
    },

    removeFlyItem: (animationId) => {
        set(produce((state: AIOrderingState) => {
            const index = state.flyQueue.findIndex(i => i.animationId === animationId);
            if (index !== -1) state.flyQueue.splice(index, 1);
        }));
    },

    removeProductById: (productId) => {
        get()._sendInternalCommand(`__INTERNAL_REMOVE_BY_ID__:${productId}`);
    },

    clearPayment: () => set({ paymentDetails: null }),

    clearCart: () => get()._sendInternalCommand('__INTERNAL_CLEAR_CART__'),

    confirmCurrentOrder: () => get().sendMessage('Confirm Order', true),

    triggerResetConfirmation: () => {
        set(produce((state: AIOrderingState) => {
            if (state.messages[state.messages.length - 1]?.contentType === 'reset_prompt') return;
            state.messages = state.messages.filter(m => m.contentType !== 'typing');
            state.messages.push({
                id: generateMessageId(),
                sender: 'ai',
                contentType: 'reset_prompt',
                content: "Are you sure you want to start a new session? This will clear your current cart and chat history."
            });
            state.isProcessing = true;
        }));
    },

    cancelReset: () => {
        set(produce((state: AIOrderingState) => {
            state.messages = state.messages.filter(m => m.contentType !== 'reset_prompt');
            state.isProcessing = false;
        }));
    },

    resetChat: () => {
        get().clearCart();
        set({
            messages: [initialWelcomeMessage],
            isLoading: false,
            isProcessing: false,
            paymentDetails: null,
            recoveryMode: false,
            recoveryOrderDetails: null,
            flyQueue: [],
        });
        messageIdCounter = 1;

        get()._sendInternalCommand('__INTERNAL_RESET_SESSION__', {}, true);
        get().fetchInitialSuggestions();
    },

    fetchInitialSuggestions: () => {
        get()._sendInternalCommand('__INTERNAL_GET_INITIAL_SUGGESTIONS__');
    },

    initiateCheckoutRecovery: () => {
        const { paymentDetails, isProcessing } = get();
        if (!paymentDetails || isProcessing) return;

        set({
            isOverlayVisible: true,
            paymentDetails: null,
            recoveryOrderDetails: paymentDetails,
            recoveryMode: true
        });

        get().addSocketAIMessage({
            type: 'recovery_prompt',
            content: "Wait! Your order isn't confirmed yet. Do you want to:",
            options: ["Restore Checkout", "Save for Later", "Cancel Order"]
        });

        get()._sendInternalCommand('__INTERNAL_INITIATE_RECOVERY__', { orderId: paymentDetails.orderId }, true);
    },

    restoreCheckout: () => {
        const { recoveryOrderDetails } = get();
        if (!recoveryOrderDetails) return;

        set({
            isOverlayVisible: true,
            recoveryMode: false,
            paymentDetails: recoveryOrderDetails,
            recoveryOrderDetails: null,
        });

        get().addSocketAIMessage({
            type: 'success_text',
            content: "Done! Checkout restored. Let's finish your order."
        });
    },

    setRecoveryReason: (reason) => set({ recoveryReason: reason }),

    saveForLater: () => {
        get()._sendInternalCommand('__INTERNAL_SAVE_FOR_LATER__');
        get().clearCart();
        set({ recoveryMode: false, recoveryOrderDetails: null, paymentDetails: null });
    },

    hardCancelOrder: (reason) => {
        const { recoveryOrderDetails, socket } = get();
        const sanitizedReason = (typeof reason === 'string' && reason) ? reason : 'changed_mind';

        if (!recoveryOrderDetails || !socket || socket.readyState !== WebSocket.OPEN) {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                get().addSocketAIMessage({ type: 'error', content: 'Connection lost. Please refresh or try again later.' });
            }
            return;
        }

        set({ isProcessing: true });

        socket.send(JSON.stringify({
            type: 'CANCEL_INTENT',
            message: {
                orderId: recoveryOrderDetails.orderId,
                reason: sanitizedReason,
            }
        }));

        set({ recoveryMode: false, recoveryOrderDetails: null, paymentDetails: null });
    },

    cancelPaymentIntent: async () => {
        get().hardCancelOrder(get().recoveryReason);
    },
  })
);
