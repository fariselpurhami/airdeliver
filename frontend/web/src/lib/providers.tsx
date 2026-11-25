// frontend/web/lib/providers.tsx

"use client";

import { type ReactNode } from "react";
import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { LazyMotion, domAnimation } from "framer-motion";

export interface ProvidersProps {
  readonly children: ReactNode;
  /** CSP nonce threaded from the root layout for inline provider scripts. */
  readonly nonce?: string;
  /** Reserved for RUM telemetry binding; accepted but not yet consumed. */
  readonly traceId?: string;
}

export function Providers({ children, nonce }: ProvidersProps) {
  return (
    <SessionProvider>
      <ThemeProvider 
        attribute="class" 
        defaultTheme="system" 
        enableSystem 
        disableTransitionOnChange
        nonce={nonce}
      >
        <LazyMotion features={domAnimation}>
          {children}
        </LazyMotion>
      </ThemeProvider>
    </SessionProvider>
  );
}
