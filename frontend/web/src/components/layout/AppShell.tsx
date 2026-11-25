// frontend/web/components/layout/AppShell.tsx

"use client";

import React from "react";
import { OrderingOverlayHostContext } from "@/components/ai/OrderingOverlayHostContext";
import dynamic from "next/dynamic";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import AIChatOverlay from "@/components/ai/AIChatOverlay";
import { useUIStore } from "@/hooks/useUIStore";
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

  const isProductOverlayVisible = useUIStore(state => state.isProductOverlayVisible);
  const isAnyOverlayVisible = isOverlayVisible || isProductOverlayVisible;

  return (
    <OrderingOverlayHostContext.Provider value={true}>
    <div data-ordering-open={isOverlayVisible || undefined} className="app-shell relative flex min-h-dvh w-full max-w-full flex-col overflow-x-clip bg-background">
      <div hidden={isAnyOverlayVisible} inert={isAnyOverlayVisible} aria-hidden={isAnyOverlayVisible || undefined}><Header /></div>
      <main inert={isAnyOverlayVisible} aria-hidden={isAnyOverlayVisible || undefined} className="relative flex-1 w-full max-w-full overflow-x-clip">
        {children}
      </main>
      <div hidden={isAnyOverlayVisible} inert={isAnyOverlayVisible}><Footer /></div>
      <AIChatOverlay
        shellOwned
        isOpen={isOverlayVisible}
        onClose={() => setOverlayVisible(false)}
      />
      <div hidden={isAnyOverlayVisible} inert={isAnyOverlayVisible}><Chatbot /></div>
    </div>
    </OrderingOverlayHostContext.Provider>
  );
}
