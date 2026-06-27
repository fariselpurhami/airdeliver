///** apps/web/app/(main)/page.tsx **//

'use client';

import Image from "next/image";
import Link from 'next/link';
import React, { Suspense, useRef, useMemo, useEffect, useState, memo } from 'react';
import dynamic from 'next/dynamic';
import { motion, useScroll, useSpring, useInView, useTransform, useMotionValue } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload, Float, OrbitControls, Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';

// Icons
import { 
  ShieldCheck, Lock, Clock, MapIcon, Quote, GlobeIcon, 
  CheckCircle2, Activity, Bot, ChevronRight, Leaf, Rocket, 
  Zap, ArrowRight, Cpu, ArrowDown, Star 
} from 'lucide-react';

// Store & Components
import { useUIStore } from '@/hooks/useUIStore';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import CinematicBackground from '@/components/ui/CinematicBackground';
import ProductOverlay from '@/components/products/ProductOverlay';

// ============================================================================
// --- GLOBAL CONFIG & PRIMITIVES ---
// ============================================================================

const premiumEasing = [0.16, 1, 0.3, 1];
const fadeUpVariant = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: premiumEasing } }
};

const canvasConfig = {
  camera: { position: [0, 0, 15] as [number, number, number], fov: 75 },
  dpr: [1, 1.5] as [number, number], // Crucial: Clamps pixel ratio for mobile performance
  gl: { antialias: false, powerPreference: "high-performance" as const, alpha: true },
};

// Reusable math function for spherical particle distribution
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

type ParticleFieldProps = {
  count: number;
  radius: number;
  color: string;
  size: number;
  rotationSpeed: { x: number; y: number; z: number };
  position?: [number, number, number];
};

// Unified, high-performance particle field component
const ParticleField = memo(({ count, radius, color, size, rotationSpeed, position = [0, 0, -60] }: ParticleFieldProps) => {
  const groupRef = useRef<THREE.Group>(null!);
  const positions = useMemo(() => createParticlePositions(count, radius), [count, radius]);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const safeDelta = Math.min(delta, 0.1); // Prevent massive jumps on thread lag
    groupRef.current.rotation.x += safeDelta * rotationSpeed.x;
    groupRef.current.rotation.y += safeDelta * rotationSpeed.y;
    groupRef.current.rotation.z += safeDelta * rotationSpeed.z;
  });

  return (
    <group ref={groupRef} position={position}>
      <Points positions={positions} stride={3} frustumCulled={false}>
        <PointMaterial
          transparent
          color={color}
          size={size}
          sizeAttenuation
          depthWrite={false}
          toneMapped={false}
          opacity={0.8}
        />
      </Points>
    </group>
  );
});
ParticleField.displayName = 'ParticleField';

const CheckCircleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
    <path d="m9 11 3 3L22 4"/>
  </svg>
);

// ============================================================================
// --- 1. HERO SECTION ---
// ============================================================================

