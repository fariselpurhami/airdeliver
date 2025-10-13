// file: apps/web/hooks/useAISupportStore.ts
'use client';

import { create } from 'zustand';

// Defines the shape of the rich response from the Neural Core
export interface NeuralCoreResponse {
  text: string;
  action: any;
  explain: string;
  confidence: number;
  telemetry: any;
}

// We will also track who the sender of the message is for UI purposes
export type ChatMessage = {
    sender: 'user' | 'ai';
    data: NeuralCoreResponse;
};

interface AISupportState {
  isOpen: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  setIsOpen: (isOpen: boolean) => void;
  sendMessage: (text: string) => void;
}

export const useAISupportStore = create<AISupportState>((set, get) => ({
  isOpen: false,
  messages: [{
    sender: 'ai',
    data: {
        text: 'Hello! I am the airdeliver Neural Core. How can I assist you?',
        action: null,
        explain: "Initial greeting.",
        confidence: 1.0,
        telemetry: { intent: "greeting" }
    }
  }],
  isLoading: false,
  setIsOpen: (isOpen) => set({ isOpen }),
  sendMessage: async (text) => {
    if (!text.trim() || get().isLoading) return;

    const userMessage: ChatMessage = {
        sender: 'user',
        data: { text, action: null, explain: "User input.", confidence: 1.0, telemetry: { intent: 'user_message' } }
    };
    
    set(state => ({ 
        messages: [...state.messages, userMessage],
        isLoading: true 
    }));

    try {
        const response = await fetch('/api/v1/ai-support/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }

        const aiResponseData: NeuralCoreResponse = await response.json();
        const aiMessage: ChatMessage = { sender: 'ai', data: aiResponseData };
        
        set(state => ({
            messages: [...state.messages, aiMessage],
            isLoading: false,
        }));

    } catch (error) {
        const errorResponse: ChatMessage = {
            sender: 'ai',
            data: {
                text: 'I am having trouble connecting to the Neural Core. Please try again in a moment.',
                action: null,
                explain: `An API or network error occurred: ${error}`,
                confidence: 1.0,
                telemetry: { intent: "error" }
            }
        };
        set(state => ({
            messages: [...state.messages, errorResponse],
            isLoading: false,
        }));
    }
  },
}));
