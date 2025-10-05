"use client";

import { MessageSquare } from 'lucide-react';
import { useAISupportStore } from '@/hooks/useAISupportStore';

export const AISupportButton = () => {
  const { openSupport } = useAISupportStore();

  return (
    <button
      onClick={openSupport}
      className="fixed bottom-8 right-8 z-40 p-4 bg-primary text-primary-foreground rounded-full shadow-lg hover:scale-110 transition-transform duration-300"
      aria-label="Open AI Support"
    >
      <MessageSquare size={28} />
    </button>
  );
};
