'use client';

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface NeuralCoreResponse {
  text: string;
  action: any;
  explain: string;
  confidence: number;
  telemetry: any;
}

export type ChatMessage = {
  id: string;
  sender: 'user' | 'ai';
  data: NeuralCoreResponse;
};

interface AISupportState {
  isOpen: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  sessionId: string;
  setIsOpen: (isOpen: boolean) => void;
  sendMessage: (text: string) => void;
  fetchInitialGreeting: () => void; // 🚀 (1) أضفنا الوظيفة الجديدة
}

// 🚀 (2) حذفنا الرسالة الوهمية (createWelcomeMessage)

export const useAISupportStore = create<AISupportState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      messages: [], // 🚀 (3) الحالة المبدئية: لا توجد رسائل
      isLoading: false,
      sessionId: uuidv4(),

      setIsOpen: (isOpen) => {
        const { messages, fetchInitialGreeting } = get();
        
        if (isOpen) {
          // إذا فتح المستخدم الشات، وكان الشات فارغاً
          if (messages.length === 0) {
            set({ isOpen: true, isLoading: true, sessionId: uuidv4() });
            fetchInitialGreeting(); // 🚀 (4) قم بطلب الرد الذكي من الباك إند
          } else {
            // لو الشات مفتوح وفيه رسايل، اعرضه بس
            set({ isOpen: true });
          }
        } else {
          // لو قفل الشات
          set({ isOpen: false });
        }
      },

     
      fetchInitialGreeting: async () => {
        const sessionId = get().sessionId;
        let aiMessage: ChatMessage;

        try {
          const response = await fetch('/api/v1/ai-support/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            
            body: JSON.stringify({ message: "__INITIAL_GREETING__", session_id: sessionId }),
          });

          if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
          }

          const aiResponseData: NeuralCoreResponse = await response.json();
          aiMessage = { id: uuidv4(), sender: 'ai', data: aiResponseData };

        } catch (error) {
          aiMessage = {
            id: uuidv4(),
            sender: 'ai',
            data: {
              text: `I am having trouble connecting: ${error instanceof Error ? error.message : String(error)}`,
              action: null,
              explain: `An API or network error occurred: ${error}`,
              confidence: 1.0,
              telemetry: { intent: "error" }
            }
          };
        }

        // نضع الرد الذكي (الذي يحتوي على الأزرار) كـ "أول" رسالة
        set({ messages: [aiMessage], isLoading: false });
      },

      sendMessage: async (text: string) => {
        if (!text.trim() || get().isLoading) return;

        const userMessage: ChatMessage = {
          id: uuidv4(),
          sender: 'user',
          data: { text, action: null, explain: "User input.", confidence: 1.0, telemetry: { intent: 'user_message' } }
        };
        
        set((state) => ({ 
          messages: [...state.messages, userMessage],
          isLoading: true 
        }));

        const sessionId = get().sessionId;
        let aiMessage: ChatMessage;

        try {
          const response = await fetch('/api/v1/ai-support/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_id: sessionId }),
          });

          if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
          }

          const aiResponseData: NeuralCoreResponse = await response.json();
          aiMessage = { id: uuidv4(), sender: 'ai', data: aiResponseData };

        } catch (error) {
          aiMessage = {
            id: uuidv4(),
            sender: 'ai',
            data: {
              text: `I am having trouble connecting: ${error instanceof Error ? error.message : String(error)}`,
              action: null,
              explain: `An API or network error occurred: ${error}`,
              confidence: 1.0,
              telemetry: { intent: "error" }
            }
          };
        }

        set((state) => ({
          messages: [...state.messages, aiMessage],
          isLoading: false,
        }));
      },
    }),
    {
      name: 'ai-support-session',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ sessionId: state.sessionId }),
    }
  )
);