const HeroSection = memo(({ onOrderClick, onExploreClick }: { onOrderClick: () => void; onExploreClick: () => void }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end start'] });
  const yParallax = useTransform(scrollYProgress, [0, 1], ['0%', '25%']);
  const opacityFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <section ref={containerRef} className="relative min-h-[100svh] w-full bg-[#050505] overflow-hidden flex items-center pt-28 pb-16 lg:pt-0 lg:pb-0">
      <div className="absolute inset-0 z-0 pointer-events-none" aria-hidden="true">
        <Suspense fallback={null}>
          <Canvas {...canvasConfig}>
            <ParticleField 
              count={150000} // Reduced from 150k for massive perf gain, visuals preserved via size
              radius={66} 
              color="#ffffff" 
              size={0.05} 
              rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.001 }} 
            />
            <Preload all />
          </Canvas>
        </Suspense>
      </div>

      <div className="absolute top-[-10%] left-[-20%] w-[70%] h-[70%] rounded-full bg-cyan-600/15 blur-[120px] pointer-events-none mix-blend-screen transform-gpu" />
      <div className="absolute bottom-[-10%] right-[-20%] w-[70%] h-[70%] rounded-full bg-purple-600/15 blur-[120px] pointer-events-none mix-blend-screen transform-gpu" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,#000_20%,transparent_100%)] opacity-50 pointer-events-none" />

      <motion.div
        style={{ y: yParallax, opacity: opacityFade, willChange: 'transform, opacity' }}
        className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10"
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          
          <div className="flex flex-col items-start max-w-2xl mt-8 lg:mt-0">
            <motion.h1
              initial="hidden" animate="visible" variants={fadeUpVariant}
              className="text-[11vw] sm:text-6xl lg:text-7xl font-black tracking-tighter text-white leading-[1.05] mb-6 font-sans drop-shadow-2xl"
            >
              Shopping at the <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-zinc-400 drop-shadow-[0_0_15px_rgba(255,255,255,0.15)]">
                speed of thought.
              </span>
            </motion.h1>

            <motion.p
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.1 }}
              className="text-base sm:text-lg md:text-xl text-zinc-300 mb-10 leading-relaxed font-light max-w-lg shadow-black"
            >
              Tell our AI exactly what you need. We secure the best deal across our global inventory and drop it at your door in minutes.
            </motion.p>

            <motion.div
              initial="hidden" animate="visible" variants={fadeUpVariant} transition={{ delay: 0.2 }}
              className="w-full max-w-xl"
            >
              <div
                onClick={onOrderClick}
                className="group relative flex items-center p-1.5 sm:p-2 rounded-[73px] bg-zinc-900/70 border border-white/10 backdrop-blur-2xl shadow-[0_0_40px_rgba(0,0,0,0.8)] transition-all duration-500 hover:border-cyan-500/50 hover:bg-zinc-900/90 cursor-text"
              >
                <div className="absolute -inset-[1px] bg-gradient-to-r from-cyan-500/40 to-purple-500/40 rounded-[73px] opacity-80 blur-md transition-all duration-500 group-hover:-inset-[3px] group-hover:opacity-100 group-hover:blur-xl -z-10 transform-gpu" />
                <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-zinc-800/80 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0">
                  <Bot size={20} strokeWidth={1.5} className="sm:w-6 sm:h-6" />
                </div>

                <div className="flex-1 px-3 sm:px-4 min-w-0">
                  <p className="text-zinc-300 text-[11px] sm:text-sm md:text-base font-light truncate">
                    I need noise-canceling headphones...
                  </p>
                </div>

                <button
                  className="flex items-center justify-center gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-full bg-white text-black font-bold text-[11px] sm:text-sm hover:bg-cyan-50 hover:text-cyan-900 transition-colors shrink-0 whitespace-nowrap shadow-lg shadow-white/10"
                >
                  order with air
                </button>
              </div>

              <div className="mt-6 flex items-center gap-6 pl-2">
                <button onClick={onExploreClick} className="text-xs sm:text-sm font-medium text-zinc-300 hover:text-cyan-300 transition-colors flex items-center gap-1 group">
                  Explore trending products <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </motion.div>
          </div>

          <div className="relative h-[400px] sm:h-[500px] lg:h-[700px] w-full flex items-center justify-center perspective-1000 mt-8 lg:mt-0">
            <motion.div
              initial={{ opacity: 0, scale: 0.9, rotateY: 10 }}
              animate={{ opacity: 1, scale: 1, rotateY: 0 }}
              transition={{ duration: 1.2, ease: premiumEasing, delay: 0.2 }}
              className="relative w-full max-w-md h-full flex items-center justify-center"
              style={{ willChange: "transform, opacity" }}
            >
              {/* Product Card 1 */}
              <div className="absolute z-20 w-[60%] sm:w-72 md:w-80 aspect-[4/5] rounded-[32px] bg-zinc-900 border border-white/15 p-3 sm:p-4 shadow-[0_30px_60px_rgba(0,0,0,0.8)] overflow-hidden group transform-gpu">
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/20 to-transparent z-10" />
                <Image
                  src="https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop"
                  alt="Apple Vision Pro"
                  fill
                  priority
                  sizes="(max-width: 768px) 60vw, 30vw"
                  className="object-cover transition-transform duration-700 group-hover:scale-105"
                />
                <div className="absolute bottom-4 sm:bottom-6 left-4 sm:left-6 right-4 sm:right-6 z-20 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-2 sm:gap-0">
                  <div>
                    <h3 className="text-white font-bold text-sm sm:text-lg tracking-tight">Apple Vision Pro</h3>
                    <p className="text-zinc-300 text-[10px] sm:text-sm font-medium">Arriving in 12 min</p>
                  </div>
                  <div className="px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/30 text-white font-bold text-xs sm:text-sm shadow-lg">
                    $348
                  </div>
                </div>
              </div>

              {/* Product Card 2 */}
              <motion.div
                animate={{ y: [0, -12, 0] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="absolute left-[2%] top-[10%] z-10 aspect-square w-[35%] overflow-hidden rounded-3xl border border-white/15 bg-zinc-900 p-2 shadow-2xl sm:-left-[10%] sm:top-[12%] sm:w-48 sm:p-3"
                style={{ willChange: "transform" }}
              >
                <img src="https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop" alt="Smart Watch" loading="lazy" decoding="async" className="absolute inset-0 w-full h-full object-cover opacity-70" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 to-transparent" />
                <div className="absolute bottom-2 sm:bottom-3 left-2 sm:left-3 text-white text-[9px] sm:text-xs font-bold px-2 py-1 bg-black/60 backdrop-blur-md rounded-lg border border-white/10 shadow-lg">
                  Best Deal!
                </div>
              </motion.div>

              {/* Product Card 3 */}
              <motion.div
                animate={{ y: [0, 12, 0] }} transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                className="absolute bottom-[5%] sm:-bottom-[2%] right-[2%] sm:-right-[10%] w-[42%] sm:w-56 aspect-[4/3] rounded-3xl bg-zinc-900 border border-white/15 shadow-2xl z-30 overflow-hidden"
                style={{ willChange: "transform" }}
              >
                <img src="https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop" alt="Nike Sneakers" loading="lazy" decoding="async" className="absolute inset-0 w-full h-full object-cover opacity-90" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent" />
                <div className="absolute bottom-3 sm:bottom-4 left-3 sm:left-4 right-3 sm:right-4 flex items-center justify-between">
                   <p className="text-white text-[10px] sm:text-sm font-bold tracking-tight">Nike Air Max</p>
                   <div className="flex items-center gap-1 text-cyan-400 text-[9px] sm:text-xs font-medium">
                     <CheckCircleIcon />
                     <span className="hidden sm:inline">In Stock</span>
                   </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
});
HeroSection.displayName = 'HeroSection';

