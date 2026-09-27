// ============================================================================
// FILE: apps/web/app/(main)/_components/LandingClient.tsx
// ============================================================================
'use client';

import Image from "next/image";
import Link from 'next/link';
import React, { 
  useRef, useMemo, useEffect, useReducer, memo, useId, Component, ErrorInfo, ReactNode 
} from 'react';
import { 
  motion, useScroll, useSpring, useInView, useTransform, 
  useMotionValue, useAnimation, useReducedMotion 
} from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload, Float, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

// Monorepo Path Aliases
import { useDeviceDetection } from '@/hooks/usePWAInstall';
import { MobileLandingView } from '@/components/home/MobileLandingView';
import { useUIStore } from '@/hooks/useUIStore';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import ProductOverlay from '@/components/products/ProductOverlay';

// Lucide Icons
import { 
  MapIcon, GlobeIcon, CheckCircle2, Activity, Bot, ChevronRight, 
  Rocket, Zap, ArrowRight, Cpu, ArrowDown
} from 'lucide-react';

// ============================================================================
// --- ZERO-DEPENDENCY BOUNDARY VALIDATION CONTRACT (Zod-Compatible) ---
// ============================================================================

export interface TrackingPayload {
  traceId: string;
  timestamp: number;
  event: 'MOUNT' | 'INTERACTION' | 'ERROR';
  metadata?: Record<string, unknown>;
}

export type ValidationResult<T> = 
  | { success: true; data: T }
  | { success: false; error: { message: string } };

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
// --- DETERMINISTIC FSM (FINITE STATE MACHINE) ---
// ============================================================================

export type UIStatus = 'IDLE' | 'AI_OVERLAY_ACTIVE' | 'PRODUCT_OVERLAY_ACTIVE' | 'MOBILE_PWA_VIEW' | 'FATAL_ERROR';

export type UIAction =
  | { type: 'OPEN_AI_CART'; payload: { traceId: string } }
  | { type: 'OPEN_PRODUCTS'; payload: { traceId: string } }
  | { type: 'CLOSE_OVERLAYS' }
  | { type: 'FORCE_MOBILE_VIEW' }
  | { type: 'REPORT_ERROR'; payload: { message: string } };

export interface UIState {
  status: UIStatus;
  activeTraceId?: string;
  errorMessage?: string;
}

const FSM_TRANSITIONS: Record<UIStatus, Partial<Record<UIAction['type'], (state: UIState, action: UIAction) => UIState>>> = {
  IDLE: {
    OPEN_AI_CART: (_, action) => ({ status: 'AI_OVERLAY_ACTIVE', activeTraceId: (action as any).payload.traceId }),
    OPEN_PRODUCTS: (_, action) => ({ status: 'PRODUCT_OVERLAY_ACTIVE', activeTraceId: (action as any).payload.traceId }),
    FORCE_MOBILE_VIEW: () => ({ status: 'MOBILE_PWA_VIEW' }),
    REPORT_ERROR: (_, action) => ({ status: 'FATAL_ERROR', errorMessage: (action as any).payload.message }),
    CLOSE_OVERLAYS: (state) => state,
  },
  AI_OVERLAY_ACTIVE: {
    CLOSE_OVERLAYS: () => ({ status: 'IDLE' }),
    OPEN_PRODUCTS: (_, action) => ({ status: 'PRODUCT_OVERLAY_ACTIVE', activeTraceId: (action as any).payload.traceId }),
    FORCE_MOBILE_VIEW: () => ({ status: 'MOBILE_PWA_VIEW' }),
    REPORT_ERROR: (_, action) => ({ status: 'FATAL_ERROR', errorMessage: (action as any).payload.message }),
  },
  PRODUCT_OVERLAY_ACTIVE: {
    CLOSE_OVERLAYS: () => ({ status: 'IDLE' }),
    OPEN_AI_CART: (_, action) => ({ status: 'AI_OVERLAY_ACTIVE', activeTraceId: (action as any).payload.traceId }),
    FORCE_MOBILE_VIEW: () => ({ status: 'MOBILE_PWA_VIEW' }),
    REPORT_ERROR: (_, action) => ({ status: 'FATAL_ERROR', errorMessage: (action as any).payload.message }),
  },
  MOBILE_PWA_VIEW: {
    REPORT_ERROR: (_, action) => ({ status: 'FATAL_ERROR', errorMessage: (action as any).payload.message }),
  },
  FATAL_ERROR: {}
};

