// apps/web/components/layout/Header.tsx
"use client";

import React, { useState, useEffect, useCallback, memo, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { motion, AnimatePresence, useScroll, useMotionValueEvent } from "framer-motion";
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

const ANIMATION_VARIANTS = {
  fog: {
    transparent: {
      backgroundColor: "rgba(0, 0, 0, 0)",
      backdropFilter: "blur(0px)",
      WebkitBackdropFilter: "blur(0px)",
      borderColor: "rgba(255, 255, 255, 0.2)",
      boxShadow: "0 0 0px rgba(0,0,0,0)",
    },
    foggy: {
      backgroundColor: "rgba(5, 5, 5, 0.75)",
      backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      borderColor: "rgba(255, 255, 255, 0.08)",
      boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.5)",
    },
  },
  logoFog: {
    transparent: {
      backgroundColor: "rgba(0, 0, 0, 0)",
      backdropFilter: "blur(0px)",
      WebkitBackdropFilter: "blur(0px)",
      padding: "4px 12px",
      borderRadius: "9999px",
      border: "1px solid transparent",
    },
    foggy: {
      backgroundColor: "rgba(5, 5, 5, 0.75)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      padding: "4px 12px",
      borderRadius: "9999px",
      border: "1px solid rgba(255, 255, 255, 0.08)",
    },
  },
} as const;

// -----------------------------------------------------------------------------
// Pure Sub-Components (Strict Render Isolation)
// -----------------------------------------------------------------------------

const ThemeToggle = memo(function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div 
        className="w-10 h-10 rounded-full bg-white/5 animate-pulse" 
        aria-hidden="true" 
      />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors group contain-layout"
      aria-label="Toggle system theme layer"
      type="button"
    >
      <div className="absolute inset-0 bg-white/5 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" style={{ willChange: "opacity" }} />
      <AnimatePresence initial={false} mode="wait">
        <motion.div
          key={isDark ? "moon" : "sun"}
          initial={{ y: -20, opacity: 0, rotate: -90 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: 20, opacity: 0, rotate: 90 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          style={{ transformOrigin: "center" }}
        >
          {isDark ? (
            <Moon
              size={18}
              className="text-gray-200 drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]"
            />
          ) : (
            <Sun
              size={18}
              className="text-gray-200 drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]"
            />
          )}
        </motion.div>
      </AnimatePresence>
    </button>
  );
});

const DesktopNavLink = memo(function DesktopNavLink({ 
  item, 
  isActive, 
  onClick 
}: { 
  item: NavItem; 
  isActive: boolean; 
  onClick: (e: React.MouseEvent<HTMLAnchorElement>, item: NavItem) => void;
}) {
  return (
    <Link
      href={item.href}
      prefetch={true}
      onClick={(e) => onClick(e, item)}
      className={`relative px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest transition-colors duration-300 ${
        isActive ? "text-black" : "text-gray-400 hover:text-white"
      }`}
    >
      <span className="relative z-10">{item.label}</span>
      {isActive && (
        <motion.div
          layoutId="active-pill"
          className="absolute inset-0 bg-white shadow-[0_0_25px_rgba(255,255,255,0.5)]"
          style={{ borderRadius: 9999 }}
          transition={{ type: "spring", stiffness: 400, damping: 35 }}
        />
      )}
    </Link>
  );
});

