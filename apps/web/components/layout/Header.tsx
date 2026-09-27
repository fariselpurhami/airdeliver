/* apps/web/components/layout/Header.tsx */

"use client";

import React, { useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Home,
  ShoppingBag,
  User,
  LucideIcon,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  isProtected: boolean;
}

const navItems: NavItem[] = [
  { href: "/", label: "Home", icon: Home, isProtected: false },
  { href: "/products", label: "Products", icon: ShoppingBag, isProtected: false },
  { href: "/profile", label: "Profile", icon: User, isProtected: true },
];

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();

  const headerRef = useRef<HTMLElement>(null);
  const floatingBarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let rafId: number;
    const handleScroll = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const isScrolled = window.scrollY > 1;
        const stringScrolled = String(isScrolled);

        if (headerRef.current && headerRef.current.dataset.scrolled !== stringScrolled) {
          headerRef.current.dataset.scrolled = stringScrolled;
        }

        if (floatingBarRef.current && floatingBarRef.current.dataset.scrolled !== stringScrolled) {
          floatingBarRef.current.dataset.scrolled = stringScrolled;
        }
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
      cancelAnimationFrame(rafId);
    };
  }, []);

  const handleProtectedRouting = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, item: Omit<NavItem, 'icon'>) => {
      if (item.isProtected && status === "unauthenticated") {
        e.preventDefault();
        const targetUrl = `/login?callbackUrl=${encodeURIComponent(item.href)}`;
        router.push(targetUrl);
      }
    },
    [status, router]
  );

  return (
    <>
      <header
        ref={headerRef}
        data-scrolled="false"
        className="fixed top-0 left-0 right-0 z-50 h-24 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] data-[scrolled=true]:-translate-y-[100px] data-[scrolled=true]:opacity-0 data-[scrolled=true]:pointer-events-none transform-gpu will-change-transform"
      >
        <div className="container mx-auto px-5 sm:px-6 lg:px-12 h-full flex justify-between items-center relative">
          
          {/* Logo Section */}
          <div className="pointer-events-auto px-1 py-1">
            <Link
              href="/"
              prefetch={true}
              aria-label="Go to airdeliver homepage"
              className="group flex items-center gap-2 relative z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-4 focus-visible:ring-offset-black rounded-sm block"
            >
              <div className="relative flex items-center mb-1">
                <Image
                  src="/logo.png"
                  alt=""
                  width={120}
                  height={22}
                  priority
                  className="object-contain transition-opacity duration-500 group-hover:opacity-80 drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)] transform-gpu"
                />
                <Image
                  src="/logo.png"
                  alt=""
                  width={120}
                  height={22}
                  priority
                  decoding="async"
                  className="absolute top-0 left-0 object-contain opacity-0 group-hover:opacity-40 blur-md transition-opacity duration-300 transform-gpu will-change-opacity"
                  aria-hidden="true"
                />
              </div>
            </Link>
          </div>

          {/* Inline Navigation (Replaces Hamburger) */}
          <nav className="relative z-10 pointer-events-auto flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={`top-${item.href}`}
                  href={item.href}
                  prefetch={true}
                  onClick={(e) => handleProtectedRouting(e, item)}
                  aria-label={item.label}
                  aria-current={isActive ? "page" : undefined}
                  className={`relative flex items-center justify-center w-10 h-10 sm:w-11 sm:h-11 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                    isActive
                      ? "bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]"
                      : "text-zinc-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} aria-hidden="true" />
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Enterprise-Grade Floating Action Bar */}
      <nav
        ref={floatingBarRef}
        data-scrolled="false"
        aria-label="Quick navigation"
        className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/10 bg-[#0A0A0A]/85 p-1.5 backdrop-blur-2xl shadow-[0_20px_40px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.1)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] translate-y-[100px] opacity-0 scale-95 pointer-events-none data-[scrolled=true]:translate-y-0 data-[scrolled=true]:opacity-100 data-[scrolled=true]:scale-100 data-[scrolled=true]:pointer-events-auto transform-gpu will-change-transform"
      >
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={`float-${item.href}`}
              href={item.href}
              prefetch={true}
              onClick={(e) => handleProtectedRouting(e, item)}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
              className={`relative flex items-center justify-center w-12 h-12 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                isActive
                  ? "bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)] scale-105"
                  : "text-zinc-400 hover:text-white hover:bg-white/10 active:scale-95"
              }`}
            >
              <item.icon size={22} strokeWidth={isActive ? 2.5 : 2} aria-hidden="true" />
            </Link>
          );
        })}
      </nav>
    </>
  );
}
