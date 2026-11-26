// ============================================================================
// FILE: frontend/web/app/(main)/_components/LandingClient.tsx
// ============================================================================
'use client';

import { randomId } from '@/lib/random-id';
import Image from "next/image";
import { FloatingHeroCards, HERO_STAGE_CLASSES } from '@/components/hero/FloatingHeroCards';
import { AISecuredOrdersBadge } from '@/components/hero/AISecuredOrdersBadge';
import Link from 'next/link';
import { AirSparkles } from '@/components/ui/AirSparkles';
import { TypewriterText } from '@/components/ui/TypewriterText';
import { PromptMediaIcons } from '@/components/ui/PromptMediaIcons';
import React, { 
  useRef, useMemo, useEffect, useReducer, memo, useId, Component, ErrorInfo, ReactNode 
} from 'react';
import { 
  motion, useScroll, useTransform, 
  useAnimation, useReducedMotion 
} from 'framer-motion';

// Monorepo Path Aliases
import { useDeviceDetection } from '@/hooks/usePWAInstall';
import { MobileLandingView } from '@/components/home/MobileLandingView';
import { useUIStore } from '@/hooks/useUIStore';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import ProductOverlay from '@/components/products/ProductOverlay';

// Lucide Icons
import { 
  MapIcon, Activity, Bot, ChevronRight, 
  Rocket, Zap, ArrowRight, Cpu, ArrowDown, Camera, ShieldCheck
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// ============================================================================
// --- [1] ZERO-DEPENDENCY BOUNDARY VALIDATION CONTRACT (Zod-Compatible) ---
// ============================================================================

export interface TrackingPayload {
  readonly traceId: string;
  readonly timestamp: number;
  readonly event: 'MOUNT' | 'INTERACTION' | 'ERROR';
  readonly metadata?: Record<string, unknown>;
}

export type ValidationResult<T> = 
  | { readonly success: true; readonly data: T }
  | { readonly success: false; readonly error: { readonly message: string } };

export const TrackingPayloadSchema = {
  safeParse: (input: unknown): ValidationResult<TrackingPayload> => {
    if (!input || typeof input !== 'object') {
      return { success: false, error: { message: 'Payload must be a non-null object' } };
    }
    const record = input as Record<string, unknown>;
    if (typeof record.traceId !== 'string' || record.traceId.trim().length === 0) {
      return { success: false, error: { message: 'traceId must be a valid string' } };
    }
    if (typeof record.timestamp !== 'number' || Number.isNaN(record.timestamp)) {
      return { success: false, error: { message: 'timestamp must be a valid number' } };
    }
    if (record.event !== 'MOUNT' && record.event !== 'INTERACTION' && record.event !== 'ERROR') {
      return { success: false, error: { message: 'event must be MOUNT, INTERACTION, or ERROR' } };
    }
    return {
      success: true,
      data: {
        traceId: record.traceId,
        timestamp: record.timestamp,
        event: record.event,
        metadata: typeof record.metadata === 'object' && record.metadata !== null 
          ? (record.metadata as Record<string, unknown>) 
          : undefined,
      }
    };
  }
};

// ============================================================================
// --- [2] DETERMINISTIC FSM (FINITE STATE MACHINE) ---
// ============================================================================

export type UIStatus = 'IDLE' | 'AI_OVERLAY_ACTIVE' | 'PRODUCT_OVERLAY_ACTIVE' | 'MOBILE_PWA_VIEW' | 'FATAL_ERROR';

export type UIAction =
  | { readonly type: 'OPEN_AI_CART'; readonly payload: { readonly traceId: string } }
  | { readonly type: 'OPEN_PRODUCTS'; readonly payload: { readonly traceId: string } }
  | { readonly type: 'CLOSE_OVERLAYS' }
  | { readonly type: 'FORCE_MOBILE_VIEW' }
  | { readonly type: 'REPORT_ERROR'; readonly payload: { readonly message: string } };

export interface UIState {
  readonly status: UIStatus;
  readonly activeTraceId?: string;
  readonly errorMessage?: string;
}

function uiFSMReducer(state: UIState, action: UIAction): UIState {
  switch (state.status) {
    case 'IDLE':
      switch (action.type) {
        case 'OPEN_AI_CART': return { status: 'AI_OVERLAY_ACTIVE', activeTraceId: action.payload.traceId };
        case 'OPEN_PRODUCTS': return { status: 'PRODUCT_OVERLAY_ACTIVE', activeTraceId: action.payload.traceId };
        case 'FORCE_MOBILE_VIEW': return { status: 'MOBILE_PWA_VIEW' };
        case 'REPORT_ERROR': return { status: 'FATAL_ERROR', errorMessage: action.payload.message };
        case 'CLOSE_OVERLAYS': return state;
        default: return state;
      }
    case 'AI_OVERLAY_ACTIVE':
      switch (action.type) {
        case 'CLOSE_OVERLAYS': return { status: 'IDLE' };
        case 'OPEN_PRODUCTS': return { status: 'PRODUCT_OVERLAY_ACTIVE', activeTraceId: action.payload.traceId };
        case 'FORCE_MOBILE_VIEW': return { status: 'MOBILE_PWA_VIEW' };
        case 'REPORT_ERROR': return { status: 'FATAL_ERROR', errorMessage: action.payload.message };
        default: return state;
      }
    case 'PRODUCT_OVERLAY_ACTIVE':
      switch (action.type) {
        case 'CLOSE_OVERLAYS': return { status: 'IDLE' };
        case 'OPEN_AI_CART': return { status: 'AI_OVERLAY_ACTIVE', activeTraceId: action.payload.traceId };
        case 'FORCE_MOBILE_VIEW': return { status: 'MOBILE_PWA_VIEW' };
        case 'REPORT_ERROR': return { status: 'FATAL_ERROR', errorMessage: action.payload.message };
        default: return state;
      }
    case 'MOBILE_PWA_VIEW':
      if (action.type === 'REPORT_ERROR') return { status: 'FATAL_ERROR', errorMessage: action.payload.message };
      return state;
    case 'FATAL_ERROR':
      return state; 
    default:
      return state;
  }
}

// ============================================================================
// --- [3] RUM OBSERVABILITY ERROR BOUNDARY ---
// ============================================================================

interface ErrorBoundaryProps {
  readonly children: ReactNode;
  readonly fallback: ReactNode;
  readonly traceId: string;
}

interface ErrorBoundaryState {
  readonly hasError: boolean;
}

class RUMErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) { 
    super(props); 
    this.state = { hasError: false }; 
  }

  static getDerivedStateFromError(): ErrorBoundaryState { 
    return { hasError: true }; 
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const errorPayload = {
      traceId: this.props.traceId,
      timestamp: Date.now(),
      event: 'ERROR' as const,
      metadata: {
        message: error.message.slice(0, 256),
        stack: error.stack ? error.stack.slice(0, 1024) : undefined,
        componentStack: errorInfo.componentStack ? errorInfo.componentStack.slice(0, 1024) : undefined
      }
    };
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('/api/telemetry/rum', JSON.stringify(errorPayload));
    }
  }

  override render() { 
    return this.state.hasError ? this.props.fallback : this.props.children; 
  }
}

