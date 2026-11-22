/// apps/web/hooks/useAIOrderingStore.ts

'use client';

import { create } from 'zustand';
import { produce } from 'immer';
import { useCartStore } from './useCartStore';

// --- Domain Types ---

export type PaymentGateway = {
  provider: string;
  clientSecret?: string;
  approval_url?: string;
  checkoutRequestId?: string;
};

export type PaymentOrderItem = {
  id: number | string;
  name: string;
  quantity: number;
  price: number;
};

export type PaymentDetails = {
  orderId: number;
  total: number;
  gateways: PaymentGateway[];
  // Live contract from apps/api ai_checkout_service (payment_intent content):
  client_secret?: string | null;
  order_data?: {
    order_id: number;
    total: number;
    items: PaymentOrderItem[];
  };
  gateway_provider?: string;
  action_url?: string;
};

export type FlyItem = {
  animationId: string;
  productId: number;
  image: string;
  startElementId: string;
};

export type MessageContentType = 
  | 'text' 
  | 'cart_preview' 
  | 'error' 
  | 'typing' 
  | 'confirmation_prompt' 
  | 'product_carousel' 
  | 'proactive_suggestion' 
  | 'payment_intent' 
  | 'success_text' 
  | 'ORDER_CANCELLED' 
  | 'recovery_prompt' 
  | 'reset_prompt' 
  | 'image_user_upload';

export interface Message {
  id: number;
  msgId?: string;
  sender: 'user' | 'ai';
  contentType: MessageContentType;
  flight_data?: Record<string, unknown>;
  imageUrl?: string;
  content: unknown;
  options?: string[];
  products?: Record<string, unknown>[];
  secondary_suggestions?: Record<string, unknown>[];
  reason?: string;
  ai_notes?: string;
  timestamp?: number;
  status?: 'sending' | 'sent' | 'failed';
}

export type SocketStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// --- State Interface ---

interface AIOrderingState {
  // Data
  messages: Message[];
  paymentDetails: PaymentDetails | null;
  recoveryOrderDetails: PaymentDetails | null;
  suggestedProductIds: number[] | null;
  flyQueue: FlyItem[];
  
  // UI Flags
  isLoading: boolean;
  isProcessing: boolean;
  isOverlayVisible: boolean;
  isVoiceMode: boolean;
  recoveryMode: boolean;
  recoveryReason: string;
  glowingProductId: number | null;
  
  // Networking / Socket State
  socket: WebSocket | null;
  socketStatus: SocketStatus;
  reconnectAttempts: number;
  messageQueue: Record<string, unknown>[];
  reconnectTimeoutId: NodeJS.Timeout | null;
  ackTimeouts: Record<string, NodeJS.Timeout>;
  abortController: AbortController | null;
  socketConnectionAttemptId: number;
  socketError: string | null;

  // Actions - Socket
  connectSocket: (token: string) => Promise<void>;
  disconnectSocket: () => void;
  handleSocketMessage: (payload: Record<string, unknown>) => void;
  appendSystemMessage: (message: { type: string; content: string }) => void;
  processOfflineQueue: () => void;

  // Actions - Messaging
  sendMessage: (text: string, isButtonCommand?: boolean) => void;
  sendImage: (fullDataUrl: string, base64: string, caption?: string) => void;
  addSocketAIMessage: (message: Record<string, unknown>) => void;
  _sendInternalCommand: (command: string, payload?: Record<string, unknown>, silent?: boolean) => void;
  _getSupportSessionId: () => string;
  _postSupportChat: (message: string, msgId: string | null, imageBase64?: string) => Promise<void>;
  _postCartCommand: (path: string, body?: Record<string, unknown>) => Promise<boolean>;
  _dispatchCommand: (payload: Record<string, unknown>) => Promise<void>;

  // Actions - UI & Cart
  setOverlayVisible: (isVisible: boolean) => void;
  setVoiceMode: (isActive: boolean) => void;
  addProductById: (product: { id: number; image_url?: string | null; image?: string }, startElementId: string) => void;
  removeFlyItem: (animationId: string) => void;
  removeProductById: (productId: number) => void;
  clearCart: () => void;