function uiFSMReducer(state: UIState, action: UIAction): UIState {
  const transitionFn = FSM_TRANSITIONS[state.status]?.[action.type];
  return transitionFn ? transitionFn(state, action) : state;
}

// ============================================================================
// --- RUM OBSERVABILITY ERROR BOUNDARY ---
// ============================================================================

class RUMErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode; traceId: string }, { hasError: boolean }> {
  constructor(props: any) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const errorPayload = {
      traceId: this.props.traceId,
      timestamp: Date.now(),
      event: 'ERROR',
      metadata: { message: error.message, stack: error.stack, componentStack: errorInfo.componentStack }
    };
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('/api/telemetry/rum', JSON.stringify(errorPayload));
    }
  }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}

// ============================================================================
// --- CONFIGURATIONS & ASSETS ---
// ============================================================================

const TRANSITION_PREMIUM = [0.16, 1, 0.3, 1];
const fadeUpVariant = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: TRANSITION_PREMIUM } }
};

const heroCanvasConfig = {
  camera: { position: [0, 0, 15] as [number, number, number], fov: 75 },
  gl: { antialias: false, powerPreference: "high-performance" as const, alpha: true, depth: false, stencil: false },
};

const globeCanvasConfig = {
  camera: { position: [0, 0, 19] as [number, number, number], fov: 35 },
  gl: { antialias: false, powerPreference: "high-performance" as const, alpha: true },
};

interface HeroFloatingCardProps {
  title: string; image: string; category: string; delay: number;
  positionClasses: string; sizeClasses: string; colorCls: string; rotation: number;
}

