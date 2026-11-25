/* frontend/web/components/layout/Header.tsx */

"use client";

import React, { useEffect, useCallback, useRef, useState, useId } from "react";
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

  const [navigationOpen, setNavigationOpen] = useState(false);
  const navigationRef = useRef<HTMLDivElement>(null);
  const navigationId = useId();
  useEffect(() => { setNavigationOpen(false); }, [pathname]);
  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (!navigationRef.current?.contains(event.target as Node)) setNavigationOpen(false);
    };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, []);

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
                  className="max-[360px]:w-[96px] object-contain transition-opacity duration-500 group-hover:opacity-80 drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)] transform-gpu"
                />
                <Image
                  src="/logo.png"
                  alt=""
                  width={120}
                  height={22}
                  priority
                  decoding="async"
                  className="max-[360px]:w-[96px] absolute top-0 left-0 object-contain opacity-0 group-hover:opacity-40 blur-md transition-opacity duration-300 transform-gpu will-change-opacity"
                  aria-hidden="true"
                />
              </div>
            </Link>
          </div>

          <div
            ref={navigationRef}
            className="relative z-10 pointer-events-auto flex items-center gap-1 sm:gap-2"
            onPointerEnter={(event) => { if (event.pointerType === 'mouse') setNavigationOpen(true); }}
            onPointerLeave={(event) => { if (event.pointerType === 'mouse' && !navigationRef.current?.contains(document.activeElement)) setNavigationOpen(false); }}
            onFocus={(event) => { if (event.target.matches(':focus-visible')) setNavigationOpen(true); }}
            onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setNavigationOpen(false); }}
            onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); navigationRef.current?.querySelector('button')?.focus(); setNavigationOpen(false); } }}
          >
            <nav id={navigationId} aria-label="Main navigation" aria-hidden={!navigationOpen} inert={!navigationOpen}
              className={`grid transition-[grid-template-columns,opacity,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${navigationOpen ? 'grid-cols-[1fr] translate-x-0 opacity-100' : 'grid-cols-[0fr] translate-x-2 opacity-0 pointer-events-none'}`}>
              <div className="flex min-w-0 items-center gap-1 overflow-hidden sm:gap-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={`top-${item.href}`}
                  href={item.href}
                  prefetch={true}
                  onClick={(e) => { handleProtectedRouting(e, item); setNavigationOpen(false); }}
                  aria-label={item.label}
                  aria-current={isActive ? "page" : undefined}
                  className={`relative flex items-center justify-center w-10 h-10 max-[360px]:w-9 sm:w-11 sm:h-11 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                    isActive
                      ? "bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]"
                      : "text-zinc-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} aria-hidden="true" />
                </Link>
              );
            })}
              </div>
            </nav>
            <button type="button" aria-label="Toggle navigation" aria-expanded={navigationOpen} aria-controls={navigationId}
              onClick={() => setNavigationOpen(open => !open)}
              className="flex h-11 w-11 max-[360px]:w-10 shrink-0 flex-col items-end justify-center gap-[5px] rounded-full px-2.5 text-white/90 transition hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200 motion-reduce:transition-none">
              <span aria-hidden="true" className="h-[2px] w-6 rounded-full bg-current" />
              <span aria-hidden="true" className="h-[2px] w-4 rounded-full bg-current" />
              <span aria-hidden="true" className="h-[2px] w-2 rounded-full bg-current" />
            </button>
          </div>
        </div>
      </header>

      {/* Enterprise-Grade Floating Action Bar */}
      <nav
        ref={floatingBarRef}
        data-scrolled="false"
        aria-label="Quick navigation"
        className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/20 bg-gradient-to-b from-black/45 via-black/55 to-black/65 p-1 backdrop-blur-3xl backdrop-saturate-150 shadow-[0_14px_40px_rgba(0,0,0,0.55),inset_0_1px_1px_rgba(255,255,255,0.22),inset_0_-1px_1px_rgba(255,255,255,0.05)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] translate-y-[100px] opacity-0 scale-95 pointer-events-none data-[scrolled=true]:translate-y-0 data-[scrolled=true]:opacity-100 data-[scrolled=true]:scale-100 data-[scrolled=true]:pointer-events-auto transform-gpu will-change-transform"
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
              className={`relative flex items-center justify-center w-11 h-11 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                isActive
                  ? "bg-gradient-to-b from-white/20 to-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]"
                  : "text-zinc-400 hover:text-white hover:bg-white/10 active:scale-95"
              }`}
            >
              <item.icon size={19} strokeWidth={isActive ? 2.5 : 2} aria-hidden="true" />
            </Link>
          );
        })}
      </nav>
    </>
  );
}
