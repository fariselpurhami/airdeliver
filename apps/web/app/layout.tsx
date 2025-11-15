// ** apps/web/app/layout.tsx **//

import type { Metadata } from 'next';
import { Inter, Orbitron, Montserrat } from 'next/font/google';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Providers } from '@/lib/providers';
import AppShell from '@/components/layout/AppShell';
import { Toaster } from 'sonner';
import '@/app/globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const orbitron = Orbitron({
  subsets: ['latin'],
  weight: ['400', '700', '900'],
  variable: '--font-orbitron',
  display: 'swap',
});

const montserrat = Montserrat({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-montserrat',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'airdeliver',
  description: "World's First AI-Driven Delivery Infrastructure.",
  themeColor: '#000000',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${orbitron.variable} ${montserrat.variable} dark`} suppressHydrationWarning>
      <head />
      <body className="antialiased">
        <Providers>
          <AppShell>
            {children}
          </AppShell>
          <Toaster
            position="bottom-right"
            richColors
            theme="dark" 
            toastOptions={{
              style: { background: '#111', border: '1px solid #333', color: '#eee' },
            }}
          />
          <Analytics />
          <SpeedInsights />
        </Providers>
      </body>
    </html>
  );
}
