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
}

const createWelcomeMessage = (): ChatMessage => ({
  id: uuidv4(),
  sender: 'ai',
  data: {
    text: 'Hello! How Can I Help You?',
    action: null,
    explain: "Initial greeting.",
    confidence: 1.0,
    telemetry: { intent: "greeting" }
  },
});

export const useAISupportStore = create<AISupportState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      messages: [createWelcomeMessage()],
      isLoading: false,
      sessionId: uuidv4(),

      setIsOpen: (isOpen) => {
        if (isOpen && (get().messages.length === 0 || get().isLoading)) {
          set({ 
            isOpen: true, 
            messages: [createWelcomeMessage()], 
            sessionId: uuidv4(),
            isLoading: false
          });
        } else {
          set({ isOpen });
        }
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
