'use client'; 

import React from 'react';
import Header from '@/components/layout/Header';
import Footer from "@/components/layout/Footer"; // 🚀 FIX 1: (f سمول)
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import dynamic from 'next/dynamic'; // 🚀 FIX 2: (استخدام Dynamic)
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

// 🚀 FIX 2: (استدعاء الشات بوت بطريقة ديناميكية لكسر الدايرة)
const Chatbot = dynamic(() => import('@/components/ai/chatbot'), {
  ssr: false,
  loading: () => <p>Loading...</p>
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
      
      {/* 🚀 FIX 2: (استدعاء الشات بوت هنا فقط) */}
      <Chatbot />
    </>
  );
}