const HERO_CARDS: HeroFloatingCardProps[] = [
  { title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[1%] left-[16%] lg:top-[10%] lg:left-[5%]", sizeClasses: "w-21 h-29 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/20 text-cyan-400" },
  { title: "PS5", category: "Wearables", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[1%] right-[16%] lg:top-[10%] lg:right-[5%]", sizeClasses: "w-21 h-29 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/20 text-purple-400" },
  { title: "Dyson", category: "Aesthetic", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -left-[4%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/20 text-pink-400" },
  { title: "Headphones", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -right-[3%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/20 text-amber-400" },
  { title: "Leather Handbag", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] left-[2%] lg:bottom-[25%] lg:left-[8%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/20 text-emerald-400" },
  { title: "Iphone 17 pro max", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] right-[1%] lg:bottom-[25%] lg:right-[8%]", sizeClasses: "w-22 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/20 text-blue-400" },
  { title: "Nike Air Max", category: "Fashion", delay: 0.7, rotation: -5, image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] left-[20%] lg:bottom-[5%] lg:left-[25%]", sizeClasses: "w-20 h-28 lg:w-48 lg:h-48", colorCls: "hover:shadow-red-500/20 text-red-400" },
  { title: "Galaxy Buds", category: "Neural Tech", delay: 0.8, rotation: 7, image: "https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] right-[20%] lg:bottom-[5%] lg:right-[25%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-cyan-500/20 text-cyan-400" }
];

const PRODUCTION_STEPS = [
  { icon: Bot, step: "01", title: "AI Intent Recognition", description: "Simply type or speak your order. Our neural engine parses your intent instantly, finding the exact product in our global network without you scrolling through catalogs." },
  { icon: Cpu, step: "02", title: "Inventory Sync", description: "Within milliseconds, the system queries local hubs and databases to secure the best price and immediate availability, reserving your item autonomously." },
  { icon: MapIcon, step: "03", title: "4D Route Computation", description: "An adaptive flight plan is generated. The AI factors in live weather layers, urban topology, and airspace corridors to chart the absolute fastest drone vector." },
  { icon: Rocket, step: "04", title: "Precision Doorstep Drop", description: "The autonomous drone arrives. Using computer vision and micro-thruster stabilization, it completes a contactless, verified handoff directly to your location." },
];

// ============================================================================
// --- WEBGL PRIMITIVES ---
// ============================================================================

const createParticlePositions = (count: number, radius: number): Float32Array => {
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = radius * Math.cbrt(Math.random());
    const theta = Math.random() * 2 * Math.PI;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);
  }
  return positions;
};

const ParticleField = memo(({ count, radius, color, size, rotationSpeed, position = [0, 0, -60] }: any) => {
  const groupRef = useRef<THREE.Group>(null);
  const pointsRef = useRef<THREE.Points>(null);
  const prefersReducedMotion = useReducedMotion();
  
  const positions = useMemo(() => createParticlePositions(count, radius), [count, radius]);
  const materialColor = useMemo(() => new THREE.Color(color), [color]);

  useEffect(() => {
    if (pointsRef.current) pointsRef.current.matrixAutoUpdate = false;
    return () => {
      // Deterministic cleanup prevents VRAM leaking on component dismount
      if (pointsRef.current?.geometry) pointsRef.current.geometry.dispose();
      if (pointsRef.current?.material) (pointsRef.current.material as THREE.Material).dispose();
    };
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current || prefersReducedMotion) return;
    const safeDelta = Math.min(delta, 0.1);
    groupRef.current.rotation.x += safeDelta * rotationSpeed.x;
    groupRef.current.rotation.y += safeDelta * rotationSpeed.y;
    groupRef.current.rotation.z += safeDelta * rotationSpeed.z;
  });

  return (
    <group ref={groupRef} position={position}>
      <points ref={pointsRef} frustumCulled={true}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial 
          transparent color={materialColor} size={size} sizeAttenuation depthWrite={false} 
          toneMapped={false} opacity={0.8} 
          onBeforeCompile={(shader) => {
            shader.fragmentShader = shader.fragmentShader.replace(
              'void main() {',
              `void main() {
                vec2 pt = gl_PointCoord - vec2(0.5);
                if (dot(pt, pt) > 0.20) discard;`
            );
          }}
        />
      </points>
    </group>
  );
});
ParticleField.displayName = 'ParticleField';

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
            <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.2em] lg:tracking-[0.3em] opacity-70 text-white mix-blend-overlay truncate">{category}</span>
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
// --- 1. HERO SECTION ---
// ============================================================================

const HeroSection = memo(({ onOrderClick, onExploreClick }: { onOrderClick: () => void; onExploreClick: () => void }) => {
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
    return lastCartMessage?.content?.items?.length || 0;
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
    // Explicit CSS containment on sections isolates rendering boundaries during scroll
    <section ref={containerRef} className="relative min-h-[100svh] w-full bg-[#050505] overflow-hidden flex items-center pt-28 pb-16 lg:pt-0 lg:pb-0" style={{ contain: 'content' }} aria-labelledby={titleId}>
      <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
        {/* Adaptive DPR prevents VRAM bottlenecking on modern 3x retina displays */}
        <Canvas {...heroCanvasConfig} dpr={[1, 1.5]} performance={{ min: 0.5 }}>
          <ParticleField count={10000} radius={66} color="#ffffff" size={0.065} rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.001 }} />
          <Preload all />
        </Canvas>
      </div>

      <div className="absolute top-[-10%] left-[-20%] w-[70%] h-[70%] rounded-full bg-cyan-600/15 blur-[120px] pointer-events-none mix-blend-screen transform-gpu" aria-hidden="true" />
      <div className="absolute bottom-[-10%] right-[-20%] w-[70%] h-[70%] rounded-full bg-purple-600/15 blur-[120px] pointer-events-none mix-blend-screen transform-gpu" aria-hidden="true" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,#000_20%,transparent_100%)] opacity-50 pointer-events-none" aria-hidden="true" />

      <motion.div
        style={{ y: prefersReducedMotion ? 0 : yParallax, opacity: opacityFade }}
        className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10 h-full transform-gpu"
      >
        <div className="w-full flex flex-col items-center justify-center min-h-[75vh] lg:min-h-[100svh] relative">
          
          <div className="flex flex-col items-center text-center max-w-3xl w-full relative z-30 pointer-events-auto">
            <motion.h1
              id={titleId}
              initial="hidden" animate="visible" variants={fadeUpVariant}
              className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tighter text-white leading-[1.05] mb-6 font-sans drop-shadow-2xl"
            >
              Shopping at the <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-zinc-400 drop-shadow-[0_0_15px_rgba(255,255,255,0.15)]">
                speed of thought.
              </span>
            </motion.h1>

            <motion.p
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.1 }}
              className="text-sm sm:text-lg md:text-xl text-zinc-300 mb-10 leading-relaxed font-light max-w-lg mx-auto"
            >
              Tell our AI exactly what you need. We secure the best deal across our global inventory and drop it at your door in minutes.
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
                <div className={`absolute -inset-[1px] rounded-[73px] blur-md transition-all duration-1000 -z-10 ${cartItemsCount > 0 ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 opacity-100' : 'bg-gradient-to-r from-cyan-500/40 to-purple-500/40 opacity-80 group-hover:-inset-[3px] group-hover:opacity-100 group-hover:blur-xl'}`} aria-hidden="true" />

                <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-zinc-800/80 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0 transform-gpu relative">
                  <Bot size={18} strokeWidth={1.5} className="sm:w-6 sm:h-6" aria-hidden="true" />
                  {cartItemsCount > 0 && (
                    <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-black text-[#050505] shadow-[0_0_10px_rgba(6,182,212,0.8)]" aria-hidden="true">
                      {cartItemsCount}
                    </motion.span>
                  )}
                </div>

                <div className="flex-1 px-3 sm:px-4 min-w-0 text-left" aria-live="polite">
                  <p className={`text-[11px] sm:text-sm md:text-base font-light truncate transition-colors ${cartItemsCount > 0 ? 'text-cyan-200 font-medium' : 'text-zinc-300'}`}>
                    {cartItemsCount > 0 ? "Your order is ready. Tap to review." : "I need noise-canceling headphones..."}
                  </p>
                </div>

                <span className="flex items-center justify-center gap-2 px-4 sm:px-6 py-3 sm:py-3 rounded-full bg-white text-black font-bold text-[10px] sm:text-sm hover:bg-cyan-50 hover:text-cyan-900 transition-colors shrink-0 whitespace-nowrap shadow-lg shadow-white/10 transform-gpu pointer-events-none">
                  {cartItemsCount > 0 ? "Confirm Order!" : "order with air"}
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
              {HERO_CARDS.map((card, idx) => (
                <HeroFloatingCard key={idx} {...card} />
              ))}
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
});
HeroSection.displayName = 'HeroSection';