// ============================================================================
// --- [4] CONFIGURATIONS & ASSETS ---
// ============================================================================

const TRANSITION_PREMIUM: [number, number, number, number] = [0.16, 1, 0.3, 1];
const fadeUpVariant = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: TRANSITION_PREMIUM } }
};

interface HeroFloatingCardProps {
  readonly title: string; 
  readonly image: string; 
  readonly category: string; 
  readonly delay: number;
  readonly positionClasses: string; 
  readonly sizeClasses: string;
  readonly colorCls: string;
  readonly rotation: number;
}

// Colors Restored for visual hierarchy!
const HERO_CARDS: ReadonlyArray<HeroFloatingCardProps> = [
  { title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[1%] left-[16%] lg:top-[10%] lg:left-[5%]", sizeClasses: "w-21 h-29 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/30 text-grey" },
  { title: "PS5", category: "Wearables", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[1%] right-[16%] lg:top-[10%] lg:right-[5%]", sizeClasses: "w-21 h-29 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/30 text-grey" },
  { title: "Dyson", category: "Aesthetic", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -left-[4%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/30 text-grey" },
  { title: "Headphones", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -right-[3%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/30 text-grey" },
  { title: "Leather Handbag", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] left-[2%] lg:bottom-[25%] lg:left-[8%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/30 text-grey" },
  { title: "Iphone 17 pro max", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] right-[1%] lg:bottom-[25%] lg:right-[8%]", sizeClasses: "w-22 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/30 text-grey" },
  { title: "Nike Air Max", category: "Fashion", delay: 0.7, rotation: -5, image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] left-[20%] lg:bottom-[5%] lg:left-[25%]", sizeClasses: "w-20 h-28 lg:w-48 lg:h-48", colorCls: "hover:shadow-red-500/30 text-grey" },
  { title: "Galaxy Buds", category: "Neural Tech", delay: 0.8, rotation: 7, image: "https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] right-[20%] lg:bottom-[5%] lg:right-[25%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-cyan-500/30 text-grey" }
];

const PRODUCTION_STEPS = [
  { icon: Bot, step: "01", title: "AI Intent Recognition", description: "Simply type or speak your order. Our neural engine parses your intent instantly, finding the exact product across our partner stores' inventory without you scrolling through catalogs." },
  { icon: Cpu, step: "02", title: "Inventory Sync", description: "Within milliseconds, the system queries local hubs and databases to secure the best price and immediate availability, reserving your item autonomously." },
  { icon: Camera, step: "03", title: "Multimodal Visual Matching", description: "Upload a image or screenshot. Our computer vision models analyze texture, brand, and style to match real-world items in seconds." },
  { icon: ShieldCheck, step: "04", title: "Autonomous One-Tap Checkout", description: "Review your personalized bag preview and complete your purchase securely with one-tap encrypted payment flow directly within the overlay." },
] as const;

// ============================================================================
// --- [5] HIGH-PERFORMANCE 2D CANVAS (COSMIC NEBULA & STARFIELD ENGINE) ---
// ============================================================================

interface StarParticle {
  x: number;
  y: number;
  size: number;
  vx: number;
  vy: number;
  alpha: number;
  da: number;
  colorRgb: string;
  isBright: boolean;
}

const STAR_PALETTE = [
  '255, 255, 255', // Pure crisp white
  '255, 255, 255', // Pure crisp white (weighted higher)
  '207, 250, 254', // Soft cyan-white tint
  '233, 213, 255', // Soft lavender-purple tint
  '165, 243, 252', // Cosmic teal-cyan highlight
] as const;

const CosmicDustCanvas = memo(() => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const orderingOpen = useAIOrderingStore(state => state.isOverlayVisible);

  useEffect(() => {
    if (orderingOpen) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
    if (!ctx) return;

    let animationFrameId = 0;
    let isVisible = true;
    let isTabActive = !document.hidden;
    let width = 0;
    let height = 0;
    let particles: StarParticle[] = [];

    const initParticles = (w: number, h: number) => {
      // Dense starfield matching the reference image while capping max count for 60fps guarantee
      const rawCount = Math.floor((w * h) / 1);
      const count = Math.min(Math.max(rawCount, 10000), 10000);
      const nextParticles: StarParticle[] = new Array(count);

      for (let i = 0; i < count; i++) {
        const rand = Math.random();
        const isBright = rand > 0.95;
        const size = isBright
          ? Math.random() * 0.3 + 0.3
          : Math.random() * 0.4 + 0.4;

        nextParticles[i] = {
          x: Math.random() * w,
          y: Math.random() * h,
          size,
          vx: (Math.random() - 0.5) * 0.05,
          vy: (Math.random() - 0.5) * 0.05,
          alpha: isBright ? Math.random() * 0.35 + 0.45 : Math.random() * 0.65 + 0.15,
          da: (Math.random() * 0.012 + 0.003) * (Math.random() > 0.5 ? 1 : -1),
          colorRgb: STAR_PALETTE[i % STAR_PALETTE.length] ?? '#ffffff',
          isBright,
        };
      }
      particles = nextParticles;
    };

    const renderFrame = (animate: boolean) => {
      ctx.clearRect(0, 0, width, height);

      const len = particles.length;
      for (let i = 0; i < len; i++) {
        const p = particles[i];
        if (!p) continue;

        if (animate) {
          p.x += p.vx;
          p.y += p.vy;
          p.alpha += p.da;

          if (p.alpha <= 0.12) {
            p.alpha = 0.12;
            p.da = -p.da;
          } else if (p.alpha >= 0.98) {
            p.alpha = 0.98;
            p.da = -p.da;
          }

          if (p.x < 0) p.x = width;
          else if (p.x > width) p.x = 0;
          if (p.y < 0) p.y = height;
          else if (p.y > height) p.y = 0;
        }

        ctx.fillStyle = `rgba(${p.colorRgb}, ${p.alpha.toFixed(2)})`;

        // Fast sub-pixel / micro-star rendering via fillRect; smooth circles for brighter stars
        if (!p.isBright) {
          ctx.fillRect(p.x, p.y, p.size, p.size);
        } else {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * 0.75, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    const stopLoop = () => {
      if (animationFrameId !== 0) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = 0;
      }
    };

    const tick = () => {
      if (!isVisible || !isTabActive || prefersReducedMotion) {
        animationFrameId = 0;
        return;
      }
      renderFrame(true);
      animationFrameId = requestAnimationFrame(tick);
    };

    const startLoop = () => {
      if (prefersReducedMotion) {
        renderFrame(false);
        return;
      }
      if (animationFrameId === 0 && isVisible && isTabActive) {
        animationFrameId = requestAnimationFrame(tick);
      }
    };

    const updateDimensions = () => {
      const rect = container.getBoundingClientRect();
      const nextW = Math.max(1, Math.floor(rect.width || window.innerWidth));
      const nextH = Math.max(1, Math.floor(rect.height || window.innerHeight));
      if (nextW === width && nextH === height) return;

      width = nextW;
      height = nextH;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      initParticles(width, height);
      renderFrame(false);
    };

    updateDimensions();
    startLoop();

    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });
    resizeObserver.observe(container);

    const intersectionObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        isVisible = Boolean(entry?.isIntersecting);
        if (isVisible) {
          startLoop();
        } else {
          stopLoop();
        }
      },
      { threshold: 0.01 }
    );
    intersectionObserver.observe(container);

    const handleVisibilityChange = () => {
      isTabActive = !document.hidden;
      if (isTabActive) {
        startLoop();
      } else {
        stopLoop();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopLoop();
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [prefersReducedMotion, orderingOpen]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 z-0 pointer-events-none overflow-hidden bg-[#04060A]"
      style={{ contain: 'strict' }}
      aria-hidden="true"
    >
      {/* Multi-layered Cosmic Teal & Deep Violet/Purple Nebula matching reference image */}
      <div
        className="absolute inset-0 transform-gpu"
        style={{
          background: [
            'radial-gradient(ellipse 85% 60% at 18% 18%, rgba(13, 148, 136, 0.15) 0%, rgba(6, 182, 212, 0.05) 42%, transparent 75%)',
      // تقليل الشفافية من 0.30 لـ 0.15 ومن 0.16 لـ 0.06
            'radial-gradient(ellipse 80% 65% at 78% 58%, rgba(126, 34, 206, 0.15) 0%, rgba(109, 40, 217, 0.06) 45%, transparent 78%)',
      // تقليل الشفافية من 0.25 لـ 0.12 ومن 0.12 لـ 0.05
            'radial-gradient(ellipse 75% 55% at 50% 82%, rgba(88, 28, 135, 0.12) 0%, rgba(49, 46, 129, 0.05) 50%, transparent 80%)',
      // تغميق ألوان القاعدة الأساسية لتكون أقرب للأسود
            'linear-gradient(165deg, #030d12 0%, #03050a 42%, #080412 78%, #020203 100%)'
          ].join(', ')
        }}
      />

      {/* Crisp Dense Starfield Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full transform-gpu"
        style={{ mixBlendMode: 'screen' }}
      />

      {/* Subtle Edge Vignette for Depth & Seamless Bottom Transition */}
      
    </div>
  );
});
CosmicDustCanvas.displayName = 'CosmicDustCanvas';

// ============================================================================
// --- [6] UI COMPONENTS (CARDS) ---
// ============================================================================

const HeroFloatingCard = memo(({ title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation }: HeroFloatingCardProps) => {
  const prefersReducedMotion = useReducedMotion();
  
  return (
    <motion.div
      className={`absolute z-0 ${positionClasses} ${sizeClasses} transform-gpu`}
      initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.8, rotate: prefersReducedMotion ? rotation : rotation + 10 }}
      animate={{ opacity: 1, scale: 1, rotate: rotation }}
      transition={{
        opacity: { duration: 1, delay },
        scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
      }}
      aria-hidden="true"
    >
      <motion.div
        animate={prefersReducedMotion ? {} : { y: [0, -15, 0] }}
        transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
        className="w-full h-full transform-gpu"
        style={{ transform: "translateZ(0)" }}
      >
        <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] lg:shadow-[0_30px_60px_rgba(0,0,0,0.8)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 pointer-events-auto ${colorCls}`}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
          <Image src={image} alt="" fill sizes="(max-width: 768px) 30vw, 20vw" decoding="async" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
          <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
            <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.2em] lg:tracking-[0.3em] opacity-70 text-current mix-blend-overlay truncate">{category}</span>
            <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight truncate" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
          </div>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
        </div>
      </motion.div>
    </motion.div>
  );
});
HeroFloatingCard.displayName = 'HeroFloatingCard';

// ============================================================================
// --- [7] HERO SECTION (Cosmic Teal/Purple Starfield Background, Vibrant UI) ---
// ============================================================================

interface HeroSectionProps {
  readonly onOrderClick: () => void;
  readonly onExploreClick: () => void;
}

const HeroSection = memo(({ onOrderClick, onExploreClick }: HeroSectionProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end start'] });
  const yParallax = useTransform(scrollYProgress, [0, 1], ['0%', '25%']);
  const opacityFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const messages = useAIOrderingStore((state) => state.messages);
  const prefersReducedMotion = useReducedMotion();
  const capsuleControls = useAnimation();
  const titleId = useId();
  
  const cartItemsCount = useMemo(() => {
    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cartContent = lastCartMessage?.content as { items?: unknown[] } | undefined;
    return cartContent?.items?.length || 0;
  }, [messages]);

  const prevCountRef = useRef(cartItemsCount);

  useEffect(() => {
    if (cartItemsCount > prevCountRef.current && !prefersReducedMotion) {
      capsuleControls.start({
        scale: [1, 1.04, 0.97, 1.02, 1],
        x: [0, -4, 4, -2, 2, 0],
        filter: [
          "drop-shadow(0 0 0px rgba(6,182,212,0))",
          "drop-shadow(0 0 25px rgba(6,182,212,0.8))",
          "drop-shadow(0 0 0px rgba(6,182,212,0))"
        ],
        transition: { duration: 0.5, ease: "easeInOut" }
      });
    }
    prevCountRef.current = cartItemsCount;
  }, [cartItemsCount, capsuleControls, prefersReducedMotion]);

  return (
    <section ref={containerRef} className={`${HERO_STAGE_CLASSES} bg-[#04060A] home-viewport-hero`} data-hero-stage="home" style={{ contain: 'layout paint' }} aria-labelledby={titleId}>
      
      {/* High-Performance Cosmic Teal & Purple Starfield Background */}
      <CosmicDustCanvas />
      <FloatingHeroCards />

      <motion.div
        style={{ opacity: opacityFade }}
        className="w-full max-w-3xl lg:max-w-[48%] mx-auto px-4 sm:px-6 relative z-10"
      >
        <div className="w-full flex flex-col items-center justify-center relative">
          
          <div className="flex flex-col items-center text-center max-w-3xl w-full relative z-30 pointer-events-auto">
            <AISecuredOrdersBadge unframed />
            <motion.h1
              id={titleId}
              initial="hidden" animate="visible" variants={fadeUpVariant}
              className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tighter text-white leading-[1.05] mb-6 font-sans drop-shadow-2xl"
            >
              Shopping at the <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-purple-200 drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                speed of thought.
              </span>
            </motion.h1>

            <motion.p
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.1 }}
              className="text-sm sm:text-lg md:text-xl text-zinc-300 mb-10 leading-relaxed font-light max-w-lg mx-auto"
            >
              Your needs, instantly fulfilled. Our AI secures the best deal and tracks your delivery in real time.
            </motion.p>

            <motion.div
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.2 }}
              className="w-full max-w-xl mx-auto"
            >
              <motion.button
                onClick={onOrderClick}
                aria-label={cartItemsCount > 0 ? `Review order with ${cartItemsCount} items` : "Start AI order"}
                animate={
                  cartItemsCount > 0 && !prefersReducedMotion
                    ? { y: [0, -6, 0], boxShadow: ["0px 0px 40px rgba(0,0,0,0.8)", "0px 10px 40px rgba(6,182,212,0.3)", "0px 0px 40px rgba(0,0,0,0.8)"] }
                    : { y: 0, boxShadow: "0px 0px 40px rgba(0,0,0,0.8)" }
                }
                transition={cartItemsCount > 0 && !prefersReducedMotion ? { duration: 3, repeat: Infinity, ease: "easeInOut" } : {}}
                className="group w-full relative flex items-center p-1.5 sm:p-2 rounded-[73px] bg-zinc-900/90 border border-white/10 backdrop-blur-2xl transition-all duration-500 hover:border-cyan-500/50 hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 cursor-pointer"
              >
                {/* Colorful Glow restored for the button */}
                <div className={`absolute -inset-[1px] rounded-[73px] blur-md transition-all duration-1000 -z-10 ${cartItemsCount > 0 ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 opacity-100' : 'bg-gradient-to-r from-cyan-500/40 to-purple-500/40 opacity-80 group-hover:-inset-[3px] group-hover:opacity-100 group-hover:blur-xl'}`} aria-hidden="true" />

                <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-zinc-800/80 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0 transform-gpu relative">
                  <AirSparkles className="h-6 w-6 text-purple-400 sm:h-7 sm:w-7" />
                  {cartItemsCount > 0 && (
                    <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-black text-[#050505] shadow-[0_0_10px_rgba(6,182,212,0.8)]" aria-hidden="true">
                      {cartItemsCount}
                    </motion.span>
                  )}
                </div>

                <div className="flex-1 px-3 sm:px-4 min-w-0 text-left" aria-live="polite">
                  <p className={`text-[11px] sm:text-sm md:text-base font-light truncate transition-colors ${cartItemsCount > 0 ? 'text-cyan-200 font-medium' : 'text-zinc-300'}`}>
                    {cartItemsCount > 0 ? "Your order is ready. Tap to review." : <TypewriterText text="I need noise-canceling headphones..." />}
                  </p>
                </div>

                {cartItemsCount === 0 && <PromptMediaIcons />}

                <span className="flex items-center justify-center gap-2 px-4 sm:px-6 py-3 sm:py-3 rounded-full bg-white text-black font-bold text-[10px] sm:text-sm hover:bg-cyan-50 hover:text-cyan-900 transition-colors shrink-0 whitespace-nowrap shadow-lg shadow-white/10 transform-gpu pointer-events-none">
                  {cartItemsCount > 0 ? "Confirm Order!" : "Order with Air"}
                </span>
              </motion.button>

              <div className="mt-6 flex items-center justify-center gap-6">
                <button 
                  onClick={onExploreClick} 
                  className="text-xs sm:text-sm font-medium text-zinc-300 hover:text-cyan-300 transition-colors flex items-center gap-1 group transform-gpu rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4"
                >
                  Explore trending products <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </button>
              </div>
            </motion.div>
          </div>


        </div>
      </motion.div>
    </section>
  );
});
HeroSection.displayName = 'HeroSection';

const MobileHomeHeroSection = memo(({ onOrderClick, onExploreClick }: HeroSectionProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end start'] });
  const yParallax = useTransform(scrollYProgress, [0, 1], ['0%', '25%']);
  const opacityFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const messages = useAIOrderingStore((state) => state.messages);
  const prefersReducedMotion = useReducedMotion();
  const capsuleControls = useAnimation();
  const titleId = useId();
  
  const cartItemsCount = useMemo(() => {
    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cartContent = lastCartMessage?.content as { items?: unknown[] } | undefined;
    return cartContent?.items?.length || 0;
  }, [messages]);

  const prevCountRef = useRef(cartItemsCount);

  useEffect(() => {
    if (cartItemsCount > prevCountRef.current && !prefersReducedMotion) {
      capsuleControls.start({
        scale: [1, 1.04, 0.97, 1.02, 1],
        x: [0, -4, 4, -2, 2, 0],
        filter: [
          "drop-shadow(0 0 0px rgba(6,182,212,0))",
          "drop-shadow(0 0 25px rgba(6,182,212,0.8))",
          "drop-shadow(0 0 0px rgba(6,182,212,0))"
        ],
        transition: { duration: 0.5, ease: "easeInOut" }
      });
    }
    prevCountRef.current = cartItemsCount;
  }, [cartItemsCount, capsuleControls, prefersReducedMotion]);

  return (
    <section ref={containerRef} className="relative w-full bg-[#04060A] overflow-hidden flex items-center min-h-[100svh] pt-28 pb-16 lg:pt-32 lg:pb-32 isolate" style={{ contain: 'layout paint' }} aria-labelledby={titleId}>
      
      {/* High-Performance Cosmic Teal & Purple Starfield Background */}
      <CosmicDustCanvas />

      <motion.div
        style={{ y: prefersReducedMotion ? 0 : yParallax, opacity: opacityFade }}
        className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10 h-full transform-gpu"
      >
        <div className="w-full flex flex-col items-center justify-center relative h-full min-h-[600px]">
          
          <div className="flex flex-col items-center text-center max-w-3xl w-full relative z-30 pointer-events-auto">
            <AISecuredOrdersBadge unframed />
            <motion.h1
              id={titleId}
              initial="hidden" animate="visible" variants={fadeUpVariant}
              className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tighter text-white leading-[1.05] mb-6 font-sans drop-shadow-2xl"
            >
              Shopping at the <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-purple-200 drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                speed of thought.
              </span>
            </motion.h1>

            <motion.p
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.1 }}
              className="text-sm sm:text-lg md:text-xl text-zinc-300 mb-10 leading-relaxed font-light max-w-lg mx-auto"
            >
              Your needs, instantly fulfilled. Our AI secures the best deal and tracks your delivery in real time.
            </motion.p>

            <motion.div
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.2 }}
              className="w-full max-w-xl mx-auto"
            >
              <motion.button
                onClick={onOrderClick}
                aria-label={cartItemsCount > 0 ? `Review order with ${cartItemsCount} items` : "Start AI order"}
                animate={
                  cartItemsCount > 0 && !prefersReducedMotion
                    ? { y: [0, -6, 0], boxShadow: ["0px 0px 40px rgba(0,0,0,0.8)", "0px 10px 40px rgba(6,182,212,0.3)", "0px 0px 40px rgba(0,0,0,0.8)"] }
                    : { y: 0, boxShadow: "0px 0px 40px rgba(0,0,0,0.8)" }
                }
                transition={cartItemsCount > 0 && !prefersReducedMotion ? { duration: 3, repeat: Infinity, ease: "easeInOut" } : {}}
                className="group w-full relative flex items-center p-1.5 sm:p-2 rounded-[73px] bg-zinc-900/90 border border-white/10 backdrop-blur-2xl transition-all duration-500 hover:border-cyan-500/50 hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 cursor-pointer"
              >
                {/* Colorful Glow restored for the button */}
                <div className={`absolute -inset-[1px] rounded-[73px] blur-md transition-all duration-1000 -z-10 ${cartItemsCount > 0 ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 opacity-100' : 'bg-gradient-to-r from-cyan-500/40 to-purple-500/40 opacity-80 group-hover:-inset-[3px] group-hover:opacity-100 group-hover:blur-xl'}`} aria-hidden="true" />

                <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-zinc-800/80 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0 transform-gpu relative">
                  <AirSparkles className="h-6 w-6 text-purple-400 sm:h-7 sm:w-7" />
                  {cartItemsCount > 0 && (
                    <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-black text-[#050505] shadow-[0_0_10px_rgba(6,182,212,0.8)]" aria-hidden="true">
                      {cartItemsCount}
                    </motion.span>
                  )}
                </div>

                <div className="flex-1 px-3 sm:px-4 min-w-0 text-left" aria-live="polite">
                  <p className={`text-[11px] sm:text-sm md:text-base font-light truncate transition-colors ${cartItemsCount > 0 ? 'text-cyan-200 font-medium' : 'text-zinc-300'}`}>
                    {cartItemsCount > 0 ? "Your order is ready. Tap to review." : <TypewriterText text="I need noise-canceling headphones..." />}
                  </p>
                </div>

                {cartItemsCount === 0 && <PromptMediaIcons />}

                <span className="flex items-center justify-center gap-2 px-4 sm:px-6 py-3 sm:py-3 rounded-full bg-white text-black font-bold text-[10px] sm:text-sm hover:bg-cyan-50 hover:text-cyan-900 transition-colors shrink-0 whitespace-nowrap shadow-lg shadow-white/10 transform-gpu pointer-events-none">
                  {cartItemsCount > 0 ? "Confirm Order!" : "Order with Air"}
                </span>
              </motion.button>

              <div className="mt-6 flex items-center justify-center gap-6">
                <button 
                  onClick={onExploreClick} 
                  className="text-xs sm:text-sm font-medium text-zinc-300 hover:text-cyan-300 transition-colors flex items-center gap-1 group transform-gpu rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4"
                >
                  Explore trending products <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </button>
              </div>
            </motion.div>
          </div>

          <div className="absolute inset-0 pointer-events-none z-20 flex items-center justify-center perspective-1000">
            <motion.div
              initial={{ opacity: 0, scale: 0.9, rotateY: 10 }} animate={{ opacity: 1, scale: 1, rotateY: 0 }} transition={{ duration: 1.2, ease: TRANSITION_PREMIUM, delay: 0.2 }}
              className="relative w-full h-full flex items-center justify-center transform-gpu"
            >
              {HERO_CARDS.map((card) => (
                <HeroFloatingCard key={card.title} {...card} />
              ))}
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
});
MobileHomeHeroSection.displayName = 'MobileHomeHeroSection';

// ============================================================================
// --- [8] HOW IT WORKS SECTION (Restored Vibrant Colors) ---
// ============================================================================

interface StepItem {
  readonly icon: LucideIcon;
  readonly step: string;
  readonly title: string;
  readonly description: string;
}

const HolographicStepCard = memo(({ item, isLast }: { readonly item: StepItem; readonly isLast: boolean; }) => {
  const cardRef = useRef<HTMLLIElement>(null);
  const { scrollYProgress } = useScroll({ target: cardRef, offset: ["start 95%", "center center"] });
  const prefersReducedMotion = useReducedMotion();

  const opacity = useTransform(scrollYProgress, [0, 0.6, 1], [0, 0.5, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [80, 0]);
  const rotateX = useTransform(scrollYProgress, [0, 1], [15, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], [0.9, 1]);
  const scaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);

  const Icon = item.icon;

  return (
    <li ref={cardRef} className="relative flex w-full gap-6 md:gap-12 pb-24 md:pb-32 last:pb-0 perspective-1000">
      <div className="relative flex shrink-0 flex-col items-center" aria-hidden="true">
        <motion.div
          style={{ scale: prefersReducedMotion ? 1 : scale, opacity: prefersReducedMotion ? 1 : opacity }}
          className="z-10 flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-2xl border border-cyan-400/40 bg-black/50 shadow-[0_0_30px_rgba(6,182,212,0.3)] backdrop-blur-md rotate-45 transform-gpu"
        >
          <div className="-rotate-45 flex flex-col items-center">
            <span className="font-mono text-[15px] md:text-lg font-black text-cyan-300 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]">{item.step}</span>
          </div>
        </motion.div>

        {!isLast && (
          <div className="absolute top-14 md:top-20 bottom-[-6rem] md:bottom-[-8rem] w-[2px] bg-white/5">
            <motion.div
              style={{ scaleY: prefersReducedMotion ? 1 : scaleY, transformOrigin: "top" }}
              className="w-full h-full bg-gradient-to-b from-cyan-400 via-purple-500 to-transparent shadow-[0_0_10px_rgba(6,182,212,0.8)] transform-gpu"
            />
          </div>
        )}
      </div>

      <motion.div
        style={{ opacity: prefersReducedMotion ? 1 : opacity, y: prefersReducedMotion ? 0 : y, rotateX: prefersReducedMotion ? 0 : rotateX }}
        className="flex-1 mt-2 md:mt-4 transform-gpu"
      >
        <div className="group relative overflow-hidden rounded-[32px] border border-white/10 bg-gradient-to-br from-white/[0.03] to-transparent p-6 md:p-10 backdrop-blur-xl transition-all duration-700 hover:border-cyan-400/40 hover:bg-white/[0.05] shadow-2xl">
          <div className="absolute -inset-px bg-gradient-to-r from-cyan-500/15 to-purple-500/15 opacity-0 group-hover:opacity-100 blur-2xl transition-all duration-700 pointer-events-none transform-gpu" aria-hidden="true" />

          <div className="relative z-10 flex flex-col md:flex-row gap-6 md:gap-8 items-start md:items-center">
            <div className="flex items-center justify-center h-14 w-14 md:h-20 md:w-20 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.2)] group-hover:scale-110 group-hover:shadow-[0_0_30px_rgba(168,85,247,0.4)] transition-all duration-500 shrink-0 transform-gpu" aria-hidden="true">
              <Icon size={32} strokeWidth={1.5} className="group-hover:text-purple-300 transition-colors" />
            </div>

            <div>
              <h3 className="mb-3 text-2xl md:text-4xl font-bold tracking-tight text-white group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-cyan-200 transition-all duration-500">
                <span className="sr-only">Step {item.step}: </span>{item.title}
              </h3>
              <p className="text-[15px] md:text-lg font-normal leading-[1.75] text-zinc-300 group-hover:text-gray-300 transition-colors duration-500">
                {item.description}
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </li>
  );
});
HolographicStepCard.displayName = 'HolographicStepCard';

const HowItWorksSection = memo(() => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start end", "end start"] });
  const yParallax = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const prefersReducedMotion = useReducedMotion();

  return (
    <section ref={containerRef} className="relative w-full overflow-hidden bg-transparent pt-12 pb-32 lg:pt-16 lg:pb-48 border-t border-white/5 isolate" style={{ contain: 'layout paint' }} aria-labelledby="how-it-works-heading">
      <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
        <motion.div style={{ y: prefersReducedMotion ? 0 : yParallax }} className="absolute inset-0 transform-gpu">
          {/* Restored Ambient Glows */}
          <div className="absolute top-[10%] left-[-20%] w-[60%] h-[60%] rounded-full bg-cyan-600/[0.04] blur-[80px] mix-blend-screen transform-gpu" />
          <div className="absolute bottom-[10%] right-[-20%] w-[60%] h-[60%] rounded-full bg-purple-600/[0.04] blur-[80px] mix-blend-screen transform-gpu" />
          
        </motion.div>
      </div>

      <div className="container relative z-10 mx-auto px-5 sm:px-6 lg:px-12">
        <div className="text-center mb-24 md:mb-32 flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }}
            className="mb-8 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/30 px-5 py-2 backdrop-blur-md shadow-[0_0_20px_rgba(6,182,212,0.2)] transform-gpu"
            aria-hidden="true"
          >
            <Activity size={16} className={`${prefersReducedMotion ? '' : 'animate-pulse'} text-cyan-400`} />
            <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-cyan-300">END-TO-END SYSTEM</span>
          </motion.div>

          <motion.h2
            id="how-it-works-heading"
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1, duration: 0.8 }}
            className="text-5xl md:text-7xl lg:text-8xl font-semibold leading-[1.05] tracking-tight text-white drop-shadow-2xl transform-gpu"
          >
            <span>HOW IT</span> <br className="md:hidden" />
            <span className="bg-gradient-to-r from-cyan-400 via-white to-purple-500 bg-clip-text text-transparent px-2">
              WORKS
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.2, duration: 0.8 }}
            className="mt-8 max-w-2xl text-lg md:text-xl font-normal leading-[1.75] text-zinc-300 transform-gpu"
          >
            Watch how our neural network translates your thoughts into a verified, checkout-ready product in seconds.
          </motion.p>
        </div>

        <ol className="max-w-4xl mx-auto w-full p-0 m-0 list-none">
          {PRODUCTION_STEPS.map((step, index) => (
            <HolographicStepCard key={step.step} item={step} isLast={index === PRODUCTION_STEPS.length - 1} />
          ))}
        </ol>
      </div>
    </section>
  );
});
HowItWorksSection.displayName = 'HowItWorksSection';

