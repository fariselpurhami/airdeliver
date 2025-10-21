"use client";

import { Bot } from 'lucide-react';
import { useAISupportStore } from '@/hooks/useAISupportStore';

export const AISupportButton = () => {
  
  const { setIsOpen } = useAISupportStore();

  return (
    <button
      
      onClick={() => setIsOpen(true)}
      className="fixed bottom-6 right-6 z-50 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-400 to-violet-500 text-white shadow-lg transition-transform duration-300 hover:scale-110"
      aria-label="Open AI Support Chat"
    >
      <Bot size={32} />
    </button>
  );
};
