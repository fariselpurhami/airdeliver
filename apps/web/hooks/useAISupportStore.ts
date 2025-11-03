// file: apps/web/hooks/useAISupportStore.ts

'use client';

import { create } from 'zustand';
import { useSession } from 'next-auth/react';

export interface NeuralCoreResponse {
  text: string;
  action: any;
  explain: string;
  confidence: number;
  telemetry: any;
}

export type ChatMessage = {
    sender: 'user' | 'ai';
    data: NeuralCoreResponse;
};

interface AISupportState {
  isOpen: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const useAISupportStoreBase = create<AISupportState>((set) => ({
  isOpen: false,
  messages: [{
    sender: 'ai',
    data: {
        text: 'Hello! How Can I Help You?',
        action: null,
        explain: "Initial greeting.",
        confidence: 1.0,
        telemetry: { intent: "greeting" }
    }
  }],
  isLoading: false,
  setIsOpen: (isOpen) => set({ isOpen }),
}));

export const useAISupportStore = () => {
    const state = useAISupportStoreBase();
    const { data: session } = useSession();

    const sendMessage = async (text: string) => {
        if (!text.trim() || state.isLoading) return;

        const userMessage: ChatMessage = {
            sender: 'user',
            data: { text, action: null, explain: "User input.", confidence: 1.0, telemetry: { intent: 'user_message' } }
        };
        
        useAISupportStoreBase.setState(s => ({ 
            messages: [...s.messages, userMessage],
            isLoading: true 
        }));

        try {
            // @ts-ignore
            const token = session?.accessToken;

            if (!token) {
                throw new Error("User is not authenticated (session token missing).");
            }

            const response = await fetch('/api/v1/ai-support/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message: text }),
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const aiResponseData: NeuralCoreResponse = await response.json();
            const aiMessage: ChatMessage = { sender: 'ai', data: aiResponseData };

            useAISupportStoreBase.setState(s => ({
                messages: [...s.messages, aiMessage],
                isLoading: false,
            }));

        } catch (error) {
            const errorResponse: ChatMessage = {
                sender: 'ai',
                data: {
                    text: `I am having trouble connecting: ${error instanceof Error ? error.message : String(error)}`,
                    action: null,
                    explain: `An API or network error occurred: ${error}`,
                    confidence: 1.0,
                    telemetry: { intent: "error" }
                }
            };
            useAISupportStoreBase.setState(s => ({
                messages: [...s.messages, errorResponse],
                isLoading: false,
            }));
        }
    };

    return { ...state, sendMessage };
};