// ============================================================================
// --- [9] FINAL CTA & TRUSTED BY (Restored Vibrant Colors) ---
// ============================================================================

const FinalCTA = memo(() => (
  <section className="relative w-full py-32 overflow-hidden bg-transparent flex items-center justify-center border-t border-white/5 isolate" style={{ contain: 'layout paint' }} aria-labelledby="cta-heading">
    <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[100px] transform-gpu" />
    </div>

    <div className="container mx-auto px-6 relative z-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 30 }} whileInView={{ opacity: 1, scale: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.8, ease: "easeOut" }}
        className="max-w-5xl mx-auto transform-gpu"
      >
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-950/30 border border-cyan-500/30 backdrop-blur-md mb-8 ring-1 ring-cyan-500/20" aria-hidden="true">
          <Zap size={14} className="text-yellow-400 fill-yellow-400" />
          <span className="text-xs font-mono text-cyan-300 uppercase tracking-widest">Next-Gen Shopping Experience</span>
        </div>

        <h2 id="cta-heading" className="text-4xl md:text-7xl font-semibold text-white mb-8 tracking-tight leading-[1.1]">
          Future of Commerce:<br />
          <span className="text-purple-400 drop-shadow-[0_0_40px_rgba(192,132,252,0.5)]">
            Powered by AI.
          </span>
        </h2>

        <p className="text-base md:text-2xl text-zinc-300 max-w-2xl mx-auto mb-12 font-normal leading-[1.75]">
          Don't search. Just ask. Shop thousands of curated products with our intelligent multimodal AI.
        </p>

        <div className="flex flex-col gap-6 justify-center items-center">
          <Link href="/profile" className="group relative px-12 py-7 bg-white text-black font-black text-xl rounded-full overflow-hidden transition-all duration-300 hover:shadow-[0_0_50px_rgba(255,255,255,0.3)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 transform-gpu">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-purple-500 opacity-0 group-hover:opacity-20 transition-opacity duration-300" aria-hidden="true" />
            <span className="relative flex items-center gap-3">
              SIGN UP <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
            </span>
          </Link>
          <button className="group px-12 py-7 text-white font-bold text-xl rounded-full border border-white/20 hover:bg-white/10 hover:border-cyan-400/50 transition-all duration-300 flex items-center gap-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 transform-gpu">
            <span>DOWNLOAD APP</span><ArrowDown className="w-6 h-6 group-hover:translate-y-1 transition-transform" aria-hidden="true" />
          </button>
        </div>
        <p className="mt-12 text-[9px] text-zinc-600 font-mono uppercase">Multimodal AI • One-Tap Checkout • 100% Autonomous</p>
      </motion.div>
    </div>
  </section>
));
FinalCTA.displayName = 'FinalCTA';

