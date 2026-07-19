/* apps/web/components/layout/Header.tsx */

"use client";

import React, { useState, useEffect, useCallback, useRef, memo, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Home,
  Package,
  User,
  Menu,
  X as CloseIcon,
  BellRing,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  isProtected: boolean;
}

const navItems: NavItem[] = [
  { href: "/", label: "Home", icon: Home, isProtected: false },
  { href: "/products", label: "Products", icon: Package, isProtected: false },
  { href: "/profile", label: "Profile", icon: User, isProtected: true },
];

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();

  const headerRef = useRef<HTMLElement>(null);
  const floatingBarRef = useRef<HTMLDivElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
      setMobileMenuOpen(false);
    },
    [status, router]
  );

  const DesktopNav = useMemo(() => (
    <nav className="hidden md:flex items-center rounded-full p-1.5 absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto">
      {navItems.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            prefetch={true}
            onClick={(e) => handleProtectedRouting(e, item)}
            className={`relative px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              isActive ? "text-black" : "text-gray-400 hover:text-white"
            }`}
          >
            <span className="relative z-10">{item.label}</span>
            {isActive && (
              <motion.div
                layoutId="active-pill"
                className="absolute inset-0 bg-white shadow-[0_0_25px_rgba(255,255,255,0.5)] transform-gpu will-change-transform"
                style={{ borderRadius: 9999 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
          </Link>
        );
      })}
    </nav>
  ), [pathname, handleProtectedRouting]);

  return (
    <>
      <header
        ref={headerRef}
        data-scrolled="false"
        className="fixed top-0 left-0 right-0 z-50 h-24 transition-all duration-[50ms] ease-[cubic-bezier(0.16,1,0.3,1)] data-[scrolled=true]:-translate-y-[100px] data-[scrolled=true]:opacity-0 data-[scrolled=true]:pointer-events-none transform-gpu will-change-transform"
      >
        <div className="container mx-auto px-6 h-full flex justify-between items-center relative">
          <div className="pointer-events-auto px-3 py-1">
            <Link
              href="/"
              prefetch={true}
              className="group flex items-center gap-2 relative z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-sm block"
            >
              <div className="relative flex items-center mb-1">
                <Image
                  src="/logo.png"
                  alt="airdeliver homepage"
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

          {DesktopNav}

          <div className="hidden md:flex items-center gap-1 relative z-10 pointer-events-auto">
            <div className="flex items-center gap-1 rounded-full p-1.5">
              <Link
                href="/notifications"
                className="relative group p-3 rounded-full text-white transition-all duration-300 hover:text-cyan-400 hover:bg-cyan-400/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                aria-label="Notifications"
                onClick={(e) => handleProtectedRouting(e, { href: '/notifications', label: 'Notifications', isProtected: true })}
              >
                <BellRing size={20} className="transition-transform duration-300 group-hover:scale-110 group-hover:rotate-12" aria-hidden="true" />
              </Link>
            </div>
          </div>

          <div className="md:hidden relative z-10 pointer-events-auto rounded-full">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-3 text-white hover:bg-white/10 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              type="button"
              aria-label="Open navigation menu"
            >
              <Menu size={24} aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      <div
        ref={floatingBarRef}
        data-scrolled="false"
        className="fixed bottom-8 left-1/2 z-50 flex -translate-x-1/2 items-center gap-6 rounded-full border border-white/40 bg-white/30 px-6 py-3 backdrop-blur-xl shadow-[0_8px_32px_rgba(255,255,255,0.25)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] translate-y-[100px] opacity-0 scale-90 pointer-events-none data-[scrolled=true]:translate-y-0 data-[scrolled=true]:opacity-100 data-[scrolled=true]:scale-100 data-[scrolled=true]:pointer-events-auto transform-gpu will-change-transform"
      >
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={`float-${item.href}`}
              href={item.href}
              prefetch={true}
              onClick={(e) => handleProtectedRouting(e, item)}
              className={`relative flex items-center justify-center p-3.5 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black ${
                isActive
                  ? "bg-white/90 shadow-lg text-black scale-110"
                  : "text-black/70 hover:text-black hover:bg-white/50 hover:scale-105"
              }`}
            >
              <item.icon size={22} strokeWidth={isActive ? 2.5 : 2} />
            </Link>
          );
        })}
      </div>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-2xl md:hidden transform-gpu will-change-opacity"
          >
            <motion.div
              initial={{ x: 100 }}
              animate={{ x: 0 }}
              exit={{ x: 100 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="absolute right-0 top-0 bottom-0 w-[85vw] max-w-sm bg-[#050505] border-l border-white/10 p-8 flex flex-col shadow-2xl transform-gpu will-change-transform contain-strict"
            >
              <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                <Image
                  src="/logo.png"
                  alt="airdeliver logo"
                  width={120}
                  height={24}
                  className="object-contain"
                />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 text-gray-400 hover:text-white hover:rotate-90 transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-full"
                  type="button"
                  aria-label="Close navigation menu"
                >
                  <CloseIcon size={24} aria-hidden="true" />
                </button>
              </div>

              <nav className="flex flex-col gap-3">
                {navItems.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      prefetch={true}
                      onClick={(e) => handleProtectedRouting(e, item)}
                      className={`flex items-center gap-4 p-5 rounded-2xl text-sm font-bold uppercase tracking-widest transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                        isActive
                          ? "bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)]"
                          : "text-gray-500 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <item.icon size={20} aria-hidden="true" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
