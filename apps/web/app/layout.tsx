import { Inter } from "next/font/google";
import { Providers } from "@/lib/providers";
import AppShell from "@/components/layout/AppShell"; 
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });


export const metadata = {
  title: "airdeliver",
  description: "We Soar In The Sky By Delivering Your Orders",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className}`}>
        <Providers>
          
          <AppShell>
            {children}
          </AppShell>
        </Providers>
      </body>
    </html>
  );
}
