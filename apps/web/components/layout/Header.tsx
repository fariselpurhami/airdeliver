"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  Sparkles,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/products", label: "Products", icon: Package },
  { href: "/profile", label: "Profile", icon: User },
];

const ThemeToggle = () => {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className="w-10 h-10 rounded-full bg-white/5 animate-pulse" />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors group"
      aria-label="Toggle theme"
      type="button"
    >
      <div className="absolute inset-0 bg-white/5 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
      <AnimatePresence initial={false} mode="wait">
        <motion.div
          key={isDark ? "moon" : "sun"}
          initial={{ y: -20, opacity: 0, rotate: -90 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: 20, opacity: 0, rotate: 90 }}
          transition={{ duration: 0.2 }}
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
};

export default function Header() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    setIsMounted(true);

    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const fogVariants = {
    transparent: {
      backgroundColor: "rgba(0, 0, 0, 0)",
      backdropFilter: "blur(0px)",
      borderColor: "rgba(255, 255, 255, 0.2)",
      boxShadow: "0 0 0px rgba(0,0,0,0)",
    },
    foggy: {
      backgroundColor: "rgba(3, 3, 3, 0.75)",
      backdropFilter: "blur(16px)",
      borderColor: "rgba(255, 255, 255, 0.08)",
      boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.5)",
    },
  };

  const logoFogVariants = {
    transparent: {
      backgroundColor: "rgba(0, 0, 0, 0)",
      backdropFilter: "blur(0px)",
      padding: "4px 12px",
      borderRadius: "9999px",
      border: "1px solid transparent",
    },
    foggy: {
      backgroundColor: "rgba(3, 3, 3, 0.75)",
      backdropFilter: "blur(12px)",
      padding: "4px 12px",
      borderRadius: "9999px",
      border: "1px solid rgba(255, 255, 255, 0.08)",
    },
  };

  if (!isMounted) {
    return <header className="fixed top-0 left-0 right-0 z-50 h-24 bg-black" />;
  }

  return (
    <>
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="fixed top-0 left-0 right-0 z-50 h-24 pointer-events-none"
      >
        <div className="container mx-auto px-6 h-full flex justify-between items-center relative">
          <motion.div
            className="pointer-events-auto"
            initial="transparent"
            animate={isScrolled ? "foggy" : "transparent"}
            variants={logoFogVariants}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          >
            <Link
              href="/"
              prefetch={true}
              className="group flex items-center gap-2 relative z-10"
            >
              <div className="relative">
                <span
                  className="text-2xl font-bold text-white tracking-tighter transition-colors duration-500 group-hover:text-gray-200 drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)]"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  airdeliver
                </span>
                <span
                  className="absolute top-0 left-0 text-2xl font-bold text-white opacity-0 group-hover:opacity-40 blur-md transition-opacity duration-300"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  airdeliver
                </span>
              </div>
            </Link>
          </motion.div>

          <motion.nav
            className="hidden md:flex items-center rounded-full p-1.5 absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto"
            initial="transparent"
            animate={isScrolled ? "foggy" : "transparent"}
            variants={fogVariants}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          >
            {navItems.map((item) => {
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch={true}
                  className={`relative px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all duration-300 ${
                    isActive ? "text-black" : "text-gray-400 hover:text-white"
                  }`}
                >
                  <span className="relative z-10">{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="active-pill"
                      className="absolute inset-0 bg-white shadow-[0_0_25px_rgba(255,255,255,0.5)]"
                      style={{ borderRadius: 9999 }}
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                </Link>
              );
            })}
          </motion.nav>

          <div className="hidden md:flex items-center gap-1 relative z-10 pointer-events-auto">
            <motion.div
              className="flex items-center gap-1 rounded-full p-1.5"
              initial="transparent"
              animate={isScrolled ? "foggy" : "transparent"}
              variants={fogVariants}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            >
              <Link
                href="/notifications"
                className="relative p-3 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-all"
                aria-label="Notifications"
              >
                <Bell size={18} />
              </Link>
            </motion.div>

            <motion.div
              className="rounded-full p-1"
              initial="transparent"
              animate={isScrolled ? "foggy" : "transparent"}
              variants={fogVariants}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            >
              <ThemeToggle />
            </motion.div>
          </div>

          <motion.div
            className="md:hidden relative z-10 pointer-events-auto rounded-full"
            animate={
              isScrolled
                ? { backgroundColor: "rgba(3,3,3,0.8)", backdropFilter: "blur(12px)" }
                : { backgroundColor: "transparent" }
            }
          >
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-3 text-white hover:bg-white/10 rounded-full transition-colors"
              type="button"
              aria-label="Open navigation menu"
            >
              <Menu size={24} />
            </button>
          </motion.div>
        </div>
      </motion.header>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-2xl md:hidden"
          >
            <motion.div
              initial={{ x: 100 }}
              animate={{ x: 0 }}
              exit={{ x: 100 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="absolute right-0 top-0 bottom-0 w-[85vw] max-w-sm bg-[#050505] border-l border-white/10 p-8 flex flex-col shadow-2xl"
            >
              <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                <span
                  className="text-xl font-bold text-white tracking-wider"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  airdeliver
                </span>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 text-gray-400 hover:text-white hover:rotate-90 transition-all duration-300"
                  type="button"
                  aria-label="Close navigation menu"
                >
                  <CloseIcon size={24} />
                </button>
              </div>

              <nav className="flex flex-col gap-3">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    prefetch={true}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-4 p-5 rounded-2xl text-sm font-bold uppercase tracking-widest transition-all ${
                      pathname === item.href
                        ? "bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)]"
                        : "text-gray-500 hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <item.icon size={20} />
                    {item.label}
                  </Link>
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