// ============================================================================
// --- 2. GLOBAL SCALE SECTION ---
// ============================================================================

const AnimatedCounter = memo(({ value, text, icon: Icon }: { value: number, text: string, icon: React.ElementType }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 80 });

  useEffect(() => {
    if (isInView) motionValue.set(value);
  }, [motionValue, isInView, value]);

  useEffect(() => {
    return springValue.on("change", (latest) => {
      if (ref.current) ref.current.textContent = Intl.NumberFormat('en-US').format(Math.round(latest));
    });
  }, [springValue]);

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className="relative group flex flex-col items-center p-6 rounded-[30px] bg-black/60 backdrop-blur-xl border border-purple-500/30 hover:border-purple-400/80 transition-all duration-500 overflow-hidden text-center transform-gpu"
      role="group"
      aria-label={`${value} ${text}`}
    >
      <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" aria-hidden="true" />
      <div className="mb-4 p-3 rounded-full bg-purple-950/50 border border-purple-400/20 text-purple-400 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(168,85,247,0.3)]" aria-hidden="true">
        <Icon size={28} />
      </div>
      <span ref={ref} className="text-4xl md:text-5xl font-black text-white tracking-tighter mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }} aria-hidden="true">0</span>
      <span className="text-sm text-purple-300/80 font-mono uppercase tracking-widest" aria-hidden="true">{text}</span>
    </motion.div>
  );
});
AnimatedCounter.displayName = 'AnimatedCounter';

