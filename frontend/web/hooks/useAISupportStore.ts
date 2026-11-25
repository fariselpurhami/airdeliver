'use client';

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { persist, createJSONStorage } from 'zustand/middleware';
import { api } from '@/lib/api';

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
  fetchInitialGreeting: () => void; 
}

export const useAISupportStore = create<AISupportState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      messages: [], 
      isLoading: false,
      sessionId: uuidv4(),

      setIsOpen: (isOpen) => {
        const { messages, fetchInitialGreeting } = get();
        
        if (isOpen) {
          
          if (messages.length === 0) {
            set({ isOpen: true, isLoading: true, sessionId: uuidv4() });
            fetchInitialGreeting(); 
          } else {

            set({ isOpen: true });
          }
        } else {

          set({ isOpen: false });
        }
      },

     
      fetchInitialGreeting: async () => {
        const sessionId = get().sessionId;
        let aiMessage: ChatMessage;

        try {
          const {data:aiResponseData} = await api.post<NeuralCoreResponse>('/ai-support/chat', {message:"__INITIAL_GREETING__",session_id:sessionId});
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
          const {data:aiResponseData} = await api.post<NeuralCoreResponse>('/ai-support/chat', {message:text,session_id:sessionId});
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
