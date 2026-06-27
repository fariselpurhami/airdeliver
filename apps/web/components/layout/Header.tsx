// apps/web/components/layout/Header.tsx
"use client";

import React, { useState, useEffect, useCallback, useRef, memo } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "next-themes";
import {
  Home,
  Package,
  User,
  Sun,
  Moon,
  Menu,
  X as CloseIcon,
  Bell,
} from "lucide-react";

// -----------------------------------------------------------------------------
// Types & Config
// -----------------------------------------------------------------------------

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  isProtected: boolean;
}

const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Home", icon: Home, isProtected: false },
  { href: "/products", label: "Products", icon: Package, isProtected: false },
  { href: "/profile", label: "Profile", icon: User, isProtected: true },
];

// -----------------------------------------------------------------------------
// Sub-Components (Memoized for Render Isolation)
// -----------------------------------------------------------------------------

const ThemeToggle = memo(function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="w-10 h-10 rounded-full bg-white/5" aria-hidden="true" />;
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
      aria-label="Toggle theme"
      type="button"
    >
      <AnimatePresence initial={false} mode="wait">
        <motion.div
          key={isDark ? "moon" : "sun"}
          initial={{ opacity: 0, rotate: -45 }}
          animate={{ opacity: 1, rotate: 0 }}
          exit={{ opacity: 0, rotate: 45 }}
          transition={{ duration: 0.15 }}
        >
          {isDark ? (
            <Moon size={18} className="text-gray-200" />
          ) : (
            <Sun size={18} className="text-gray-200" />
          )}
        </motion.div>
      </AnimatePresence>
    </button>
  );
});

