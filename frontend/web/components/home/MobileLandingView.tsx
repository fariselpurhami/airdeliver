'use client';

import React, { memo, useEffect, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Zap, ArrowDown } from 'lucide-react';
import { usePWAInstall } from '@/hooks/usePWAInstall';
import { IOSInstallPrompt } from '@/components/pwa/IOSInstallPrompt';

// --- Constants ---
const THEME = {
  fonts: {
    sans: "'Montserrat', sans-serif",
    display: "'Orbitron', sans-serif",
  },
  scrollThreshold: 10,
} as const;

// --- Hooks ---
/**
 * Handles scroll-based header visibility using direct DOM mutation.
 * Bypasses React state to ensure 60fps performance without re-renders.
 */
const useHeaderScroll = (headerRef: React.RefObject<HTMLElement | null>) => {
  useEffect(() => {
    let rafId: number;
    const handleScroll = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        if (!headerRef.current) return;
        
        const isScrolled = window.scrollY > THEME.scrollThreshold;
        const stringScrolled = String(isScrolled);

        if (headerRef.current.dataset.scrolled !== stringScrolled) {
          headerRef.current.dataset.scrolled = stringScrolled;
        }
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    // Initial check
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      cancelAnimationFrame(rafId);
    };
  }, [headerRef]);
};

// --- Sub-components ---

/**
 * Injects global CSS overrides to aggressively hide conflicting UI elements 
 * (chatbots, floating navs) ensuring the mobile landing view remains pristine.
 */
const GlobalStyleOverride = memo(() => {
  useEffect(() => {
    const styleId = 'mobile-override-styles';
    
    // Prevent duplicate injections during strict mode or fast refresh
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.innerHTML = `
      /* Hide default layout header */
      header:not(#custom-mobile-header) { 
        display: none !important; 
      }
      
      /* Aggressively hide fixed bottom navs, bots, and chat widgets */
      div[class*="fixed"][class*="bottom-"]:not(#ios-install-prompt):not(#ios-install-prompt *),
      button[class*="fixed"][class*="bottom-"],
      div[class*="chat" i], button[class*="chat" i],
      div[class*="bot" i], button[class*="bot" i] {
        display: none !important;
        opacity: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
      }
    `;
    document.head.appendChild(style);

    return () => {
      document.getElementById(styleId)?.remove();
    };
  }, []);

  return null;
});
GlobalStyleOverride.displayName = 'GlobalStyleOverride';

const MobileHeader = memo(({ headerRef }: { headerRef: React.RefObject<HTMLElement | null> }) => (
  <header
    id="custom-mobile-header"
    ref={headerRef}
    data-scrolled="false"
    className="fixed top-0 left-0 right-0 z-50 h-24 transition-all duration-[50ms] ease-[cubic-bezier(0.16,1,0.3,1)] data-[scrolled=true]:-translate-y-[100px] data-[scrolled=true]:opacity-0 data-[scrolled=true]:pointer-events-none transform-gpu will-change-transform"
  >
    <div className="container mx-auto px-6 h-full flex justify-between items-center relative">
      <div className="pointer-events-auto px-3 py-1">
        <Link
          href="/"
          aria-label="Return to homepage"
          className="group flex items-center gap-2 relative z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-black rounded-sm block"
        >
          <div className="relative flex items-center mb-1">
            <Image
              src="/logo.png"
              alt="airdeliver logo"
              width={120}
              height={22}
              priority
              className="object-contain transition-opacity duration-500 group-hover:opacity-80 drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)] transform-gpu"
            />
            {/* Glow effect duplicate */}
            <Image
              src="/logo.png"
              alt=""
              width={120}
              height={22}
              priority
              decoding="async"
              aria-hidden="true"
              className="absolute top-0 left-0 object-contain opacity-0 group-hover:opacity-40 blur-md transition-opacity duration-300 transform-gpu will-change-opacity"
            />
          </div>
        </Link>
      </div>
    </div>
  </header>
));
MobileHeader.displayName = 'MobileHeader';

const HeroBackground = memo(() => (
  <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
    <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20" />
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[100px] will-change-transform translate-z-0" />
  </div>
));
HeroBackground.displayName = 'HeroBackground';

const HeroContent = memo(({ onDownload }: { onDownload: () => void }) => (
  <div className="container mx-auto px-6 relative z-10 text-center">
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 30 }}
      whileInView={{ opacity: 1, scale: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      style={{ willChange: "transform, opacity" }}
      className="max-w-5xl mx-auto transform-gpu"
    >
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-950/30 border border-cyan-500/30 backdrop-blur-md mb-8 ring-1 ring-cyan-500/20">
        <Zap size={14} className="text-yellow-400 fill-yellow-400" aria-hidden="true" />
        <span className="text-xs font-mono text-cyan-300 uppercase tracking-widest">Next-Gen Shopping Experience</span>
      </div>

      <h2 className="text-5xl md:text-8xl font-black text-white mb-8 tracking-tighter leading-[0.9]" style={{ fontFamily: THEME.fonts.display }}>
        YOUR ORDER.<br />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-purple-400 drop-shadow-[0_0_40px_rgba(192,132,252,0.5)]">
          IN THE SKY.
        </span>
      </h2>

      <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto mb-12 font-light leading-relaxed">
        Don&apos;t wait for traffic. Shop thousands of products and watch them arrive from the clouds in minutes.
      </p>

      <div className="flex flex-col gap-6 justify-center items-center">
        <button 
          onClick={onDownload}
          className="group px-12 py-7 text-white font-bold text-xl rounded-full border border-white/10 hover:bg-white/5 hover:border-cyan-400/50 transition-all duration-300 flex items-center gap-3 transform-gpu focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-black"
        >
          <span>DOWNLOAD APP</span>
          <ArrowDown className="w-6 h-6 group-hover:translate-y-1 transition-transform" aria-hidden="true" />
        </button>
      </div>
      
      <p className="mt-12 text-[10px] text-gray-600 font-mono uppercase tracking-[0.2em]">
        Instant Delivery &bull; Live Tracking &bull; 100% Autonomous
      </p>
    </motion.div>
  </div>
));
HeroContent.displayName = 'HeroContent';

// --- Main Component ---

export const MobileLandingView = memo(() => {
  const { triggerInstall, isIOSPromptVisible, setIOSPromptVisible } = usePWAInstall();
  const headerRef = useRef<HTMLElement>(null);

  useHeaderScroll(headerRef);

  return (
    <div 
      id="mobile-landing-root" 
      className="min-h-[100dvh] w-full text-gray-100 overflow-hidden bg-black flex flex-col" 
      style={{ fontFamily: THEME.fonts.sans }}
    >
      <GlobalStyleOverride />
      <MobileHeader headerRef={headerRef} />

      <main className="relative z-10 w-full flex-1 flex flex-col justify-center pt-24 pb-10">
        <section className="relative w-full min-h-[100dvh] py-32 overflow-hidden bg-black flex items-center justify-center border-t border-white/5">
          <HeroBackground />
          <HeroContent onDownload={triggerInstall} />
        </section>
      </main>

      <IOSInstallPrompt 
        isOpen={isIOSPromptVisible} 
        onClose={() => setIOSPromptVisible(false)} 
      />
    </div>
  );
});
MobileLandingView.displayName = 'MobileLandingView';
