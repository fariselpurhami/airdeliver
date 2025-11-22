// apps/web/components/layout/AppShell.tsx

'use client'; 

import React from 'react';
import Header from '@/components/layout/Header';
import Footer from "@/components/layout/Footer";
import dynamic from 'next/dynamic';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';
import AIChatOverlay from '../ai/AIChatOverlay';

const Chatbot = dynamic(() => import('@/components/ai/chatbot'), {
  ssr: false,
});

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