const TrustedBySection = memo(({ nonce }: { readonly nonce?: string }) => {
  const companies = ["NVIDIA", "STRIPE", "AWS", "CLOUDFLARE", "MASTERCARD"];
  const repeatedCompanies = [...companies, ...companies, ...companies, ...companies];
  return (
    <section className="py-12 bg-transparent border-y border-white/5 overflow-hidden relative isolate" style={{ contain: 'layout paint' }} aria-label="Trusted Partners">
      <div className="absolute inset-0 bg-cyan-900/5 blur-3xl pointer-events-none transform-gpu" aria-hidden="true" />
      <div className="container mx-auto px-4 mb-6 text-center relative z-10">
        <p className="text-[10px] font-mono text-zinc-600 uppercase tracking-[0.3em]" aria-hidden="true">Trusted by Industry Leaders</p>
        <span className="sr-only">Trusted by NVIDIA, STRIPE, AWS, CLOUDFLARE, and MASTERCARD.</span>
      </div>
      <div className="relative flex overflow-x-hidden group">
        <div className="absolute top-0 left-0 h-full w-24 bg-gradient-to-r from-[#050505] to-transparent z-10 pointer-events-none" aria-hidden="true" />
        <div className="absolute top-0 right-0 h-full w-24 bg-gradient-to-l from-[#050505] to-transparent z-10 pointer-events-none" aria-hidden="true" />
        
        <div className="flex gap-16 items-center hover:[animation-play-state:paused] transform-gpu" style={{ animation: 'marquee 25s linear infinite' }} aria-hidden="true">
          {repeatedCompanies.map((company, index) => (
            <span key={`${company}-${index}`} className="text-xl md:text-2xl font-bold text-zinc-800 uppercase tracking-tighter hover:text-cyan-400 transition-colors duration-500 cursor-default select-none whitespace-nowrap" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {company}
            </span>
          ))}
        </div>
      </div>
      <style nonce={nonce} dangerouslySetInnerHTML={{__html: `
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
      `}} />
    </section>
  );
});
TrustedBySection.displayName = 'TrustedBySection';