// ============================================================================
// --- 2. HOW IT WORKS SECTION (THE MAGICAL REDESIGN) ---
// ============================================================================

const PRODUCTION_STEPS = [
  { icon: Bot, step: "01", title: "AI Intent Recognition", description: "Simply type or speak your order. Our neural engine parses your intent instantly, finding the exact product in our global network without you scrolling through catalogs." },
  { icon: Cpu, step: "02", title: "Global Inventory Sync", description: "Within milliseconds, the system queries local hubs and global databases to secure the best price and immediate availability, reserving your item autonomously." },
  { icon: MapIcon, step: "03", title: "4D Route Computation", description: "An adaptive flight plan is generated. The AI factors in live weather layers, urban topology, and airspace corridors to chart the absolute fastest drone vector." },
  { icon: Rocket, step: "04", title: "Precision Doorstep Drop", description: "The autonomous drone arrives. Using computer vision and micro-thruster stabilization, it completes a contactless, verified handoff directly to your location." },
];

const HolographicStepCard = memo(({ item, index, isLast }: { item: typeof PRODUCTION_STEPS[0], index: number, isLast: boolean }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: cardRef, offset: ["start 95%", "center center"] });

  // سحر الفريمر موشن لدمج تأثيرات الـ Hero مع السكرول
  const opacity = useTransform(scrollYProgress, [0, 0.6, 1], [0, 0.5, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [80, 0]);
  const rotateX = useTransform(scrollYProgress, [0, 1], [15, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], [0.9, 1]);
  const glowLine = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  const Icon = item.icon;

  return (
    <div ref={cardRef} className="relative flex w-full gap-6 md:gap-12 pb-24 md:pb-32 last:pb-0 perspective-1000">

      {/* 1. مسار الطيران (The Flight Path) */}
      <div className="relative flex shrink-0 flex-col items-center">
        {/* الماسة المتوهجة */}
        <motion.div
          style={{ scale, opacity }}
          className="z-10 flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-2xl border border-cyan-400/40 bg-black/50 shadow-[0_0_30px_rgba(6,182,212,0.3)] backdrop-blur-md rotate-45 transform-gpu"
        >
          <div className="-rotate-45 flex flex-col items-center">
            <span className="font-mono text-sm md:text-lg font-black text-cyan-300 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]">{item.step}</span>
          </div>
        </motion.div>

        {/* خط الليزر الذي يمتلئ مع السكرول */}
        {!isLast && (
          <div className="absolute top-14 md:top-20 bottom-[-6rem] md:bottom-[-8rem] w-[2px] bg-white/5">
            <motion.div
              style={{ height: glowLine }}
              className="w-full bg-gradient-to-b from-cyan-400 via-purple-500 to-transparent shadow-[0_0_10px_rgba(6,182,212,0.8)]"
            />
          </div>
        )}
      </div>

      {/* 2. البطاقة الهولوجرامية (Holographic Panel) */}
      <motion.div
        style={{ opacity, y, rotateX, willChange: 'transform, opacity' }}
        className="flex-1 mt-2 md:mt-4"
      >
        <div className="group relative overflow-hidden rounded-[32px] border border-white/10 bg-gradient-to-br from-white/[0.03] to-transparent p-6 md:p-10 backdrop-blur-xl transition-all duration-700 hover:border-cyan-400/40 hover:bg-white/[0.05] shadow-2xl">
          {/* إضاءة خلفية للبطاقة تظهر عند التمرير */}
          <div className="absolute -inset-px bg-gradient-to-r from-cyan-500/15 to-purple-500/15 opacity-0 group-hover:opacity-100 blur-2xl transition-all duration-700 transform-gpu" />

          <div className="relative z-10 flex flex-col md:flex-row gap-6 md:gap-8 items-start md:items-center">
            {/* الأيقونة */}
            <div className="flex items-center justify-center h-14 w-14 md:h-20 md:w-20 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.2)] group-hover:scale-110 group-hover:shadow-[0_0_30px_rgba(168,85,247,0.4)] transition-all duration-500 shrink-0">
              <Icon size={32} strokeWidth={1.5} className="group-hover:text-purple-300 transition-colors" />
            </div>

            {/* النصوص */}
            <div>
              <h3 className="mb-3 text-2xl md:text-4xl font-bold tracking-tight text-white group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-cyan-200 transition-all duration-500" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                {item.title}
              </h3>
              <p className="text-sm md:text-lg font-light leading-relaxed text-gray-400 group-hover:text-gray-300 transition-colors duration-500">
                {item.description}
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
});
HolographicStepCard.displayName = 'HolographicStepCard';

