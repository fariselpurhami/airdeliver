// file: apps/web/components/layout/Header.tsx
// version: 1.0.0
// date: 2025-09-23
// author: Gemini 2.5 Pro

'use client';

import Link from "next/link";
import Image from "next/image";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useCartStore } from "@/hooks/useCartStore";
import { FiShoppingCart } from "react-icons/fi";

const Header = () => {
  const { items } = useCartStore();
  const cartItemCount = items.reduce((acc, item) => acc + item.quantity, 0);

  return (
    <header className="py-4 px-6 border-b sticky top-0 bg-background/80 backdrop-blur-sm z-50">
      <div className="container mx-auto flex justify-between items-center">
        <Link href="/" className="flex items-center gap-2">
       
          <span className="text-2xl font-bold tracking-wider">airdeliver</span>
        </Link>
        <nav className="hidden md:flex gap-6 items-center">
	  <Link href="/" className="hover:text-foreground/70 transition-colors">Home</Link>
          <Link href="/products" className="hover:text-foreground/70 transition-colors">Products</Link>
          <Link href="/about" className="hover:text-foreground/70 transition-colors">About</Link>
          <Link href="/profile" className="hover:text-foreground/70 transition-colors">Profile</Link>
        </nav>
        <div className="flex items-center gap-4">
          <Link href="/cart" className="relative">
            <FiShoppingCart size={24} />
            {cartItemCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center animate-bounce">
                {cartItemCount}
              </span>
            )}
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
};

export default Header;