// ============================================================================
// --- [10] MAIN CLIENT EXPORT ---
// ============================================================================

interface LandingClientProps {
  readonly nonce: string;
  readonly initialTraceId: string;
}

export function LandingClient({ nonce, initialTraceId }: LandingClientProps) {
  const [uiState, dispatch] = useReducer(uiFSMReducer, { status: 'IDLE', activeTraceId: initialTraceId });
  const { isMobile, isStandalone, mounted } = useDeviceDetection();
  
  // Stores synchronization
  const setOverlayVisible = useAIOrderingStore(state => state.setOverlayVisible);
  const { showProductOverlay, hideProductOverlay } = useUIStore();

  useEffect(() => {
    if (mounted && isMobile && !isStandalone) {
      dispatch({ type: 'FORCE_MOBILE_VIEW' });
    }
  }, [mounted, isMobile, isStandalone]);

  // Strict telemetry dispatch with AbortController lifecycle
  useEffect(() => {
    const controller = new AbortController();
    const payload = TrackingPayloadSchema.safeParse({
      traceId: initialTraceId,
      timestamp: Date.now(),
      event: 'MOUNT',
      metadata: { status: uiState.status, noncePresent: Boolean(nonce) }
    });

    if (payload.success && typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('/api/telemetry/rum', JSON.stringify(payload.data));
    }

    return () => {
      controller.abort();
    };
  }, [initialTraceId, uiState.status, nonce]);

  if (!mounted) {
    return <div className="w-full bg-[#050505] isolate min-h-[100svh]" aria-hidden="true" />;
  }

  if (uiState.status === 'MOBILE_PWA_VIEW') {
    return <MobileLandingView />;
  }

  const handleOrderClick = () => {
    const actionTraceId = randomId();
    dispatch({ type: 'OPEN_AI_CART', payload: { traceId: actionTraceId } });
    setOverlayVisible(true);
  };

  const handleExploreClick = () => {
    const actionTraceId = randomId();
    dispatch({ type: 'OPEN_PRODUCTS', payload: { traceId: actionTraceId } });
    showProductOverlay();
  };

  const handleClose = () => {
    dispatch({ type: 'CLOSE_OVERLAYS' });
    setOverlayVisible(false);
    hideProductOverlay();
  };

  return (
    <RUMErrorBoundary traceId={initialTraceId} fallback={<div className="p-8 text-center text-white w-full">System telemetry interruption. Please refresh.</div>}>
      <div className="flex flex-col w-full text-gray-100 bg-[#050505] isolate" style={{ fontFamily: "'Montserrat', sans-serif" }}>
        <main className="relative z-10 flex flex-col w-full transform-gpu home-continuous-background">
          {isMobile ? <MobileHomeHeroSection onOrderClick={handleOrderClick} onExploreClick={handleExploreClick} /> : <HeroSection onOrderClick={handleOrderClick} onExploreClick={handleExploreClick} />}
          <HowItWorksSection />
          <FinalCTA />
          <TrustedBySection nonce={nonce} />
        </main>

        <ProductOverlay isOpen={uiState.status === 'PRODUCT_OVERLAY_ACTIVE'} onClose={handleClose} />
        <AIChatOverlay isOpen={uiState.status === 'AI_OVERLAY_ACTIVE'} onClose={handleClose} />
      </div>
    </RUMErrorBoundary>
  );
}