// -----------------------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------------------

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  // Use refs to avoid stale closures in the scroll handler without re-registering it
  const isScrolledRef = useRef(isScrolled);
  const isVisibleRef = useRef(isVisible);
  const lastScrollY = useRef(0);
  const ticking = useRef(false);

  useEffect(() => { isScrolledRef.current = isScrolled; }, [isScrolled]);
  useEffect(() => { isVisibleRef.current = isVisible; }, [isVisible]);

  // Single passive scroll listener — far cheaper than useMotionValueEvent + framer tracking
  useEffect(() => {
    const onScroll = () => {
      if (ticking.current) return;
      ticking.current = true;

      requestAnimationFrame(() => {
        const latest = window.scrollY;
        const previous = lastScrollY.current;
        const delta = latest - previous;
        lastScrollY.current = latest;
        ticking.current = false;

        // Fog logic
        const shouldBeScrolled = latest > 20;
        if (shouldBeScrolled !== isScrolledRef.current) {
          setIsScrolled(shouldBeScrolled);
        }

        // Boundary guard — at top, always show
        if (latest <= 0) {
          if (!isVisibleRef.current) setIsVisible(true);
          return;
        }

        // Bottom bounce guard
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        if (latest >= maxScroll - 5) return;

        // Direction
        if (delta > 6 && latest > 100) {
          if (isVisibleRef.current) setIsVisible(false);
        } else if (delta < -4) {
          if (!isVisibleRef.current) setIsVisible(true);
        }
      });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll when mobile menu is active
  useEffect(() => {
    document.body.style.overflow = mobileMenuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileMenuOpen]);

  const handleProtectedRouting = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, item: NavItem) => {
      if (item.isProtected && status === "unauthenticated") {
        e.preventDefault();
        router.push(`/login?callbackUrl=${encodeURIComponent(item.href)}`);
      }
      if (mobileMenuOpen) setMobileMenuOpen(false);
    },
    [status, router, mobileMenuOpen]
  );

  return (
    <>
      {/*
        KEY PERF DECISIONS:
        - Single CSS transition on the wrapper instead of framer animate for hide/show
        - Single backdrop-blur layer (the nav pill) instead of 4 separate ones
        - Removed will-change-transform from static containers
        - Removed duplicate logo image used for blur glow effect
      */}
      <header
        className="fixed top-0 left-0 right-0 z-50 h-24 pointer-events-none transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]"
        style={{ transform: isVisible ? "translateY(0)" : "translateY(-120px)" }}
      >
        <div className="container mx-auto px-6 h-full flex justify-between items-center relative">

          {/* Logo Node — fog via CSS class, no motion wrapper */}
          <div
            className={`pointer-events-auto transition-all duration-300 rounded-full px-3 py-1 border ${
              isScrolled
                ? "bg-black/75 backdrop-blur-xl border-white/8"
                : "bg-transparent border-transparent"
            }`}
          >
            <Link href="/" prefetch={true} className="flex items-center gap-2">
              <Image
                src="/logo.png"
                alt="airdeliver logo"
                width={150}
                height={28}
                priority
                sizes="(max-width: 768px) 120px, 150px"
                className="h-7 w-auto object-contain transition-opacity duration-300 hover:opacity-80"
              />
            </Link>
          </div>

          {/* Desktop Navigation — single backdrop-blur pill */}
          <nav
            className={`hidden md:flex items-center rounded-full p-1.5 absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto transition-all duration-300 ${
              isScrolled
                ? "bg-black/75 backdrop-blur-xl border border-white/8 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.5)]"
                : "bg-transparent border-transparent"
            }`}
          >
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch={true}
                  onClick={(e) => handleProtectedRouting(e, item)}
                  className={`relative px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest transition-colors duration-200 ${
                    isActive ? "text-black" : "text-gray-400 hover:text-white"
                  }`}
                >
                  <span className="relative z-10">{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="active-pill"
                      className="absolute inset-0 bg-white shadow-[0_0_20px_rgba(255,255,255,0.4)]"
                      style={{ borderRadius: 9999 }}
                      transition={{ type: "spring", stiffness: 400, damping: 35 }}
                    />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Utility Actions — single fog wrapper */}
          <div
            className={`hidden md:flex items-center gap-1 rounded-full p-1.5 pointer-events-auto transition-all duration-300 ${
              isScrolled
                ? "bg-black/75 backdrop-blur-xl border border-white/8"
                : "bg-transparent border-transparent"
            }`}
          >
            <Link
              href="/notifications"
              className="relative p-3 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Notifications"
              onClick={(e) =>
                handleProtectedRouting(e, {
                  href: "/notifications",
                  label: "Notifications",
                  icon: Bell,
                  isProtected: true,
                })
              }
            >
              <Bell size={18} />
            </Link>
            <ThemeToggle />
          </div>

          {/* Mobile Trigger */}
          <div
            className={`md:hidden pointer-events-auto rounded-full transition-all duration-300 ${
              isScrolled ? "bg-black/80 backdrop-blur-xl" : "bg-transparent"
            }`}
          >
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-3 text-white hover:bg-white/10 rounded-full transition-colors"
              type="button"
              aria-label="Open navigation"
              aria-expanded={mobileMenuOpen}
            >
              <Menu size={24} />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Navigation Modal */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-2xl md:hidden"
          >
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: "0%" }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 40 }}
              className="absolute right-0 top-0 bottom-0 w-[85vw] max-w-sm bg-[#050505] border-l border-white/10 p-8 flex flex-col shadow-2xl"
            >
              <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                <Image
                  src="/logo.png"
                  alt="airdeliver logo"
                  width={120}
                  height={24}
                  className="h-6 w-auto object-contain"
                />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 text-gray-400 hover:text-white hover:rotate-90 transition-all duration-300"
                  type="button"
                  aria-label="Close navigation"
                >
                  <CloseIcon size={24} />
                </button>
              </div>

              <nav className="flex flex-col gap-3">
                {NAV_ITEMS.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      prefetch={true}
                      onClick={(e) => handleProtectedRouting(e, item)}
                      className={`flex items-center gap-4 p-5 rounded-2xl text-sm font-bold uppercase tracking-widest transition-colors ${
                        isActive
                          ? "bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)]"
                          : "text-gray-500 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <item.icon size={20} />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>

              <div className="mt-auto border-t border-white/5 pt-8">
                <div className="flex justify-center p-2">
                  <ThemeToggle />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
