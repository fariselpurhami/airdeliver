//** apps/web/lib/providers.tsx **//

"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { ReactNode } from "react";
import { LazyMotion, domAnimation } from "framer-motion";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <LazyMotion features={domAnimation}>
          {children}
	</LazyMotion>
      </ThemeProvider>
    </SessionProvider>
  );
}