const Globe = memo(() => {
  const globeRef = useRef<THREE.Group>(null);
  const pulseRefs = useRef<(THREE.Mesh | null)[]>([]);
  const prefersReducedMotion = useReducedMotion();

  const { paths, pulseTrajectories } = useMemo(() => {
    const points = [
      { lat: 40.7128, lon: -74.0060 }, { lat: 51.5074, lon: -0.1278 },
      { lat: 35.6895, lon: 139.6917 }, { lat: 25.2048, lon: 55.2708 },
      { lat: 1.3521, lon: 103.8198 }, { lat: 30.0444, lon: 31.2357 },
    ];
    const radius = 5;
    const getPos = (lat: number, lon: number) => {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      return new THREE.Vector3(
        -(radius * Math.sin(phi) * Math.cos(theta)),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta)
      );
    };

    const routes: THREE.Vector3[][] = [];
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        routes.push([getPos(points[i].lat, points[i].lon), getPos(points[j].lat, points[j].lon)]);
      }
    }

    const curves = routes.map(([v1, v2]) => {
      const dist = v1.distanceTo(v2);
      const midPoint = new THREE.Vector3().addVectors(v1, v2).multiplyScalar(0.5).normalize().multiplyScalar(radius + (dist * 0.4));
      return new THREE.CatmullRomCurve3([v1, midPoint, v2]);
    });

    const segments = 200;
    const trajectories = curves.map(curve => {
      const pts = curve.getPoints(segments);
      return pts.map(p => ({ x: p.x, y: p.y, z: p.z }));
    });

    return { paths: curves, pulseTrajectories: trajectories };
  }, []);

  const sphereGeo = useMemo(() => new THREE.SphereGeometry(5, 32, 32), []);
  const haloGeo = useMemo(() => new THREE.SphereGeometry(5, 24, 24), []);
  const pulseGeo = useMemo(() => new THREE.SphereGeometry(0.08, 12, 12), []);
  const tubeGeos = useMemo(() => paths.map(curve => new THREE.TubeGeometry(curve, 24, 0.02, 3, false)), [paths]);

  useEffect(() => {
    return () => {
      sphereGeo.dispose();
      haloGeo.dispose();
      pulseGeo.dispose();
      tubeGeos.forEach(g => g.dispose());
    };
  }, [sphereGeo, haloGeo, pulseGeo, tubeGeos]);

  useFrame((state, delta) => {
    if (prefersReducedMotion) return;
    const safeDelta = Math.min(delta, 0.1);
    if (globeRef.current) globeRef.current.rotation.y += safeDelta * 0.05;

    const time = state.clock.elapsedTime;
    for (let i = 0; i < pulseRefs.current.length; i++) {
      const mesh = pulseRefs.current[i];
      if (!mesh) continue;
      const loopTime = 6 + (i % 3);
      const t = (time % loopTime) / loopTime;
      const exactIndex = Math.floor(t * 200);
      const target = pulseTrajectories[i][exactIndex];
      if (target) {
        mesh.position.set(target.x, target.y, target.z);
      }
    }
  });

  return (
    <group ref={globeRef}>
      <mesh geometry={sphereGeo}>
        <meshStandardMaterial color="#1e3a8a" emissive="#172554" emissiveIntensity={0.5} roughness={0.4} metalness={0.6} />
      </mesh>
      <mesh scale={[1.05, 1.05, 1.05]} geometry={haloGeo}>
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.15} side={THREE.BackSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <mesh scale={[1.2, 1.2, 1.2]} geometry={haloGeo}>
        <meshBasicMaterial color="#a855f7" transparent opacity={0.05} side={THREE.BackSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {tubeGeos.map((tubeGeo, i) => (
        <group key={i}>
          <mesh geometry={tubeGeo}>
            <meshBasicMaterial color="#d8b4fe" transparent opacity={0.6} blending={THREE.AdditiveBlending} depthWrite={false} />
          </mesh>
          <mesh ref={(el) => { pulseRefs.current[i] = el; }} geometry={pulseGeo}>
            <meshBasicMaterial color="#ffffff" toneMapped={false} />
          </mesh>
        </group>
      ))}
    </group>
  );
});
Globe.displayName = 'Globe';

