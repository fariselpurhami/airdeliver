// apps/web/components/layout/AppShell.tsx

"use client";

import React from "react";
import { OrderingOverlayHostContext } from "@/components/ai/OrderingOverlayHostContext";
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
  const isOverlayVisible = useAIOrderingStore(state => state.isOverlayVisible);
  const setOverlayVisible = useAIOrderingStore(state => state.setOverlayVisible);

  return (
    <OrderingOverlayHostContext.Provider value={true}>
    <div data-ordering-open={isOverlayVisible || undefined} className="app-shell relative flex min-h-dvh w-full max-w-full flex-col overflow-x-clip bg-background">
      <div hidden={isOverlayVisible} inert={isOverlayVisible} aria-hidden={isOverlayVisible || undefined}><Header /></div>
      <main inert={isOverlayVisible} aria-hidden={isOverlayVisible || undefined} className="relative flex-1 w-full max-w-full overflow-x-clip">
        {children}
      </main>
      <div hidden={isOverlayVisible} inert={isOverlayVisible}><Footer /></div>
      <AIChatOverlay
        shellOwned
        isOpen={isOverlayVisible}
        onClose={() => setOverlayVisible(false)}
      />
      <div hidden={isOverlayVisible} inert={isOverlayVisible}><Chatbot /></div>
    </div>
    </OrderingOverlayHostContext.Provider>
  );
}