  // Actions - Checkout & Flow
  fetchInitialSuggestions: () => void;
  clearPayment: () => void;
  confirmCurrentOrder: () => void;
  triggerResetConfirmation: () => void;
  cancelReset: () => void;
  resetChat: () => void;
  initiateCheckoutRecovery: () => void;
  restoreCheckout: () => void;
  saveForLater: () => void;
  hardCancelOrder: (reason: string | unknown) => void;
  setRecoveryReason: (reason: string) => void;
  cancelPaymentIntent: () => Promise<void>;
}

// --- Utilities ---

let messageIdCounter = 1;
const generateMessageId = () => Date.now() + messageIdCounter++;
// Faster UUID generation for UI tasks
const generateUUID = () => crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36);

// TODO(product): the welcome message was never populated - it is an empty
// object cast to Message. Preserving that exact runtime behavior for now;
// the chat render path already tolerates it.
const initialWelcomeMessage = {} as Message;

const SILENT_COMMAND_TRIGGERS = new Set([
  "clear cart", "confirm order", "checkout", "pay now",
  "cancel order", "save for later", "retry payment"
]);

const NOISY_TEXT_FRAGMENTS = [
  "secured in manifest",
  "added to order"
];

// --- Store Implementation ---

export const useAIOrderingStore = create<AIOrderingState>()((set, get) => ({
  // --- Initial State ---
  messages: [initialWelcomeMessage],
  paymentDetails: null,
  recoveryOrderDetails: null,
  suggestedProductIds: null,
  isLoading: false,
  isProcessing: false,
  isOverlayVisible: false,
  isVoiceMode: false,
  recoveryMode: false,
  recoveryReason: 'price',
  glowingProductId: null,
  flyQueue: [],
  socket: null,
  socketStatus: 'disconnected',
  reconnectAttempts: 0,
  messageQueue: [],
  reconnectTimeoutId: null,
  ackTimeouts: {},
  abortController: null,
  socketConnectionAttemptId: 0,
  socketError: null,

  // --- Socket Logic ---
  connectSocket: async (token: string) => {
    const {
      socket,
      socketStatus,
      abortController,
      socketConnectionAttemptId,
      disconnectSocket,
    } = get();

    const hasLiveSocket =
      socket?.readyState === WebSocket.OPEN ||
      socket?.readyState === WebSocket.CONNECTING;

    if (hasLiveSocket || socketStatus === 'connecting') {
      return;
    }

    abortController?.abort();

    if (socket && socket.readyState !== WebSocket.CLOSED) {
      try {
        socket.close();
      } catch {
        // Ignore close errors on stale sockets
      }
    }

    const nextAttemptId = socketConnectionAttemptId + 1;
    const controller = new AbortController();

    set({
      abortController: controller,
      socketStatus: 'connecting',
      socketError: null,
      socketConnectionAttemptId: nextAttemptId,
    });

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL?.trim() || '/api/v1';

      const ticketResponse = await fetch(`${apiBase}/ai-ordering/ticket`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      if (!ticketResponse.ok) {
        if (get().socketConnectionAttemptId !== nextAttemptId) return;
        set({
          socketStatus: 'error',
          socketError: `Ticket request failed with status ${ticketResponse.status}`,
          abortController: null,
        });
        return;
      }

      const ticketPayload = await ticketResponse.json() as { ticket?: string };
      const ticket = ticketPayload?.ticket;

      if (!ticket) {
        if (get().socketConnectionAttemptId !== nextAttemptId) return;
        set({
          socketStatus: 'error',
          socketError: 'Ticket response is missing a valid ticket.',
          abortController: null,
        });
        return;
      }

      if (controller.signal.aborted || get().socketConnectionAttemptId !== nextAttemptId) return;

      const wsBase =
        process.env.NEXT_PUBLIC_WS_URL?.trim() ||
        process.env.NEXT_PUBLIC_SOCKET_URL?.trim();

      let socketUrl = '';
      if (wsBase) {
         socketUrl = `${wsBase.replace(/\/$/, '')}/ai-ordering/chat?ticket=${encodeURIComponent(ticket)}`;
      } else {
         const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
         socketUrl = `${protocol}//${window.location.host}/api/v1/ai-ordering/chat?ticket=${encodeURIComponent(ticket)}`;
      }

      const nextSocket = new WebSocket(socketUrl);

      nextSocket.onopen = () => {
        if (get().socketConnectionAttemptId !== nextAttemptId) {
          nextSocket.close();
          return;
        }

        set({
          socket: nextSocket,
          socketStatus: 'connected',
          socketError: null,
          abortController: null,
        });

        get()._sendInternalCommand('__INTERNAL_SYNC_CART__', {}, true);

        if (get().messages.length <= 1) {
          get()._sendInternalCommand('__INTERNAL_GET_INITIAL_SUGGESTIONS__', {}, true);
        }

        setTimeout(() => {
            get().processOfflineQueue();
        }, 500);
      };

      nextSocket.onmessage = (event: MessageEvent<string>) => {
        if (get().socket !== nextSocket) return;

        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === 'SERVER_ACK') {
            const replyTo = payload.reply_to;
            set(produce((state: AIOrderingState) => {
              // Optimizing lookup from end of array since messages are chronological
              for (let i = state.messages.length - 1; i >= 0; i--) {
                  const message = state.messages[i];
                  if (message && message.msgId === replyTo) {
                      message.status = 'sent';
                      break;
                  }
              }
              if (state.ackTimeouts[replyTo]) {
                clearTimeout(state.ackTimeouts[replyTo]);
                delete state.ackTimeouts[replyTo];
              }
            }));
            return;
          }

          get().handleSocketMessage(payload);
        } catch {
          get().appendSystemMessage({
            type: 'error',
            content: 'Received an invalid socket message.',
          });
        }
      };

      nextSocket.onerror = () => {
        if (get().socketConnectionAttemptId !== nextAttemptId) return;
        set({
          socketStatus: 'error',
          socketError: 'WebSocket connection failed.',
        });
      };

      nextSocket.onclose = () => {
        const state = get();
        if (state.socket === nextSocket) {
          set({ socket: null });
        }
        if (state.socketConnectionAttemptId !== nextAttemptId) return;
        set({
          socketStatus: 'disconnected',
          abortController: null,
        });
      };

    } catch (error) {
      if ((error as DOMException)?.name === 'AbortError') {
        if (get().socketConnectionAttemptId === nextAttemptId) {
          set({ socketStatus: 'disconnected', abortController: null });
        }
        return;
      }

      if (get().socketConnectionAttemptId !== nextAttemptId) return;

      set({
        socketStatus: 'error',
        socketError: error instanceof Error ? error.message : 'Unknown socket connection error.',
        abortController: null,
      });

      disconnectSocket();
    }
  },

  disconnectSocket: () => {
    const { socket, reconnectTimeoutId, abortController } = get();

    if (reconnectTimeoutId) clearTimeout(reconnectTimeoutId);
    if (abortController) abortController.abort();

    if (socket) {
      socket.onclose = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.close();
    }

    set({
      socket: null,
      socketStatus: 'disconnected',
      reconnectAttempts: 0,
      reconnectTimeoutId: null,
      abortController: null
    });
  },

  handleSocketMessage: (payload) => {
    // Backend ERROR frames (e.g. DELIVERY_FAILED when the broker publish
    // fails) must surface honestly instead of being rendered as an unknown
    // message type.
    if (payload.type === 'ERROR') {
      get().appendSystemMessage({
        type: 'error',
        content: typeof payload.content === 'string'
          ? payload.content
          : 'Service temporarily unavailable. Please try again.',
      });
      return;
    }
    get().addSocketAIMessage(payload);
  },

  appendSystemMessage: (message) => {
    set(produce((state: AIOrderingState) => {
      // Filter mutates array in place faster than re-assigning if done manually, 
      // but immer handles standard filter optimally enough.
      state.messages = state.messages.filter(m => m.contentType !== 'typing');
      state.isLoading = false;
      state.isProcessing = false;
      
      state.messages.push({
        id: generateMessageId(),
        sender: 'ai',
        contentType: 'error',
        content: message.content,
        timestamp: Date.now(),
      });
    }));
  },

  processOfflineQueue: () => {
    const { socket, messageQueue } = get();
    if (socket?.readyState === WebSocket.OPEN && messageQueue.length > 0) {
      // Commands were queued while the socket (response channel) was down.
      // Dispatch them over the HTTP command API now that responses can arrive.
      const queued = [...messageQueue];
      set({ messageQueue: [] });
      queued.forEach(msg => { void get()._dispatchCommand(msg); });
    }
  },

  addSocketAIMessage: (response) => {
    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'typing');
      state.isLoading = false;

      const lastMsg = state.messages[state.messages.length - 1];

      // Dedup logic
      if (lastMsg && lastMsg.contentType === response.type) {
        // Fast JSON stringify comparison is acceptable for small payloads
        const isIdenticalContent = JSON.stringify(lastMsg.content) === JSON.stringify(response.content);
        if (isIdenticalContent || response.type === 'recovery_prompt') {
          return;
        }
      }

      if (response.type !== 'typing') {
        state.isProcessing = false;
      }

      // Filter noisy text
      const isTextType = response.type === 'success_text' || response.type === 'text';
      if (isTextType && typeof response.content === 'string') {
          const lowerContent = response.content.toLowerCase();
          for (const fragment of NOISY_TEXT_FRAGMENTS) {
              if (lowerContent.includes(fragment)) return;
          }
      }

      // Cleanup prompts if receiving confirmation UI
      const isIncomingContentOrButtons =
        response.type === 'confirmation_prompt' ||
        (Array.isArray(response.products) && response.products.length > 0);

      if (isIncomingContentOrButtons) {
        state.messages = state.messages.filter(m => m.contentType !== 'confirmation_prompt');
      }

      const aiMessage: Message = {
        id: generateMessageId(),
        sender: 'ai',
        contentType: response.type as MessageContentType,
        content: response.content,
        products: response.products as Record<string, unknown>[],
        secondary_suggestions: response.secondary_suggestions as Record<string, unknown>[],
        options: response.options as string[],
        reason: response.reason as string,
        ai_notes: response.ai_notes as string,
        timestamp: Date.now(),
        flight_data: response.flight_data as Record<string, unknown>
      };

      // Flow specific states
      if (response.type === 'payment_intent') {
        state.paymentDetails = response.content as PaymentDetails;
        state.recoveryMode = false;
        return; // Don't push to chat
      }

      if (response.type === 'ORDER_CANCELLED') {
        state.paymentDetails = null;
        state.recoveryOrderDetails = null;
        state.recoveryMode = false;
        aiMessage.contentType = 'text';
        aiMessage.content = response.content;
      }

      if (response.type === 'cart_preview') {
        const isDuplicate = lastMsg?.contentType === 'cart_preview' &&
                            JSON.stringify(lastMsg.content) === JSON.stringify(response.content);

        if (isDuplicate) return;

        const contentAsRecord = response.content as Record<string, unknown>;
        
        if (Array.isArray(contentAsRecord?.items)) {
          // تحويل البيانات لتطابق هيكل useCartStore
          const syncedItems = contentAsRecord.items.map((item: any) => ({
              ...item,
              id: item.product_id || item.id,
              // Backend يرسل السعر كنص String لضمان الدقة المالية، لذا نحوله هنا إلى رقم[cite: 7]
              price: Number(item.price) 
          }));
          
          // حقن المنتجات في سلة الموقع الرئيسية المخزنة في localStorage
          useCartStore.setState({ items: syncedItems });
        }

        if (Array.isArray(contentAsRecord?.items) && contentAsRecord.items.length === 0) {
          state.messages = state.messages.filter(m => m.contentType !== 'confirmation_prompt');
        }
      }

      state.messages.push(aiMessage);
    }));
  },

  // --- Actions ---

  sendMessage: (text, isButtonCommand = false) => {
    if (!text) return;
    
    // Prevent multiple sends if loading, unless it's an explicit button override
    if (get().isLoading && !isButtonCommand) return;

    const msgId = generateUUID();
    const lowerText = text.toLowerCase();
    
    // Auto-detect silent commands
    let isSilent = isButtonCommand;
    if (!isSilent) {
        for (const trigger of SILENT_COMMAND_TRIGGERS) {
            if (lowerText.includes(trigger)) {
                isSilent = true;
                break;
            }
        }
    }

    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'typing');

      if (!isSilent) {
        state.messages.push({
          id: generateMessageId(),
          msgId: msgId,
          sender: 'user',
          contentType: 'text',
          content: text,
          timestamp: Date.now(),
          status: 'sending'
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

    // Setup Timeout for ACK
    const timeoutId = setTimeout(() => {
      set(produce((state: AIOrderingState) => {
        // Find from end
        for (let i = state.messages.length - 1; i >= 0; i--) {
            const message = state.messages[i];
            if (message && message.msgId === msgId && message.status === 'sending') {
                message.status = 'failed';
                break;
            }
        }
        state.isLoading = false;
        state.isProcessing = false;
      }));
    }, 60000);

    set(produce((state: AIOrderingState) => {
      state.ackTimeouts[msgId] = timeoutId;
    }));

    if (isSilent) {
      // Cart/checkout commands go to the HTTP ai-ordering endpoints.
      get()._sendInternalCommand(text, { id: msgId }, true);
    } else {
      void get()._postSupportChat(text, msgId);
    }
  },

  sendImage: (fullDataUrl, base64Raw, caption) => {
    const isOnline = get().socketStatus === 'connected';

    set(produce((state: AIOrderingState) => {
      state.messages.push({
        id: generateMessageId(),
        sender: 'user',
        contentType: 'image_user_upload',
        content: caption || 'Analyzing image...',
        imageUrl: fullDataUrl,
        status: 'sent'
      });
      if (isOnline) {
        state.isLoading = true;
        state.isProcessing = true;
      }
    }));

    if (isOnline) {
      setTimeout(() => {
        set(produce((state: AIOrderingState) => {
          if (state.isProcessing) {
            state.isLoading = false;
            state.isProcessing = false;
          }
        }));
      }, 60000); // 60s timeout on processing flag lock
    }

    void get()._postSupportChat(caption || '', null, base64Raw);
  },

  _getSupportSessionId: () => {
    // Session continuity for the NeuralCore memory layer. Session ids are
    // bound by the endpoint to ^[a-zA-Z0-9_-]{8,128}$.
    if (typeof window === 'undefined') return 'ssr-session';
    let sessionId = window.localStorage.getItem('airdeliver-support-session');
    if (!sessionId || !/^[a-zA-Z0-9_-]{8,128}$/.test(sessionId)) {
      sessionId = crypto.randomUUID();
      window.localStorage.setItem('airdeliver-support-session', sessionId);
    }
    return sessionId;
  },

  _postSupportChat: async (message, msgId, imageBase64) => {
    // Live assistant path: the ai_support HTTP endpoint backed by
    // NeuralCoreService. Chat text and image queries go here; cart and
    // checkout commands stay on the websocket.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch('/api/v1/ai-support/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message,
          session_id: get()._getSupportSessionId(),
          ...(imageBase64 ? { image_base64: imageBase64 } : {}),
        }),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`support chat returned ${response.status}`);
      }
      const data = await response.json() as { text?: string };

      // Delivery confirmed: settle the optimistic user message.
      if (msgId) {
        const ackTimeout = get().ackTimeouts[msgId];
        if (ackTimeout) clearTimeout(ackTimeout);
        set(produce((state: AIOrderingState) => {
          delete state.ackTimeouts[msgId];
          for (let i = state.messages.length - 1; i >= 0; i--) {
            const m = state.messages[i];
            if (m && m.msgId === msgId && m.status === 'sending') {
              m.status = 'sent';
              break;
            }
          }
        }));
      }

      get().addSocketAIMessage({ type: 'text', content: data.text ?? '' });
    } catch (error) {
      if (msgId) {
        const ackTimeout = get().ackTimeouts[msgId];
        if (ackTimeout) clearTimeout(ackTimeout);
        set(produce((state: AIOrderingState) => {
          delete state.ackTimeouts[msgId];
          for (let i = state.messages.length - 1; i >= 0; i--) {
            const m = state.messages[i];
            if (m && m.msgId === msgId && m.status === 'sending') {
              m.status = 'failed';
              break;
            }
          }
        }));
      }
      get().appendSystemMessage({
        type: 'error',
        content: "I couldn't reach the assistant service right now. Please try again in a moment.",
      });
    } finally {
      clearTimeout(timeoutId);
    }
  },

  _sendInternalCommand: (command, payload = {}, silent = false) => {
    const { socket, socketStatus } = get();

    const fullPayload = {
      type: 'CHAT_MESSAGE',
      message: command,
      timestamp: Date.now(),
      ...payload
    };

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      set(produce((state: AIOrderingState) => {
        state.messageQueue.push(fullPayload);
        if (!silent) {
           state.isLoading = true;
           state.isProcessing = true;
        }
      }));

      // Attempt opportunistic reconnect if not already trying
      if (socketStatus !== 'connecting') {
          const token = typeof document !== 'undefined' 
            ? (document.cookie.split('; ').find(row => row.startsWith('next-auth.session-token='))?.split('=')[1] || '') 
            : '';
          if (token) get().connectSocket(token);
      }

      // Safety unlock if socket doesn't recover
      setTimeout(() => {
          const currentState = get();
          if (currentState.isLoading && (!currentState.socket || currentState.socket.readyState !== WebSocket.OPEN)) {
             set({ isLoading: false, isProcessing: false });
          }
      }, 3000);

      return;
    }

    if (!silent) {
      set({ isLoading: true, isProcessing: true, suggestedProductIds: null });
    }

    void get()._dispatchCommand(fullPayload);
  },

  // Single command path: every cart/checkout command maps to the HTTP
  // ai-ordering endpoints (the RabbitMQ command queues have no consumer in
  // this stack). AI responses still arrive over the websocket via the Redis
  // relay, so callers gate on socket health before dispatching.
  _dispatchCommand: async (payload) => {
    const rawMessage = payload.message;
    const message = typeof rawMessage === 'string' ? rawMessage : '';
    const lower = message.toLowerCase();

    let path: string | null = null;
    let body: Record<string, unknown> = {};

    const numericId = (prefix: string): number | null => {
      const value = Number(message.slice(prefix.length));
      return Number.isFinite(value) && value > 0 ? value : null;
    };

    if (message.startsWith('__INTERNAL_ADD_BY_ID__:')) {
      const productId = numericId('__INTERNAL_ADD_BY_ID__:');
      if (productId === null) return;
      path = '/cart/add';
      body = { product_id: productId };
    } else if (message.startsWith('__INTERNAL_REMOVE_BY_ID__:')) {
      const productId = numericId('__INTERNAL_REMOVE_BY_ID__:');
      if (productId === null) return;
      path = '/cart/remove';
      body = { product_id: productId };
    } else if (message === '__INTERNAL_SYNC_CART__') {
      path = '/cart/sync';
    } else if (message === '__INTERNAL_CLEAR_CART__' || lower.includes('clear cart')) {
      path = '/cart/clear';
    } else if (message === '__INTERNAL_SAVE_FOR_LATER__' || lower.includes('save for later')) {
      path = '/cart/save';
    } else if (message === '__INTERNAL_CONFIRM_ORDER__' || lower.includes('confirm order') || lower.includes('checkout') || lower.includes('pay now') || lower.includes('retry payment')) {
      path = '/checkout/confirm';
    } else if (message === '__CANCEL__' || payload.type === 'CANCEL_INTENT' || lower.includes('cancel order')) {
      path = '/checkout/cancel';
      if (rawMessage && typeof rawMessage === 'object') {
        const orderId = (rawMessage as Record<string, unknown>).orderId;
        if (typeof orderId === 'number') body = { order_id: orderId };
      }
    } else if (message === '__INTERNAL_RESET_SESSION__') {
      path = '/session/reset';
    } else if (message === '__INTERNAL_GET_INITIAL_SUGGESTIONS__') {
      path = '/session/suggestions';
    } else if (message === '__INTERNAL_INITIATE_RECOVERY__') {
      // No handler has ever existed for this command (checked both the NLU
      // service and the worker). Dropped deliberately.
      return;
    } else {
      // Unknown internal command: drop rather than fake an ACK.
      return;
    }

    const ok = await get()._postCartCommand(path, body);
    // Cart sync and opening suggestions are best-effort hydration calls:
    // their failure was silent on the worker path too, so keep it quiet.
    const quiet = path === '/cart/sync' || path === '/session/suggestions';
    if (!ok && !quiet) {
      set({ isLoading: false, isProcessing: false });
      get().appendSystemMessage({
        type: 'error',
        content: "I couldn't reach the ordering service. Please try again in a moment.",
      });
    }
  },

  _postCartCommand: async (path, body = {}) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL?.trim() || '/api/v1';
    const token = typeof document !== 'undefined'
      ? (document.cookie.split('; ').find(row => row.startsWith('next-auth.session-token='))?.split('=')[1] || '')
      : '';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(`${apiBase}/ai-ordering${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  setOverlayVisible: (isVisible) => set({ isOverlayVisible: isVisible }),
  setVoiceMode: (isActive) => set({ isVoiceMode: isActive }),

  addProductById: (product, startElementId) => {
    const { recoveryMode, messages } = get();
    
    // Auto-restore cart if adding items while in recovery flow
    if (recoveryMode) {
      // Find last cart preview
      let previousItems: Record<string, unknown>[] = [];
      for (let i = messages.length - 1; i >= 0; i--) {
          const message = messages[i];
          if (message && message.contentType === 'cart_preview') {
              const content = message.content as Record<string, unknown>;
              if (Array.isArray(content?.items)) {
                  previousItems = content.items as Record<string, unknown>[];
              }
              break;
          }
      }

      set({ recoveryMode: false, paymentDetails: null, recoveryOrderDetails: null });
      previousItems.forEach((item) => {
        if (item.product_id) {
          get()._sendInternalCommand(`__INTERNAL_ADD_BY_ID__:${item.product_id}`, {}, true);
        }
      });
    } else {
      set({ recoveryMode: false, paymentDetails: null, recoveryOrderDetails: null });
    }

    const newFlyItem: FlyItem = {
      animationId: `${product.id}-${generateUUID()}`,
      productId: product.id,
      image: product.image_url || product.image || '',
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
  
  confirmCurrentOrder: () => {
    set({ isProcessing: true, isLoading: true });
    get()._sendInternalCommand('__INTERNAL_CONFIRM_ORDER__', {}, true);
  },

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
      messageQueue: [],
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

    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');
      state.isOverlayVisible = true;
      state.recoveryMode = false;
      state.paymentDetails = recoveryOrderDetails;
      state.recoveryOrderDetails = null;
    }));
  },

  setRecoveryReason: (reason) => set({ recoveryReason: reason }),

  saveForLater: () => {
    get()._sendInternalCommand('__INTERNAL_SAVE_FOR_LATER__');
    get().clearCart();

    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');
      state.recoveryMode = false;
      state.recoveryOrderDetails = null;
      state.paymentDetails = null;
    }));
  },

  hardCancelOrder: (reason) => {
    const { recoveryOrderDetails } = get();
    const sanitizedReason = (typeof reason === 'string' && reason) ? reason : 'changed_mind';

    get()._sendInternalCommand('__CANCEL__', {
      type: 'CANCEL_INTENT',
      message: { orderId: recoveryOrderDetails?.orderId, reason: sanitizedReason }
    }, true);

    set(produce((state: AIOrderingState) => {
      state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');
      state.recoveryMode = false;
      state.recoveryOrderDetails = null;
      state.paymentDetails = null;
      state.isProcessing = false;
    }));
  },

  cancelPaymentIntent: async () => {
    get().hardCancelOrder(get().recoveryReason);
  },
}));