const GlobalScaleSection = memo(() => {
  return (
    <section className="relative min-h-[100svh] w-full overflow-hidden bg-black flex flex-col justify-between pb-10" style={{ contain: 'content' }} aria-label="Global Scale Statistics">
      <div className="absolute inset-0 z-0 transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
        <Canvas {...globeCanvasConfig} dpr={[1, 1.5]} performance={{ min: 0.5 }}>
          <ambientLight intensity={0.4} />
          <directionalLight position={[10, 10, 5]} intensity={2} color="#a855f7" />
          <directionalLight position={[-10, -10, -5]} intensity={2} color="#3b82f6" />
          <ParticleField count={5000} radius={56} color="#e9d5ff" size={0.05} rotationSpeed={{ x: 0.0001, y: 0.0001, z: 0.001 }} position={[0, 0, -40]} />
          <Float speed={1} rotationIntensity={0.1} floatIntensity={0.2}>
            <group position={[5.5, 0, 0]}><Globe /></group>
          </Float>
          <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.2} maxPolarAngle={Math.PI / 1.6} minPolarAngle={Math.PI / 3} />
          <Preload all />
        </Canvas>
        <div className="absolute inset-0 bg-gradient-to-r from-black via-transparent to-transparent pointer-events-none" />
      </div>

      <div className="relative z-10 container mx-auto px-6 pt-24 lg:pt-32 pointer-events-none grow flex items-center">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 w-full">
          <div className="pointer-events-auto max-w-xl">
            <motion.div
              initial={{ opacity: 0, x: -50 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.8 }}
              className="transform-gpu"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]" aria-hidden="true">
                  <GlobeIcon className="text-purple-400" size={20} />
                </div>
                <span className="text-sm font-mono text-purple-400 uppercase tracking-[0.3em] drop-shadow-md">Next-Gen Logistics</span>
              </div>

              <h2 className="text-5xl md:text-7xl font-black text-white mb-6 leading-[0.9] tracking-tighter" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                URBAN<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-pink-500 to-purple-600">
                  SCALE
                </span>
              </h2>

              <p className="text-lg text-gray-300 font-light leading-relaxed mb-6 border-l-4 border-purple-500/50 pl-6 drop-shadow-lg">
                Our decentralized network of strategic hubs brings inventory closer to you. Bypassing traditional bottlenecks to deliver directly to your exact location with pinpoint accuracy. <br />
                <span className="text-white font-bold">Zero Latency. Seamless Coverage.</span>
              </p>
            </motion.div>
          </div>
        </div>
      </div>

      <div className="relative z-10 container mx-auto px-6 mt-12 pointer-events-auto">
        <motion.div
          initial={{ opacity: 0, y: 50 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.3, duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto transform-gpu"
        >
          <AnimatedCounter value={263} text="Active Drones" icon={Rocket} />
          <AnimatedCounter value={3} text="Connected Cities" icon={MapIcon} />
          <AnimatedCounter value={1863} text="Successful Drops" icon={CheckCircle2} />
        </motion.div>
      </div>
    </section>
  );
});
GlobalScaleSection.displayName = 'GlobalScaleSection';

// ============================================================================
// --- 3. HOW IT WORKS SECTION ---
// ============================================================================

