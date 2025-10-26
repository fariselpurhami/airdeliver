// components/layout/AppShell.tsx

'use client'; 

import React from 'react';
import Header from '@/components/layout/Header';
import Footer from "@/components/layout/Footer";
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import Chatbot from '@/components/ai/Chatbot';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

export default function AppShell({ children }: { children: React.ReactNode }) {
  
  const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();

  return (
    <>
      
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-grow container mx-auto px-4">{children}</main>
        <Footer />
      </div>
      
      <AIChatOverlay 
        isOpen={isOverlayVisible} 
        onClose={() => setOverlayVisible(false)} 
      />
      <Chatbot />
    </>
  );
}
