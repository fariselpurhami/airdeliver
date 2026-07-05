// apps/web/app/layout.tsx

import type { Metadata, Viewport } from 'next';
import { Inter, Orbitron, Montserrat } from 'next/font/google';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Toaster } from 'sonner';

import { Providers } from '@/lib/providers';
import AppShell from '@/components/layout/AppShell';
import '@/app/globals.css';

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${inter.variable} ${orbitron.variable} ${montserrat.variable} no-scrollbar`}
    >
      <body className="min-h-screen bg-background font-sans antialiased no-scrollbar selection:bg-primary/20 selection:text-primary">
        <Providers>
          <AppShell>{children}</AppShell>
          <Toaster position="bottom-right" richColors closeButton expand={false} />
        </Providers>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
