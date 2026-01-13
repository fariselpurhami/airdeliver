
//** apps/web/hooks/useAIOrderingStore.ts **//

'use client';

import { create } from 'zustand';
import { produce } from 'immer';

// --- TYPES ---
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
  msgId?: string; // Client-side unique ID for tracking ACKs
  sender: 'user' | 'ai';
  contentType: 'text' | 'cart_preview' | 'error' | 'typing' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'payment_intent' | 'success_text' | 'ORDER_CANCELLED' | 'recovery_prompt' | 'reset_prompt' | 'image_user_upload';
  flight_data?: any;
  imageUrl?: string;
  content: any;
  options?: string[];
  products?: any[];
  secondary_suggestions?: any[];
  reason?: string;
  ai_notes?: string;
  timestamp?: number;
  status?: 'sending' | 'sent' | 'failed'; // 💎 UI Feedback
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
  
  // 💎 Architecture Upgrades
  messageQueue: any[]; // Offline Queue
  reconnectTimeoutId: NodeJS.Timeout | null; // For clearing on disconnect
  ackTimeouts: Record<string, NodeJS.Timeout>; // Track pending ACKs
  abortController: AbortController | null; // For cancelling stale ticket requests

  connectSocket: (token: string) => Promise<void>;
  disconnectSocket: () => void;
  sendMessage: (text: string, isButtonCommand?: boolean) => void;
  sendImage: (fullDataUrl: string, base64: string, caption?: string) => void;

  setOverlayVisible: (isVisible: boolean) => void;
  addProductById: (product: any, startElementId: string) => void;
  removeFlyItem: (animationId: string) => void;
  removeProductById: (productId: number) => void;

  addSocketAIMessage: (message: any) => void;
  processOfflineQueue: () => void;
  
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
const generateUUID = () => Math.random().toString(36).substring(2) + Date.now().toString(36);