const HowItWorksSection = memo(() => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start end", "end start"] });
  const yParallax = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);

  return (
    <section ref={containerRef} className="relative min-h-screen w-full overflow-hidden bg-[#050505] py-32 lg:py-48 border-t border-white/5">
      {/* 1. الخلفية السحرية المدمجة من الـ Hero والـ Global Scale */}
      <div className="absolute inset-0 z-0 pointer-events-none" aria-hidden="true">
        <motion.div style={{ y: yParallax }} className="absolute inset-0">
          <div className="absolute top-[10%] left-[-20%] w-[60%] h-[60%] rounded-full bg-cyan-600/10 blur-[150px] mix-blend-screen" />
          <div className="absolute bottom-[10%] right-[-20%] w-[60%] h-[60%] rounded-full bg-purple-600/10 blur-[150px] mix-blend-screen" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_10%,transparent_100%)] opacity-50" />
        </motion.div>
      </div>

      <div className="container relative z-10 mx-auto px-5 sm:px-6 lg:px-12">
        {/* 2. عنوان القسم (Massive & Cinematic) */}
        <div className="text-center mb-24 md:mb-32 flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }}
            className="mb-8 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/30 px-5 py-2 backdrop-blur-md shadow-[0_0_20px_rgba(6,182,212,0.2)]"
          >
            <Activity size={16} className="animate-pulse text-cyan-400" />
            <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-cyan-300">Autonomy Protocol v2.0</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1, duration: 0.8 }}
            className="text-5xl md:text-7xl lg:text-8xl font-black leading-[0.9] tracking-tighter text-white drop-shadow-2xl"
            style={{ fontFamily: "'Orbitron', sans-serif" }}
          >
            HOW IT <br className="md:hidden" />
            <span className="bg-gradient-to-r from-cyan-400 via-white to-purple-500 bg-clip-text text-transparent px-2">
              WORKS
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.2, duration: 0.8 }}
            className="mt-8 max-w-2xl text-lg md:text-xl font-light leading-relaxed text-gray-400"
          >
            Watch how our neural network translates your thoughts into a physical product at your door in under 15 minutes.
          </motion.p>
        </div>

        {/* 3. الخطوات الهولوجرامية */}
        <div className="max-w-4xl mx-auto">
          {PRODUCTION_STEPS.map((step, index) => (
            <HolographicStepCard key={step.step} item={step} index={index} isLast={index === PRODUCTION_STEPS.length - 1} />
          ))}
        </div>
      </div>
    </section>
  );
});
HowItWorksSection.displayName = 'HowItWorksSection';