const HolographicStepCard = memo(({ item, isLast }: { 
  item: { icon: React.ElementType, step: string, title: string, description: string }; 
  isLast: boolean; 
}) => {
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
            <span className="font-mono text-sm md:text-lg font-black text-cyan-300 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]">{item.step}</span>
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
              <h3 className="mb-3 text-2xl md:text-4xl font-bold tracking-tight text-white group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-cyan-200 transition-all duration-500" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                <span className="sr-only">Step {item.step}: </span>{item.title}
              </h3>
              <p className="text-sm md:text-lg font-light leading-relaxed text-gray-400 group-hover:text-gray-300 transition-colors duration-500">
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
    <section ref={containerRef} className="relative min-h-screen w-full overflow-hidden bg-[#050505] py-32 lg:py-48 border-t border-white/5" style={{ contain: 'content' }} aria-labelledby="how-it-works-heading">
      <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
        <motion.div style={{ y: prefersReducedMotion ? 0 : yParallax }} className="absolute inset-0 transform-gpu">
          <div className="absolute top-[10%] left-[-20%] w-[60%] h-[60%] rounded-full bg-cyan-600/10 blur-[150px] mix-blend-screen transform-gpu" />
          <div className="absolute bottom-[10%] right-[-20%] w-[60%] h-[60%] rounded-full bg-purple-600/10 blur-[150px] mix-blend-screen transform-gpu" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_10%,transparent_100%)] opacity-50" />
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
            className="text-5xl md:text-7xl lg:text-8xl font-black leading-[0.9] tracking-tighter text-white drop-shadow-2xl transform-gpu"
          >
            <span style={{ fontFamily: "'Orbitron', sans-serif" }}>HOW IT</span> <br className="md:hidden" />
            <span className="bg-gradient-to-r from-cyan-400 via-white to-purple-500 bg-clip-text text-transparent px-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              WORKS
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.2, duration: 0.8 }}
            className="mt-8 max-w-2xl text-lg md:text-xl font-light leading-relaxed text-gray-400 transform-gpu"
          >
            Watch how our neural network translates your thoughts into a physical product at your door in under 15 minutes.
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
// --- 4. FINAL CTA & TRUSTED BY ---
// ============================================================================

const FinalCTA = memo(() => (
  <section className="relative w-full py-32 overflow-hidden bg-black flex items-center justify-center border-t border-white/5" style={{ contain: 'content' }} aria-labelledby="cta-heading">
    <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }} aria-hidden="true">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20" />
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

        <h2 id="cta-heading" className="text-5xl md:text-8xl font-black text-white mb-8 tracking-tighter leading-[0.9]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
          YOUR ORDER.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-purple-400 drop-shadow-[0_0_40px_rgba(192,132,252,0.5)]">
            IN THE SKY.
          </span>
        </h2>

        <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto mb-12 font-light leading-relaxed">
          Don't wait for traffic. Shop thousands of products and watch them arrive from the clouds in minutes.
        </p>

        <div className="flex flex-col gap-6 justify-center items-center">
          <Link href="/profile" className="group relative px-12 py-7 bg-white text-black font-black text-xl rounded-full overflow-hidden transition-all duration-300 hover:shadow-[0_0_50px_rgba(255,255,255,0.4)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 transform-gpu">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-purple-500 opacity-0 group-hover:opacity-20 transition-opacity duration-300" aria-hidden="true" />
            <span className="relative flex items-center gap-3">
              SIGN UP <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
            </span>
          </Link>
          <button className="group px-12 py-7 text-white font-bold text-xl rounded-full border border-white/10 hover:bg-white/5 hover:border-cyan-400/50 transition-all duration-300 flex items-center gap-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4 transform-gpu">
            <span>DOWNLOAD APP</span><ArrowDown className="w-6 h-6 group-hover:translate-y-1 transition-transform" aria-hidden="true" />
          </button>
        </div>
        <p className="mt-12 text-[10px] text-gray-600 font-mono uppercase tracking-[0.2em]">Instant Delivery • Live Tracking • 100% Autonomous</p>
      </motion.div>
    </div>
  </section>
));
FinalCTA.displayName = 'FinalCTA';

