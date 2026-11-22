// apps/web/components/layout/AppShell.tsx

"use client";

import React from "react";
import dynamic from "next/dynamic";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import AIChatOverlay from "@/components/ai/AIChatOverlay";
import { useAIOrderingStore } from "@/hooks/useAIOrderingStore";

const Chatbot = dynamic(() => import("@/components/ai/Chatbot"), {
  ssr: false,
});

type AppShellProps = {
  children: React.ReactNode;
};

export default function AppShell({ children }: AppShellProps) {
  const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();

  return (
    <div className="relative flex min-h-dvh w-full max-w-full flex-col overflow-x-clip bg-background">
      <Header />
      <main className="relative flex-1 w-full max-w-full overflow-x-clip">
        {children}
      </main>
      <Footer />
      <AIChatOverlay
        isOpen={isOverlayVisible}
        onClose={() => setOverlayVisible(false)}
      />
      <Chatbot />
    </div>
  );
}