// ============================================================================
// --- 3. GLOBAL SCALE SECTION ---
// ============================================================================

const AnimatedCounter = memo(({ value, text, icon: Icon }: { value: number, text: string, icon: any }) => {
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
    >
        <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="mb-4 p-3 rounded-full bg-purple-950/50 border border-purple-400/20 text-purple-400 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(168,85,247,0.3)]">
            <Icon size={28} />
        </div>
        <span ref={ref} className="text-4xl md:text-5xl font-black text-white tracking-tighter mb-2" style={{fontFamily: "'Orbitron', sans-serif"}}>0</span>
        <span className="text-sm text-purple-300/80 font-mono uppercase tracking-widest">{text}</span>
    </motion.div>
  );
});
AnimatedCounter.displayName = 'AnimatedCounter';

const Globe = memo(() => {
  const globeRef = useRef<THREE.Group>(null!);
  const [paths, setPaths] = useState<THREE.CatmullRomCurve3[]>([]);
  const pulseRefs = useRef<THREE.Mesh[]>([]);

  useEffect(() => {
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

    const routes = [];
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        routes.push([points[i], points[j]]);
      }
    }

    const curves = routes.map(([p1, p2]) => {
      const v1 = getPos(p1.lat, p1.lon);
      const v2 = getPos(p2.lat, p2.lon);
      const dist = v1.distanceTo(v2);
      const midPoint = new THREE.Vector3().addVectors(v1, v2).multiplyScalar(0.5).normalize().multiplyScalar(radius + (dist * 0.4));
      return new THREE.CatmullRomCurve3([v1, midPoint, v2]);
    });

    setPaths(curves);
    pulseRefs.current = new Array(curves.length);
  }, []);

  useFrame((state, delta) => {
    const safeDelta = Math.min(delta, 0.1);
    if (globeRef.current) globeRef.current.rotation.y += safeDelta * 0.05;

    pulseRefs.current.forEach((mesh, i) => {
      if (mesh && paths[i]) {
        const loopTime = 6 + (i % 3);
        const t = (state.clock.elapsedTime % loopTime) / loopTime;
        paths[i].getPointAt(t, mesh.position);
      }
    });
  });

  return (
    <group ref={globeRef}>
      <mesh>
        <sphereGeometry args={[5, 48, 48]} />
        <meshPhysicalMaterial color="#1e3a8a" emissive="#172554" emissiveIntensity={0.5} roughness={0.4} metalness={0.6} clearcoat={1} clearcoatRoughness={0.1} />
      </mesh>

      <mesh scale={[1.05, 1.05, 1.05]}>
        <sphereGeometry args={[5, 32, 32]} />
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.15} side={THREE.BackSide} blending={THREE.AdditiveBlending} />
      </mesh>

      <mesh scale={[1.2, 1.2, 1.2]}>
        <sphereGeometry args={[5, 32, 32]} />
        <meshBasicMaterial color="#a855f7" transparent opacity={0.05} side={THREE.BackSide} blending={THREE.AdditiveBlending} />
      </mesh>

      {paths.map((curve, i) => (
        <group key={i}>
          <mesh>
            <tubeGeometry args={[curve, 32, 0.02, 4, false]} />
            <meshBasicMaterial color="#d8b4fe" transparent opacity={0.6} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh ref={(el) => { if(el) pulseRefs.current[i] = el; }}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color="#ffffff" toneMapped={false} />
            {/* pointLight strictly removed for mobile render performance; basic material provides enough emissive glow */}
          </mesh>
        </group>
      ))}
    </group>
  );
});
Globe.displayName = 'Globe';