const TrustedBySection = memo(() => {
  const companies = ["NVIDIA", "STRIPE", "AWS", "CLOUDFLARE", "MASTERCARD"];
  return (
    <section className="py-12 bg-black border-y border-white/5 overflow-hidden relative" style={{ contain: 'content' }} aria-label="Trusted Partners">
      <div className="absolute inset-0 bg-cyan-900/5 blur-3xl pointer-events-none transform-gpu" aria-hidden="true" />
      <div className="container mx-auto px-4 mb-6 text-center relative z-10">
        <p className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.3em]" aria-hidden="true">Trusted by Industry Leaders</p>
        <span className="sr-only">Trusted by NVIDIA, STRIPE, AWS, CLOUDFLARE, and MASTERCARD.</span>
      </div>
      <div className="relative flex overflow-x-hidden group">
        <div className="absolute top-0 left-0 h-full w-24 bg-gradient-to-r from-black to-transparent z-10 pointer-events-none" aria-hidden="true" />
        <div className="absolute top-0 right-0 h-full w-24 bg-gradient-to-l from-black to-transparent z-10 pointer-events-none" aria-hidden="true" />
        
        <div className="flex gap-16 items-center hover:[animation-play-state:paused] transform-gpu" style={{ animation: 'marquee 25s linear infinite' }} aria-hidden="true">
          {[...companies, ...companies, ...companies, ...companies].map((company, index) => (
            <span key={index} className="text-xl md:text-2xl font-bold text-gray-800 uppercase tracking-tighter hover:text-cyan-400 transition-colors duration-500 cursor-default select-none whitespace-nowrap" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {company}
            </span>
          ))}
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
      `}} />
    </section>
  );
});
TrustedBySection.displayName = 'TrustedBySection';

// ============================================================================
// --- MAIN CLIENT EXPORT ---
// ============================================================================

export function LandingClient({ nonce, initialTraceId }: { nonce: string; initialTraceId: string }) {
  const [uiState, dispatch] = useReducer(uiFSMReducer, { status: 'IDLE', activeTraceId: initialTraceId });
  const { isMobile, isStandalone, mounted } = useDeviceDetection();
  
  // Stores synchronization
  const { setOverlayVisible } = useAIOrderingStore();
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
    return <div className="min-h-screen w-full bg-black" aria-hidden="true" />;
  }

  if (uiState.status === 'MOBILE_PWA_VIEW') {
    return <MobileLandingView />;
  }

  const handleOrderClick = () => {
    const actionTraceId = crypto.randomUUID();
    dispatch({ type: 'OPEN_AI_CART', payload: { traceId: actionTraceId } });
    setOverlayVisible(true);
  };

  const handleExploreClick = () => {
    const actionTraceId = crypto.randomUUID();
    dispatch({ type: 'OPEN_PRODUCTS', payload: { traceId: actionTraceId } });
    showProductOverlay();
  };

  const handleClose = () => {
    dispatch({ type: 'CLOSE_OVERLAYS' });
    setOverlayVisible(false);
    hideProductOverlay();
  };

  return (
    <RUMErrorBoundary traceId={initialTraceId} fallback={<div className="p-8 text-center text-white">System telemetry interruption. Please refresh.</div>}>
      <div className="min-h-screen w-full text-gray-100 overflow-x-hidden bg-black" style={{ fontFamily: "'Montserrat', sans-serif" }}>
        <main className="relative z-10 w-full transform-gpu">
          <HeroSection onOrderClick={handleOrderClick} onExploreClick={handleExploreClick} />
          <GlobalScaleSection />
          <HowItWorksSection />
          <FinalCTA />
          <TrustedBySection />
        </main>

        <ProductOverlay isOpen={uiState.status === 'PRODUCT_OVERLAY_ACTIVE'} onClose={handleClose} />
        <AIChatOverlay isOpen={uiState.status === 'AI_OVERLAY_ACTIVE'} onClose={handleClose} />
      </div>
    </RUMErrorBoundary>
  );
}
