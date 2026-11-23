// apps/web/app/layout.tsx

import { randomId } from '@/lib/random-id';
import type { Metadata, Viewport } from 'next';
import { Inter, Orbitron, Montserrat } from 'next/font/google';
import { headers } from 'next/headers';
import { Suspense } from 'react';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Toaster } from 'sonner';

import PWAGuard from '@/components/layout/PWAGuard';
import { Providers } from '@/lib/providers';
import AppShell from '@/components/layout/AppShell';
import { ViewportEnforcer } from '@/components/layout/ViewportEnforcer';
import '@/app/globals.css';

/**
 * STRICT CONTRACT DEFINITION
 * Defines the precise shape of the RootLayout properties.
 */
interface RootLayoutProps {
  children: React.ReactNode;
}

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  preload: true,
});

const orbitron = Orbitron({
  subsets: ['latin'],
  weight: ['400', '700', '900'],
  variable: '--font-orbitron',
  display: 'swap',
  preload: true,
});

const montserrat = Montserrat({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-montserrat',
  display: 'swap',
  preload: true,
});

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#000000' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: 'airdeliver',
    template: '%s | airdeliver',
  },
  description: "World's First AI-Driven Delivery Infrastructure.",
  keywords: ['AI', 'Delivery', 'Logistics', 'Infrastructure', 'Autonomous'],
  authors: [{ name: 'airdeliver Team' }],
  creator: 'airdeliver',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://airdeliver.com',
    title: 'airdeliver',
    description: "World's First AI-Driven Delivery Infrastructure.",
    siteName: 'airdeliver',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'airdeliver',
    description: "World's First AI-Driven Delivery Infrastructure.",
    creator: '@airdeliver',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};

export default async function RootLayout({ children }: RootLayoutProps) {
  // Await headers to support Next.js 15+ strict async server APIs
  const headersList = await headers();
  
  // Extract edge-injected security and telemetry identifiers
  const nonce = headersList.get('x-nonce') ?? undefined;
  const traceId = headersList.get('x-trace-id') ?? randomId();

  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${inter.variable} ${orbitron.variable} ${montserrat.variable} no-scrollbar`}
    >
      <head>
        {/* Propagate Edge Trace ID for Real User Monitoring (RUM) linkage */}
        <meta name="x-trace-id" content={traceId} />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased no-scrollbar selection:bg-primary/20 selection:text-primary">
        <ViewportEnforcer />
        
        {/* Pass nonce and traceId into providers to enforce CSP across dynamic Client Components */}
        <Providers nonce={nonce} traceId={traceId}>
          {/* 
            Strict PPR Boundary: Wrap dynamic guards and stateful shells in Suspense.
            This guarantees the static HTML above can be edge-cached and streamed instantly.
          */}
          <Suspense fallback={<div id="app-shell-skeleton" aria-hidden="true" />}>
            <PWAGuard>
              <AppShell>{children}</AppShell>
            </PWAGuard>
          </Suspense>
          
          <Toaster position="bottom-right" richColors closeButton expand={false} />
        </Providers>

        {/* @vercel/analytics does not accept a CSP nonce in this version */}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