const GlobalScaleSection = memo(() => {
  return (
    <section className="relative min-h-screen w-full overflow-hidden bg-black flex flex-col justify-between pb-10">
      <div className="absolute inset-0 z-0">
        <Canvas {...canvasConfig} camera={{ position: [0, 0, 19], fov: 35 }}>
          <ambientLight intensity={0.4} />
          <directionalLight position={[10, 10, 5]} intensity={2} color="#a855f7" />
          <directionalLight position={[-10, -10, -5]} intensity={2} color="#3b82f6" />
          <ParticleField 
            count={100000}          // عدد النجوم
            radius={66}            // انتشار النجوم
            color="#e9d5ff"        // لون أبيض يميل للبنفسجي الفاتح جداً ليتناغم مع إضاءة الكوكب
            size={0.025}           // حجم صغير لتبدو بعيدة
            rotationSpeed={{ x: 0.0001, y: 0.0001, z: 0.001 }} // دوران بطيء جداً وهادئ
            position={[0, 0, -40]} // دفع النجوم للخلف بعيداً عن الكوكب
          />
          <Float speed={1} rotationIntensity={0.1} floatIntensity={0.2}>
            <group position={[5.5, 0, 0]}>
              <Suspense fallback={null}><Globe /></Suspense>
            </group>
          </Float>
          <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.2} maxPolarAngle={Math.PI / 1.6} minPolarAngle={Math.PI / 3}/>
        </Canvas>
        <div className="absolute inset-0 bg-gradient-to-r from-black via-transparent to-transparent pointer-events-none" />
      </div>

      <div className="relative z-10 container mx-auto px-6 pt-24 lg:pt-32 pointer-events-none grow flex items-center">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 w-full">
          <div className="pointer-events-auto max-w-xl">
            <motion.div
              initial={{ opacity: 0, x: -50 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.8 }}
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 shadow-[0_0_10px_rgba(168,85,247,0.2)] transform-gpu">
                  <GlobeIcon className="text-purple-400" size={20} />
                </div>
                <span className="text-sm font-mono text-purple-400 uppercase tracking-[0.3em] drop-shadow-md">Planetary Operations</span>
              </div>

              <h2 className="text-5xl md:text-7xl font-black text-white mb-6 leading-[0.9] tracking-tighter" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                GLOBAL<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-pink-500 to-purple-600">
                  SCALE
                </span>
              </h2>

              <p className="text-lg text-gray-300 font-light leading-relaxed mb-6 border-l-4 border-purple-500/50 pl-6 drop-shadow-lg">
                A synchronized autonomous network spanning continents. <br />
                <span className="text-white font-medium">Zero Latency. Infinite Reach.</span>
              </p>
            </motion.div>
          </div>
        </div>
      </div>

      <div className="relative z-10 container mx-auto px-6 mt-12 pointer-events-auto">
        <motion.div
          initial={{ opacity: 0, y: 50 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.3, duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          <AnimatedCounter value={1843} text="Active Drones" icon={Rocket} />
          <AnimatedCounter value={212} text="Connected Cities" icon={MapIcon} />
          <AnimatedCounter value={947204} text="Successful Drops" icon={CheckCircle2} />
        </motion.div>
      </div>
    </section>
  );
});
GlobalScaleSection.displayName = 'GlobalScaleSection';

// ============================================================================
// --- 5. FINAL CTA & PARTNERS ---
// ============================================================================

const FinalCTA = memo(() => (
  <section className="relative w-full py-32 overflow-hidden bg-black flex items-center justify-center border-t border-white/5">
    <div className="absolute inset-0 z-0 pointer-events-none">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[100px] transform-gpu" />
    </div>

    <div className="container mx-auto px-6 relative z-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 30 }} whileInView={{ opacity: 1, scale: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.8, ease: "easeOut" }}
        className="max-w-5xl mx-auto"
      >
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-950/30 border border-cyan-500/30 backdrop-blur-md mb-8 ring-1 ring-cyan-500/20 transform-gpu">
          <Zap size={14} className="text-yellow-400 fill-yellow-400" />
          <span className="text-xs font-mono text-cyan-300 uppercase tracking-widest">Next-Gen Shopping Experience</span>
        </div>

        <h2 className="text-5xl md:text-8xl font-black text-white mb-8 tracking-tighter leading-[0.9]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
          YOUR ORDER.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-purple-400 drop-shadow-[0_0_40px_rgba(192,132,252,0.5)]">
            IN THE SKY.
          </span>
        </h2>

        <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto mb-12 font-light leading-relaxed">
          Don't wait for traffic. Shop thousands of products and watch them arrive from the clouds in minutes.
        </p>

        <div className="flex flex-col gap-6 justify-center items-center">
          <Link href="/profile" className="group relative px-12 py-7 bg-white text-black font-black text-xl rounded-full overflow-hidden transition-all duration-300 hover:shadow-[0_0_50px_rgba(255,255,255,0.4)]">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-purple-500 opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
            <span className="relative flex items-center gap-3">
              SIGN UP <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
            </span>
          </Link>
          <button className="group px-12 py-7 text-white font-bold text-xl rounded-full border border-white/10 hover:bg-white/5 hover:border-cyan-400/50 transition-all duration-300 flex items-center gap-3">
            <span>DOWNLOAD</span><ArrowDown className="w-6 h-6 group-hover:translate-y-1 transition-transform" />
          </button>
        </div>
        <p className="mt-12 text-[10px] text-gray-600 font-mono uppercase tracking-[0.2em]">Instant Delivery • Live Tracking • 100% Autonomous</p>
      </motion.div>
    </div>
  </section>
));
FinalCTA.displayName = 'FinalCTA';

const TrustedBySection = memo(() => {
  const companies = [
    "NVIDIA",       
    "STRIPE",        
    "AWS",               
    "CLOUDFLARE",   
    "MASTERCARD"
  ];
  return (
    <section className="py-12 bg-black border-y border-white/5 overflow-hidden relative">
      <div className="absolute inset-0 bg-cyan-900/5 blur-3xl pointer-events-none transform-gpu" />
      <div className="container mx-auto px-4 mb-6 text-center relative z-10">
        <p className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.3em]">Trusted by Industry Leaders</p>
      </div>
      <div className="relative flex overflow-x-hidden group">
        <div className="absolute top-0 left-0 h-full w-24 bg-gradient-to-r from-black to-transparent z-10" />
        <div className="absolute top-0 right-0 h-full w-24 bg-gradient-to-l from-black to-transparent z-10" />
        <div className="flex gap-16 animate-marquee whitespace-nowrap items-center hover:[animation-play-state:paused]">
          {[...companies, ...companies, ...companies, ...companies].map((company, index) => (
            <span key={index} className="text-xl md:text-2xl font-bold text-gray-800 uppercase tracking-tighter hover:text-cyan-400 transition-colors duration-500 cursor-default select-none" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {company}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
});
TrustedBySection.displayName = 'TrustedBySection';

// ============================================================================
// --- DYNAMIC LOADERS ---
// ============================================================================

const DynamicHeroSection = dynamic(() => Promise.resolve(HeroSection), {
  ssr: false,
  loading: () => <section className="relative h-screen w-full overflow-hidden bg-black" />
});

const DynamicGlobalScaleSection = dynamic(() => Promise.resolve(GlobalScaleSection), {
  ssr: false,
  loading: () => <section className="relative h-screen w-full overflow-hidden bg-black" />
});

// ============================================================================
// --- PAGE COMPONENT ---
// ============================================================================

export default function Page() {
  const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();
  const { isProductOverlayVisible, showProductOverlay, hideProductOverlay } = useUIStore();

  return (
    <div className="min-h-screen w-full text-gray-100 overflow-x-hidden bg-black" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      <main className="relative z-10 w-full">
        <DynamicHeroSection onOrderClick={() => setOverlayVisible(true)} onExploreClick={showProductOverlay} />
        <HowItWorksSection />
        <DynamicGlobalScaleSection />
        <FinalCTA />
        <TrustedBySection />
        <CinematicBackground />
      </main>

      {/* Overlays properly separated from main layout thread */}
      <ProductOverlay isOpen={isProductOverlayVisible} onClose={hideProductOverlay} />
      <AIChatOverlay isOpen={isOverlayVisible} onClose={() => setOverlayVisible(false)} />
    </div>
  );
}