const initialWelcomeMessage: Message = {
  id: 0,
  sender: 'ai',
  contentType: 'text',
  content: 'Welcome! Ask what you need. order with air: From your intent to reality. Fast and Effortless.',
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
    
    // 💎 Initial State for New Features
    messageQueue: [],
    reconnectTimeoutId: null,
    ackTimeouts: {},
    abortController: null,

    connectSocket: async (token) => {
      const { socket, socketStatus, abortController } = get();
      
      // 💎 Fix 1: Ticket Race Condition
      if (abortController) {
          abortController.abort();
      }
      const newController = new AbortController();
      set({ abortController: newController });

      if (socket?.readyState === WebSocket.OPEN || socketStatus === 'connecting') return;

      set({ socketStatus: 'connecting' });

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
        const ticketRes = await fetch(`${apiBase}/ai-ordering/ticket`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            signal: newController.signal // Bind signal
        });

        if (!ticketRes.ok) {
            set({ socketStatus: 'error', abortController: null });
            return;
        }

        const { ticket } = await ticketRes.json();
        const wsUrl = `${getWebSocketURL()}?ticket=${ticket}`;
        const newSocket = new WebSocket(wsUrl);

        newSocket.onopen = () => {
            set({ socket: newSocket, socketStatus: 'connected', reconnectAttempts: 0 });

            // 💎 Sync Session & Process Offline Queue
            const hasHistory = get().messages.length > 1;
            if (!hasHistory) {
               get()._sendInternalCommand('__INTERNAL_RESET_SESSION__', {}, true);
               get()._sendInternalCommand('__INTERNAL_GET_INITIAL_SUGGESTIONS__', {}, true);
            }
            
            // 💎 Fix 3: Flush Queue
            get().processOfflineQueue();
        };

        newSocket.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);
                
                // 💎 Fix 4: Handle Server ACKs
                if (response.type === 'SERVER_ACK') {
                    const { reply_to } = response;
                    set(produce((state: AIOrderingState) => {
                        const msg = state.messages.find(m => m.msgId === reply_to);
                        if (msg) msg.status = 'sent';
                        // Clear timeout
                        if (state.ackTimeouts[reply_to]) {
                            clearTimeout(state.ackTimeouts[reply_to]);
                            delete state.ackTimeouts[reply_to];
                        }
                    }));
                    return;
                }
                
                get().addSocketAIMessage(response);
            } catch (e) {
                console.error("Socket Parse Error:", e);
            }
        };

        newSocket.onclose = (event) => {
            set({ socket: null, socketStatus: 'disconnected', isLoading: false, isProcessing: false });

            if (!event.wasClean) {
                const { reconnectAttempts } = get();
                const maxAttempts = 5;

                if (reconnectAttempts < maxAttempts) {
                    const timeoutMs = Math.min(1000 * (2 ** reconnectAttempts), 10000);
                    set({ reconnectAttempts: reconnectAttempts + 1 });

                    // 💎 Fix 2: Manage Timeout ID
                    const timeoutId = setTimeout(() => {
                        if (get().isOverlayVisible) {
                            get().connectSocket(token);
                        }
                    }, timeoutMs);
                    set({ reconnectTimeoutId: timeoutId });
                } else {
                    set({ socketStatus: 'error' });
                    get().addSocketAIMessage({
                        type: 'error',
                        content: 'Connection lost. Please refresh.'
                    });
                }
            }
        };

        newSocket.onerror = () => {
            set({ socketStatus: 'error', isProcessing: false, isLoading: false });
        };

      } catch (e: any) {
          if (e.name !== 'AbortError') {
              set({ socketStatus: 'error', isProcessing: false, isLoading: false });
          }
      }
    },

    disconnectSocket: () => {
      const { socket, reconnectTimeoutId, abortController } = get();
      
      // 💎 Fix 2: Clean everything
      if (reconnectTimeoutId) clearTimeout(reconnectTimeoutId);
      if (abortController) abortController.abort();
      
      if (socket) {
          socket.onclose = null;
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

    processOfflineQueue: () => {
        const { socket, messageQueue } = get();
        if (socket && socket.readyState === WebSocket.OPEN && messageQueue.length > 0) {
            // Send all queued messages
            messageQueue.forEach(msg => socket.send(JSON.stringify(msg)));
            set({ messageQueue: [] });
        }
    },

    addSocketAIMessage: (response) => {
      set(produce((state: AIOrderingState) => {
        // 1. تنظيف الـ Typing ومؤشرات التحميل (كودك الأصلي)
        state.messages = state.messages.filter(m => m.contentType !== 'typing');
        state.isLoading = false;

        const lastMsg = state.messages[state.messages.length - 1];

        // لو الرسالة الجديدة هي نفس نوع الرسالة الأخيرة (خاصة الـ recovery أو الدفع) -> تجاهلها فوراً
        if (lastMsg && lastMsg.contentType === response.type) {

            // استثناء: لو المحتوى مختلف جذرياً (مثلاً رسالة خطأ مختلفة)، اسمح بالمرور
            // لكن في حالة الـ prompts الثابتة، نمنعها.
            const isIdenticalContent = JSON.stringify(lastMsg.content) === JSON.stringify(response.content);

            if (isIdenticalContent || response.type === 'recovery_prompt') {
                return; // ⛔ STOP HERE
            }
	}

        if (response.type !== 'typing') {
            state.isProcessing = false;
        }

        // ==============================================================================
        // 🛑 1. ARCHITECTURAL INTERVENTION: SILENCE PROTOCOL (بروتوكول الصمت)
        // ==============================================================================
        // الهدف: منع رسائل "secured in manifest" من دخول المصفوفة نهائياً.
        // نتحقق إذا كان المحتوى نصياً ويحتوي على الجمل المكررة.
        const isNoisyText = 
            (response.type === 'success_text' || response.type === 'text') &&
            typeof response.content === 'string' &&
            (response.content.toLowerCase().includes("secured in manifest") || 
             response.content.toLowerCase().includes("added to order"));

        if (isNoisyText) {
            // ⛔ خروج فوري: لن يتم إنشاء الرسالة ولن تظهر في الشات.
            // (المنتج انضاف للسلة بالفعل في الـ Backend، والـ Cart Preview هيتحدث لوحده)
            return; 
        }

	const isIncomingContentOrButtons =
            response.type === 'confirmation_prompt' ||
            (response.products && response.products.length > 0);

        if (isIncomingContentOrButtons) {
            state.messages = state.messages.filter(m => m.contentType !== 'confirmation_prompt');
        }

        // ==============================================================================
        // ⚙️ CORE LOGIC (كودك الأصلي كما هو بدون تغيير لضمان استقرار النظام)
        // ==============================================================================

        if (response.type === 'FLIGHT_MANIFEST') {
            // Special handling if needed
        }

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
          flight_data: response.flight_data
        };

        if (response.type === 'payment_intent') {
          state.paymentDetails = response.content as PaymentDetails;
          state.recoveryMode = false;
          return; 
        }

        if (response.type === 'ORDER_CANCELLED') {
          state.paymentDetails = null;
          state.recoveryOrderDetails = null;
          state.recoveryMode = false;
          aiMessage.contentType = 'text';
          aiMessage.content = response.content;
        }

        // Deduplication Logic for Cart Previews
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

      const msgId = generateUUID();

      const silentTriggers = [
          "clear cart",
          "confirm order",
          "checkout", "pay now", "cancel order",
          "save for later", "retry payment"
      ];

      if (silentTriggers.some(trigger => text.toLowerCase().includes(trigger))) {
          isButtonCommand = true;
      }


      set(produce((state: AIOrderingState) => {
        state.messages = state.messages.filter(m => m.contentType !== 'typing');

        if (!isButtonCommand) {
          state.messages.push({
              id: generateMessageId(),
              msgId: msgId, // 💎 Track ID
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
      
      // 💎 Fix 4: Set ACK Timeout
      const timeoutId = setTimeout(() => {
          set(produce((state: AIOrderingState) => {
              const msg = state.messages.find(m => m.msgId === msgId);
              if (msg && msg.status === 'sending') {
                  msg.status = 'failed';
                  // Optionally show toast error here
              }
              state.isLoading = false; // Release lock
              state.isProcessing = false;
          }));
      }, 60000); // 8 seconds timeout
      
      set(produce((state: AIOrderingState) => {
          state.ackTimeouts[msgId] = timeoutId;
      }));

      get()._sendInternalCommand(text, { id: msgId }, true); // Pass ID to server
    },

    sendImage: (fullDataUrl, base64Raw, caption) => {
      const { socketStatus } = get();
      const isOnline = socketStatus === 'connected';

      set(produce((state: AIOrderingState) => {
        state.messages.push({
            id: Date.now(), 
            sender: 'user',
            contentType: 'image_user_upload',
            content: caption || 'Analyzing image...',
            imageUrl: fullDataUrl,
            status: 'sent' // Assume sent for images (complex to ACK chunks)
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
                      state.isProcessing = false; // 🔓 Force Unlock
                  }
              }));
          }, 5000); 
      }
      
      try {
          // 3. Prepare & Send (Safe Execution)
          const commandText = caption || "Visual Query";

          get()._sendInternalCommand(commandText, {
              type: 'IMAGE_QUERY',
              image: base64Raw
          }, true);
          
      } catch (e) {
          // في حالة حدوث خطأ أثناء الإرسال (مثل ReferenceError)، نفتح الشاشة فوراً
          console.error("Image Send Error:", e);
          set({ isLoading: false, isProcessing: false }); // 🔓 Emergency Unlock
      }
    },

    _sendInternalCommand: (command, payload: any = {}, silent: boolean = false) => {
        const { socket, socketStatus } = get();
        
        const fullPayload = {
            type: 'CHAT_MESSAGE',
            message: command,
            timestamp: Date.now(),
            ...payload
        };

        // 💎 Fix 3: Offline Queue Logic
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            set(produce((state: AIOrderingState) => {
                state.messageQueue.push(fullPayload);
            }));
            if (!silent) {
                // Optimistic loading state even if offline
                set({ isLoading: true, isProcessing: true });
            }
            return;
        }

        if (!silent) {
            set({ isLoading: true, isProcessing: true, suggestedProductIds: null });
        }

        socket.send(JSON.stringify(fullPayload));
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
            messageQueue: [], // Clear offline queue on reset
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
        set({ isOverlayVisible: true, paymentDetails: null, recoveryOrderDetails: paymentDetails, recoveryMode: true });
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
            // 💎 1. تنظيف: شيل رسالة الاختيارات عشان متبقاش ظاهرة ورا الـ Overlay
            state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');

            // 2. تفعيل: افتح الـ Overlay ورجع بيانات الدفع
            state.isOverlayVisible = true;
            state.recoveryMode = false;
            state.paymentDetails = recoveryOrderDetails;
            state.recoveryOrderDetails = null;
        }));
    },

    setRecoveryReason: (reason) => set({ recoveryReason: reason }),

    saveForLater: () => {
        // إرسال الأمر للسيرفر
        get()._sendInternalCommand('__INTERNAL_SAVE_FOR_LATER__');
        
        // تنظيف السلة
        get().clearCart();
        
        // 💎 التعديل: مسح رسالة الأزرار وتصفير الحالة
        set(produce((state: AIOrderingState) => {
            // 1. مسح الرسالة اللي فيها الأزرار عشان تختفي من الشات
            state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');

            // 2. تصفير باقي الحالات
            state.recoveryMode = false;
            state.recoveryOrderDetails = null;
            state.paymentDetails = null;
        }));
    },

    hardCancelOrder: (reason) => {
        const { recoveryOrderDetails } = get();
        const sanitizedReason = (typeof reason === 'string' && reason) ? reason : 'changed_mind';
        
        // 1. إرسال الأمر للسيرفر
        get()._sendInternalCommand('__CANCEL__', { 
            type: 'CANCEL_INTENT',
            message: { orderId: recoveryOrderDetails?.orderId, reason: sanitizedReason }
        }, true);

        // 2. تحديث الحالة (لاحظ إقفال الأقواس هنا)
        set(produce((state: AIOrderingState) => {
            // مسح الرسالة
            state.messages = state.messages.filter(m => m.contentType !== 'recovery_prompt');
            
            // تعديل القيم مباشرة على state (بدون set داخلية)
            state.recoveryMode = false;
            state.recoveryOrderDetails = null;
            state.paymentDetails = null;
            state.isProcessing = false;
        })); 
    }, // <--- 🔴 دي الفاصلة اللي كانت تايهة منك وقوس إغلاق الدالة

    cancelPaymentIntent: async () => { 
        get().hardCancelOrder(get().recoveryReason); 
    },
  })
);

