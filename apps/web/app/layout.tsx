// apps/web/app/layout.tsx 

import './globals.css';
import type { Metadata } from 'next';
import { Inter, Orbitron } from 'next/font/google';
import { Providers } from '@/lib/providers';
import AppShell from '@/components/layout/AppShell';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const orbitron = Orbitron({ subsets: ['latin'], variable: '--font-orbitron', weight: ['400', '700', '900'] });

export const metadata: Metadata = {
  title: 'airdeliver',
  description: 'We Soar In The Sky By Delivering Your Orders',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>

      <body className={`${inter.variable} ${orbitron.variable} font-sans`}>
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
        </Providers>
      </body>
    </html>
  );
}
