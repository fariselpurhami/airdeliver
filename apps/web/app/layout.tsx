
import AIOrderingOverlay from '@/components/ai/AIOrderingOverlay';
import Chatbot from '@/components/ai/Chatbot';
import type { Metadata } from "next";
import { Providers } from "../lib/providers";
import Header from "../components/layout/Header";
import Footer from "../components/layout/Footer";
import ClientOnly from '@/components/ClientOnly';
import "./globals.css";

export const metadata: Metadata = {
  title: "airdeliver",
  description: "We Soar In The Sky By Delivering Your Orders.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="flex flex-col min-h-screen">
            <ClientOnly>
              <Header />
            </ClientOnly>
            
            <main className="flex-grow container mx-auto px-4">{children}</main>
            
            <Footer />
          </div>

          <ClientOnly>
            <AIOrderingOverlay />
            <Chatbot />
          </ClientOnly>
        </Providers>
      </body>
    </html>
  );
}