const MobileNavLink = memo(function MobileNavLink({
  item,
  isActive,
  onClick
}: {
  item: NavItem;
  isActive: boolean;
  onClick: (e: React.MouseEvent<HTMLAnchorElement>, item: NavItem) => void;
}) {
  return (
    <Link
      href={item.href}
      prefetch={true}
      onClick={(e) => onClick(e, item)}
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
});

// -----------------------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------------------

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();

  // Core UI State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // React State for visual tree
  const [isScrolled, setIsScrolled] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  // Performance Telemetry Engine (Ref-based Accumulator)
  const { scrollY } = useScroll();
  const scrollAccumulator = useRef(0);
  const lastScrollY = useRef(0);

  useMotionValueEvent(scrollY, "change", (latest) => {
    // 1. Fog State (Strict equality check to prevent thrashing)
    const shouldBeScrolled = latest > 20;
    if (shouldBeScrolled !== isScrolled) {
      setIsScrolled(shouldBeScrolled);
    }

    // 2. Absolute Top Boundary (Bounce protection)
    if (latest <= 50) {
      if (!isVisible) setIsVisible(true);
      scrollAccumulator.current = 0;
      lastScrollY.current = latest;
      return;
    }

    // 3. Scroll Intent Accumulator Engine
    const delta = latest - lastScrollY.current;
    lastScrollY.current = latest;

    // Reset accumulator when user reverses direction
    if ((delta > 0 && scrollAccumulator.current < 0) || (delta < 0 && scrollAccumulator.current > 0)) {
      scrollAccumulator.current = 0;
    }
    
    scrollAccumulator.current += delta;

    // 4. Asymmetrical State Mutations (Instant Up, Intentional Down)
    if (scrollAccumulator.current > 60) {
      // Intent: Scrolling down definitively -> Hide
      if (isVisible) setIsVisible(false);
    } else if (scrollAccumulator.current < -2) {
      // Intent: Scrolling up instantly -> Show (Ultra-responsive micro-buffer)
      if (!isVisible) setIsVisible(true);
    }
  });

  // Lock body scroll when mobile menu is active
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [mobileMenuOpen]);

  const handleProtectedRouting = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, item: NavItem) => {
      if (item.isProtected && status === "unauthenticated") {
        e.preventDefault();
        const targetUrl = `/login?callbackUrl=${encodeURIComponent(item.href)}`;
        router.push(targetUrl);
      }
      if (mobileMenuOpen) setMobileMenuOpen(false);
    },
    [status, router, mobileMenuOpen]
  );

  // Primitive Cache: Prevent object recreation in the render loop for motion components
  const activeFogVariant = isScrolled ? "foggy" : "rgba(0, 0, 0, 0)";

  return (
    <>
      <motion.header
        initial={{ y: 0 }}
        animate={{ y: isVisible ? 0 : -100 }} // Reduced travel distance for faster perceived arrival
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }} // Native iOS spring-like bezier physics
        className="fixed top-0 left-0 right-0 z-50 h-24 pointer-events-none"
        style={{ willChange: "transform" }}
      >
        <div className="container mx-auto px-6 h-full flex justify-between items-center relative">
          
          {/* Logo Node */}
          <motion.div
            className="pointer-events-auto"
            style={{ willChange: "transform, filter, backdrop-filter" }}
            initial="rgba(0, 0, 0, 0)"
            animate={activeFogVariant}
            variants={ANIMATION_VARIANTS.logoFog}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            <Link
              href="/"
              prefetch={true}
              className="group flex items-center gap-2 relative z-10"
            >
              <div className="relative flex items-center mb-1">
                <Image
                  src="/logo.png"
                  alt="airdeliver logo"
                  width={150}
                  height={28}
                  priority
                  sizes="(max-width: 768px) 120px, 150px"
                  className="h-7 w-auto object-contain transition-opacity duration-500 group-hover:opacity-80 drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)]"
                  style={{ height: "auto" }}
                  style={{ height: "auto" }}
                />
                <Image
                  src="/logo.png"
                  alt=""
                  width={150}
                  height={28}
                  sizes="(max-width: 768px) 120px, 150px"
                  className="absolute top-0 left-0 h-7 w-auto object-contain opacity-0 group-hover:opacity-40 blur-md transition-opacity duration-300 pointer-events-none"
                  style={{ height: "auto" }}
                  style={{ height: "auto" }}
                  aria-hidden="true"
                />
              </div>
            </Link>
          </motion.div>

          {/* Desktop Navigation Node */}
          <motion.nav
            className="hidden md:flex items-center rounded-full p-1.5 absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto"
            style={{ willChange: "transform, filter, backdrop-filter" }}
            initial="rgba(0, 0, 0, 0)"
            animate={activeFogVariant}
            variants={ANIMATION_VARIANTS.fog}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            {NAV_ITEMS.map((item) => (
              <DesktopNavLink 
                key={item.href}
                item={item}
                isActive={pathname === item.href}
                onClick={handleProtectedRouting}
              />
            ))}
          </motion.nav>

          {/* Utility Action Node */}
          <div className="hidden md:flex items-center gap-1 relative z-10 pointer-events-auto">
            <motion.div
              className="flex items-center gap-1 rounded-full p-1.5"
              style={{ willChange: "transform, filter, backdrop-filter" }}
              initial="rgba(0, 0, 0, 0)"
              animate={activeFogVariant}
              variants={ANIMATION_VARIANTS.fog}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              <Link
                href="/notifications"
                className="relative p-3 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="System Notifications"
                onClick={(e) => handleProtectedRouting(e, { href: '/notifications', label: 'Notifications', icon: Bell, isProtected: true })}
              >
                <Bell size={18} />
              </Link>
            </motion.div>

            <motion.div
              className="rounded-full p-1"
              style={{ willChange: "transform, filter, backdrop-filter" }}
              initial="rgba(0, 0, 0, 0)"
              animate={activeFogVariant}
              variants={ANIMATION_VARIANTS.fog}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              <ThemeToggle />
            </motion.div>
          </div>

          {/* Mobile Navigation Trigger Node */}
          <motion.div
            className="md:hidden relative z-10 pointer-events-auto rounded-full"
            style={{ willChange: "transform, filter, backdrop-filter" }}
            animate={
              isScrolled
                ? { backgroundColor: "rgba(5,5,5,0.8)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }
                : { backgroundColor: "rgba(0, 0, 0, 0)", backdropFilter: "blur(0px)", WebkitBackdropFilter: "blur(0px)" }
            }
            transition={{ duration: 0.3 }}
          >
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-3 text-white hover:bg-white/10 rounded-full transition-colors"
              type="button"
              aria-label="Initialize navigation sequence"
              aria-expanded={mobileMenuOpen}
            >
              <Menu size={24} />
            </button>
          </motion.div>
        </div>
      </motion.header>

      {/* Mobile Navigation Modal Layer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-2xl md:hidden"
            style={{ willChange: "opacity" }}
          >
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: "0%" }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 40 }}
              className="absolute right-0 top-0 bottom-0 w-[85vw] max-w-sm bg-[#050505] border-l border-white/10 p-8 flex flex-col shadow-2xl"
              style={{ willChange: "transform" }}
            >
              <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                <Image
                  src="/logo.png"
                  alt="airdeliver core logo"
                  width={120}
                  height={24}
                  className="h-6 w-auto object-contain"
                  style={{ height: "auto" }}
                  style={{ height: "auto" }}
                />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 text-gray-400 hover:text-white hover:rotate-90 transition-all duration-300"
                  type="button"
                  aria-label="Terminate navigation sequence"
                >
                  <CloseIcon size={24} />
                </button>
              </div>

              <nav className="flex flex-col gap-3">
                {NAV_ITEMS.map((item) => (
                  <MobileNavLink 
                    key={item.href}
                    item={item}
                    isActive={pathname === item.href}
                    onClick={handleProtectedRouting}
                  />
                ))}
              </nav>

              <div className="mt-auto space-y-4 border-t border-white/5 pt-8">
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
