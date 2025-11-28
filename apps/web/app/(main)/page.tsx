//** apps/web/app/(main)/page.tsx **//

'use client';

import { ShieldCheck, Lock, Clock, MapIcon, Quote, GlobeIcon, CheckCircle2 } from 'lucide-react';
import { useUIStore } from '@/hooks/useUIStore';
import ProductOverlay from '@/components/products/ProductOverlay';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';
import Link from 'next/link';
import Autoplay from 'embla-carousel-autoplay';
import useEmblaCarousel from 'embla-carousel-react';
import { Star } from 'lucide-react';
import React, { Suspense, useRef, useMemo, useEffect, useState, ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Preload, Float, Line, Text, useTexture, OrbitControls, Stars } from '@react-three/drei';
import { motion, useScroll, useSpring, useInView, useTransform, useMotionValue, type MotionValue } from 'framer-motion';
import { Bot, BrainCircuit, Leaf, Rocket, Zap, ArrowRight, Cpu, Map } from 'lucide-react';
import { X } from 'lucide-react'; 
import * as THREE from 'three';
import dynamic from 'next/dynamic';

const Cleanup = () => {
  const { gl } = useThree();
  useEffect(() => {
    return () => {
      gl.dispose();
    };
  }, [gl]);
  return null; 
};

// ============================================================================
// --- COMPONENT DEFINITIONS (Locally Scoped) ---
// ============================================================================

const StarryBackground = () => {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900/50 via-black to-black" />
      <div className="absolute inset-0 opacity-20" 
           style={{ backgroundImage: 'radial-gradient(white 1px, transparent 1px)', backgroundSize: '50px 50px' }}>
      </div>
    </div>
  );
};

// ============================================================================
// --- 1. HERO SECTION (Definition) ---
// ============================================================================
const HeroSection = ({ onOrderClick, onExploreClick }: { onOrderClick: () => void; onExploreClick: () => void }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });
  const parallaxY = useTransform(scrollYProgress, [0, 1], ['0%', '50%']);

  return (
    <section ref={containerRef} className="relative h-screen w-full overflow-hidden">
      <div className="absolute inset-0 z-0">
        <Suspense fallback={<div className="w-full h-full bg-transparent" />}>
          <Canvas camera={{ position: [0, 0, 15], fov: 75 }}>
            <Hero3DBackground />
            <Preload all />
	        <Cleanup />
          </Canvas>
        </Suspense>
      </div>

      <motion.div style={{ y: parallaxY }} className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="mb-4 text-sm font-light tracking-[0.3em] text-gray-50 uppercase"
        >
          AI. AUTONOMY. REDEFINING E-COMMERCE.
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8 }}
          className="w-full max-w-[90vw] mx-auto font-black uppercase leading-none" 
          style={{ fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif" }}
        >
          <span className="block text-[12vw] sm:text-[10vw] md:text-[9vw] lg:text-[8vw] leading-[0.9] bg-clip-text text-transparent bg-gradient-to-b from-cyan-400 via-cyan-400 to-white drop-shadow-[0_0_25px_rgba(0,198,255,0.3)]">
            COMMERCE.
          </span>
          
          <span className="block text-[12vw] sm:text-[10vw] md:text-[9vw] lg:text-[8vw] leading-[0.9] bg-clip-text text-transparent bg-gradient-to-b from-white via-purple-300 to-purple-500 drop-shadow-[0_0_25px_rgba(168,85,247,0.3)]">
            TAKES FLIGHT.
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.2 }}
          className="mt-6 max-w-2xl text-base md:text-lg text-gray-300"
        >
          Experience the World’s First AI-Driven Delivery Infrastructure — Faster, Smarter, and Fully Autonomous.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.5 }}
          className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4"
        >

          <button
            onClick={onOrderClick}
            className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 hover:scale-105 overflow-hidden"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative flex items-center" style={{ fontFamily: "'Quattrocento Sans', sans-serif" }}>order with air <Bot className="ml-2 h-5 w-5" /></span>
          </button>

          <button
	    onClick={onExploreClick}
	    className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-white bg-transparent border-2 border-white/20 rounded-full shadow-lg transition-all duration-300 hover:border-white/50 hover:bg-white/10">
            Explore Products <ArrowRight className="ml-2 h-5 w-5" />
          </button>
        </motion.div>
      </motion.div>
    </section>
  );
};

const Hero3DBackground = () => {
  const light1Ref = useRef<THREE.PointLight>(null!);
  const light2Ref = useRef<THREE.PointLight>(null!);

  useFrame((state) => {
    const time = state.clock.elapsedTime;

    if (light1Ref.current) {
      light1Ref.current.position.x = Math.sin(time * 0.5) * 10;
      light1Ref.current.position.y = Math.cos(time * 0.5) * 10;
      light1Ref.current.position.z = Math.cos(time * 0.5) * 10;
    }
    if (light2Ref.current) {
      light2Ref.current.position.x = Math.sin(time * 0.3) * -10;
      light2Ref.current.position.y = Math.cos(time * 0.3) * -10;
      light2Ref.current.position.z = Math.sin(time * 0.3) * 5;
    }
  });

  return (
    <>
      <fog attach="fog" args={['#000000', 10, 40]} />
      <ambientLight intensity={1.5} />
      <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
      <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
      <Starfield />
    </>
  );
};

const Starfield = (props: any) => {
  const starsRef = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (starsRef.current) {
      starsRef.current.rotation.x += delta * 0.01;
      starsRef.current.rotation.y += delta * 0.02;
    }
  });

  return (
    <group ref={starsRef} {...props} position={[0, 0, -50]}>
      <Stars
        radius={100}
        depth={100}
        count={44444}
        factor={17}
        saturation={0}
        fade
        speed={1.5}
      />
    </group>
  );
};

// ============================================================================
// --- 2. HOW IT WORKS SECTION (Architectural Blueprint) ---
// ============================================================================

const VIEWBOX_WIDTH = 850;
const VIEWBOX_HEIGHT = 1100;

const timelineSteps = [
  {
    icon: Bot,
    step: 1,
    title: "AI Initiation",
    description: "Natural language processing core interprets your intent instantly."
  },
  {
    icon: Cpu,
    step: 2,
    title: "Route Computation",
    description: "Neural networks calculate the optimal 4D flight path in milliseconds."
  },
  {
    icon: MapIcon,
    step: 3,
    title: "Live Telemetry",
    description: "Real-time holographic tracking from dispatch to destination."
  },
  {
    icon: Rocket,
    step: 4,
    title: "Autonomous Arrival",
    description: "Precision landing sequence initiated. Delivery complete."
  },
];

const stepsWithPositions = [
  { ...timelineSteps[0], x: 70, y: 40, width: 340, height: 240 },
  { ...timelineSteps[1], x: 490, y: 220, width: 340, height: 240 },
  { ...timelineSteps[2], x: 70, y: 400, width: 340, height: 240 },
  { ...timelineSteps[3], x: 390, y: 721, width: 340, height: 240 },
];

const DiagramPath = ({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) => {
  const pathLength = useTransform(scrollYProgress, [0.1, 0.7], [0, 1]);

  const pathData = `M 410 160 L 450 160 L 450 340 L 490 340 ` + 
                   `M 660 460 L 660 520 L 410 520 ` +           
                   `M 240 640 L 240 841 L 390 841`;             

  return (
    <svg className="absolute inset-0 w-full h-full" viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} preserveAspectRatio="xMidYMin meet">
      <path d={pathData} fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth={4} strokeLinecap="square" />
      <motion.path
        d={pathData}
        fill="none"
        stroke="url(#architectural-gradient)"
        strokeWidth={3}
        strokeLinecap="square"
        style={{ pathLength, filter: 'drop-shadow(0 0 8px rgba(0, 198, 255, 0.6))' }}
      />
      <defs>
        <linearGradient id="architectural-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#00C6FF" />
          <stop offset="100%" stopColor="#7F00FF" />
        </linearGradient>
      </defs>
    </svg>
  );
};

const StepCard = ({ item }: { item: (typeof stepsWithPositions)[0] }) => {
  return (
    <div className="relative group h-full w-full">
        <div className="absolute inset-0 bg-cyan-500/20 rounded-[40px] blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
        <div className="relative h-full w-full rounded-[40px] bg-black/60 backdrop-blur-xl border border-white/10 p-6 flex flex-col items-start transition-all duration-500 group-hover:border-cyan-500/30 group-hover:bg-black/80 overflow-hidden">
            <div className="absolute top-6 right-6 flex gap-1">
                <div className="w-1 h-1 rounded-full bg-white/20 group-hover:bg-cyan-400/80 transition-colors" />
                <div className="w-1 h-1 rounded-full bg-white/20 group-hover:bg-cyan-400/60 transition-colors" />
                <div className="w-1 h-1 rounded-full bg-white/20 group-hover:bg-cyan-400/40 transition-colors" />
            </div>

            <div className="mb-4 inline-flex items-center justify-center p-3 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10 text-cyan-400 group-hover:text-white group-hover:scale-110 transition-all duration-500 shadow-lg shadow-black/50">
                <item.icon size={28} />
            </div>

            <div className="flex items-center gap-3 mb-2">
                <span className="text-[10px] font-mono text-cyan-500/80 tracking-widest uppercase border border-cyan-500/20 px-2 py-0.5 rounded">
                    Phase 0{item.step}
                </span>
            </div>

            <h3 className="text-2xl font-bold text-white mb-3 tracking-wide group-hover:text-cyan-100 transition-colors" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                {item.title}
            </h3>

            <p className="text-sm text-gray-400 leading-relaxed font-light group-hover:text-gray-300">
                {item.description}
            </p>
        </div>
    </div>
  );
};

const PositionedStepCard = ({ step }: { step: (typeof stepsWithPositions)[0] }) => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.4 });

  return (
    <motion.div
      ref={ref}
      className="absolute z-10"
      style={{
        left: `${(step.x / VIEWBOX_WIDTH) * 100}%`,
        top: `${(step.y / VIEWBOX_HEIGHT) * 100}%`,
        width: `${(step.width / VIEWBOX_WIDTH) * 100}%`,
        height: `${(step.height / VIEWBOX_HEIGHT) * 100}%`,
      }}
      initial={{ opacity: 0, y: 40, scale: 0.95 }}
      animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      <StepCard item={step} />
    </motion.div>
  );
};

const HowItWorksSection = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start center', 'end end'] });

  return (
    <section ref={containerRef} className="relative w-full py-32 px-4 overflow-hidden bg-black">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_100%)] pointer-events-none" />

      <div className="container mx-auto relative z-10">
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-24"
        >
            <h2 className="text-5xl md:text-7xl font-black mb-6 tracking-tight text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-white to-purple-500 drop-shadow-[0_0_20px_rgba(0,198,255,0.3)]">
                SYSTEM ARCHITECTURE
              </span>
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto text-lg font-light tracking-wide uppercase">
                From Query to Delivery in Four Autonomous Phases
            </p>
        </motion.div>

        <div className="relative w-full max-w-5xl mx-auto" style={{ aspectRatio: `${VIEWBOX_WIDTH} / ${VIEWBOX_HEIGHT}` }}>
          <div className="absolute inset-0 z-0">
            <DiagramPath scrollYProgress={scrollYProgress} />
          </div>
          {stepsWithPositions.map((step) => (
            <PositionedStepCard key={step.step} step={step} />
          ))}
        </div>
      </div>
    </section>
  );
};

// ============================================================================
// --- 7. GLOBAL SCALE SECTION (Definition) ---
// ============================================================================

const AnimatedCounter = ({ value, text, icon: Icon }: { value: number, text: string, icon: any }) => {
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
        className="relative group flex flex-col items-center p-6 rounded-[30px] bg-black/60 backdrop-blur-xl border border-purple-500/30 hover:border-purple-400/80 transition-all duration-500 overflow-hidden text-center"
    >
        <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="mb-4 p-3 rounded-full bg-purple-950/50 border border-purple-400/20 text-purple-400 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(168,85,247,0.3)]">
            <Icon size={28} />
        </div>
        <span ref={ref} className="text-4xl md:text-5xl font-black text-white tracking-tighter mb-2 drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" style={{fontFamily: "'Orbitron', sans-serif"}}>0</span>
        <span className="text-sm text-purple-300/80 font-mono uppercase tracking-widest">{text}</span>
    </motion.div>
  );
};

const Globe = () => {
    const globeRef = useRef<THREE.Group>(null!);
  
    const points = useMemo(() => [
        { lat: 40.7128, lon: -74.0060 }, { lat: 51.5074, lon: -0.1278 },
        { lat: 35.6895, lon: 139.6917 }, { lat: 25.2048, lon: 55.2708 },
        { lat: 1.3521, lon: 103.8198 }, { lat: 30.0444, lon: 31.2357 },
    ], []);

    const [paths, setPaths] = useState<THREE.CatmullRomCurve3[]>([]);
    const pulseRefs = useRef<THREE.Mesh[]>([]);

    useEffect(() => {
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
        pulseRefs.current = pulseRefs.current.slice(0, curves.length);
    }, [points]);

    useFrame((state, delta) => {
        if(globeRef.current) {
            globeRef.current.rotation.y += delta * 0.05;
        }
        pulseRefs.current.forEach((mesh, i) => {
             if (mesh && paths[i]) {
                 const time = state.clock.elapsedTime;
                 const loopTime = 6 + (i % 3);
                 const t = (time % loopTime) / loopTime;
                 paths[i].getPointAt(t, mesh.position);
             }
        });
    });

    return (
        <group ref={globeRef}>
            
            <mesh>
                <sphereGeometry args={[5, 128, 128]} />
                <meshPhysicalMaterial
                    color="#1e3a8a" 
                    emissive="#172554" 
                    emissiveIntensity={0.5}
                    roughness={0.4}
                    metalness={0.6}
                    clearcoat={1} 
                    clearcoatRoughness={0.1}
                />
            </mesh>

            <mesh scale={[1.05, 1.05, 1.05]}>
                <sphereGeometry args={[5, 64, 64]} />
                <meshBasicMaterial color="#3b82f6" transparent opacity={0.15} side={THREE.BackSide} blending={THREE.AdditiveBlending} />
            </mesh>
          
            <mesh scale={[1.2, 1.2, 1.2]}>
                <sphereGeometry args={[5, 64, 64]} />
                <meshBasicMaterial color="#a855f7" transparent opacity={0.05} side={THREE.BackSide} blending={THREE.AdditiveBlending} />
            </mesh>

            {paths.map((curve, i) => (
                <group key={i}>
                     <mesh>
                       
                        <tubeGeometry args={[curve, 64, 0.025, 8, false]} />
                       
                        <meshBasicMaterial color="#d8b4fe" transparent opacity={0.8} blending={THREE.AdditiveBlending} />
                    </mesh>
                  
                     <mesh ref={(el) => (pulseRefs.current[i] = el!)}>
                        <sphereGeometry args={[0.08, 16, 16]} />
                        <meshBasicMaterial color="#ffffff" toneMapped={false} />
                        <pointLight color="#d8b4fe" intensity={1} distance={3} />
                    </mesh>
                </group>
            ))}
        </group>
    );
};

const GlobalScaleSection = () => {
    return (
        <section className="relative min-h-screen w-full overflow-hidden bg-black flex flex-col justify-between pb-10">

            <div className="absolute inset-0 z-0">
                <Canvas camera={{ position: [0, 0, 17], fov: 35 }}>
                    <ambientLight intensity={0.4} />
                    <directionalLight position={[10, 10, 5]} intensity={2} color="#a855f7" /> 
                    <directionalLight position={[-10, -10, -5]} intensity={2} color="#3b82f6" /> 

                    <Stars
                        radius={100}
                        depth={100}
                        count={40000} 
                        factor={14}    
                        saturation={1}
                        fade
                        speed={0.2}  
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
                            initial={{ opacity: 0, x: -50 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.8 }}
                        >
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]">
                                    <GlobeIcon className="text-purple-400" size={20} />
                                </div>
                                <span className="text-sm font-mono text-purple-400 uppercase tracking-[0.3em] drop-shadow-md">Planetary Operations</span>
                            </div>

                            <h2 className="text-5xl md:text-7xl font-black text-white mb-6 leading-[0.9] tracking-tighter drop-shadow-2xl" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                GLOBAL<br />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-fuchsia-400 to-cyan-400 drop-shadow-[0_0_20px_rgba(168,85,247,0.8)] filter brightness-125">
                                    SCALE
                                </span>
                            </h2>

                            <p className="text-lg text-gray-300 font-light leading-relaxed mb-6 border-l-4 border-purple-500/50 pl-6 drop-shadow-lg">
                                A synchronized autonomous network spanning continents. <br />
                                <span className="text-white font-medium">Zero Latency. Infinite Reach.</span>
                            </p>
                        </motion.div>
                     </div>
                     <div></div>
                 </div>
            </div>

            <div className="relative z-10 container mx-auto px-6 mt-12 pointer-events-auto">
                <motion.div
                        initial={{ opacity: 0, y: 50 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3, duration: 0.8 }}
                        className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto"
                >
                    <AnimatedCounter value={1843} text="Active Drones" icon={Rocket} />
                    <AnimatedCounter value={212} text="Connected Cities" icon={MapIcon} />
                    <AnimatedCounter value={947204} text="Successful Drops" icon={CheckCircle2} />
                </motion.div>
            </div>
        </section>
    );
};

// ============================================================================
// --- 8. TESTIMONIALS (Redesigned) ---
// ============================================================================

const testimonials = [
  {
    name: 'Elena',
    title: 'CEO, Neo',
    quote: "airdeliver isn't just a service; it's the future of logistics. The speed and autonomy are unparalleled.",
    rating: 5,
    avatar: 'E',
    color: 'cyan'
  },
  {
    name: 'Kenji',
    title: 'Lead Futurist, QuantumLeap',
    quote: "The AI's efficiency in optimizing routes is something we thought was years away. It's here now.",
    rating: 5,
    avatar: 'K',
    color: 'purple'
  },
  {
    name: 'Fatima',
    title: 'Head of Innovation, EcoSpear',
    quote: "Sustainability is key for us. airdeliver's zero-emission network is a game-changer for green commerce.",
    rating: 5,
    avatar: 'F',
    color: 'green'
  },
];

const TrustSignalCard = ({ icon: Icon, title, description, delay }: { icon: any, title: string, description: string, delay: number }) => (
    <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, delay: delay }}
        whileHover={{ scale: 1.05, y: -10 }}
        className="relative group flex flex-col items-center text-center p-8 bg-black/40 backdrop-blur-xl border border-white/10 rounded-[40px] overflow-hidden hover:border-cyan-500/30 transition-all duration-500 h-full"
    >
        <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="absolute -inset-px bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-[40px] blur-xl opacity-0 group-hover:opacity-50 transition-opacity duration-500" />

        <div className="relative mb-6 p-4 rounded-2xl bg-white/5 border border-white/10 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/30 transition-colors duration-500 shadow-lg shadow-black/20">
            <Icon size={32} className="text-gray-300 group-hover:text-cyan-400 transition-colors duration-500" />
        </div>

        <h3 className="text-xl font-bold text-white mb-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            {title}
        </h3>

        <p className="text-sm text-gray-400 leading-relaxed font-light">
            {description}
        </p>
    </motion.div>
);

const TestimonialCard = ({ testimonial }: { testimonial: typeof testimonials[0] }) => {
    return (
        <div className="flex-[0_0_85%] md:flex-[0_0_40%] min-w-0 pl-6">
            <motion.div
                whileHover={{ scale: 1.02 }}
                className="relative h-full p-10 rounded-[40px] bg-gradient-to-br from-white/5 to-transparent border border-white/10 flex flex-col group overflow-hidden"
            >
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover:via-cyan-500/50 transition-all duration-500" />

                <div className="flex items-center gap-4 mb-8">
                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold text-black shadow-lg ${
                        testimonial.color === 'purple' ? 'bg-purple-400 shadow-purple-500/20' :
                        testimonial.color === 'green' ? 'bg-emerald-400 shadow-emerald-500/20' :
                        'bg-cyan-400 shadow-cyan-500/20'
                    }`}>
                        {testimonial.avatar}
                    </div>
                    <div>
                        <h4 className="text-xl font-bold text-white font-mono uppercase tracking-wide">{testimonial.name}</h4>
                        <p className="text-xs text-cyan-500/80 uppercase tracking-widest font-semibold">{testimonial.title}</p>
                    </div>
                </div>

                <div className="relative z-10 flex-grow">
                    <Quote size={48} className="absolute -top-4 -left-2 text-white/5 -z-10" />
                    <p className="text-lg text-gray-300 font-light leading-relaxed italic pl-4 border-l-2 border-white/10">
                        "{testimonial.quote}"
                    </p>
                </div>

                <div className="flex items-center gap-1 mt-8">
                    {[...Array(5)].map((_, i) => (
                        <Star key={i} size={16} className="text-cyan-400 fill-cyan-400" />
                    ))}
                </div>
            </motion.div>
        </div>
    );
};

export const TestimonialsSection = () => {
  const [emblaRef] = useEmblaCarousel({ loop: true, align: 'center' }, [Autoplay({ delay: 6000, stopOnInteraction: false })]);

  return (
    <section className="py-32 px-4 relative bg-black overflow-hidden">

        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.04] pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black pointer-events-none" />

        <div className="container mx-auto relative z-10">

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8 }}
                className="text-center mb-24 max-w-4xl mx-auto"
            >
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md mb-6">
                    <Zap size={12} className="text-yellow-400 fill-yellow-400" />
                    <span className="text-[10px] font-mono text-gray-300 uppercase tracking-widest">Community Uplink</span>
                </div>

                <h2 className="text-5xl md:text-7xl font-black text-white mb-8 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    TRUSTED BY<br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-cyan-400 animate-gradient-x">
                        VISIONARIES
                    </span>
                </h2>
                <p className="text-xl text-gray-400 font-light leading-relaxed max-w-2xl mx-auto">
                    From global tech leaders to first-time users — airdeliver is redefining the physics of commerce.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-32">
                <TrustSignalCard
                    icon={Lock}
                    title="Secure Payments"
                    description="Quantum-resistant encryption for every transaction."
                    delay={0.1}
                />
                <TrustSignalCard
                    icon={Leaf}
                    title="Eco-Friendly"
                    description="100% electric fleet. Zero emissions. Pure efficiency."
                    delay={0.2}
                />
                <TrustSignalCard
                    icon={ShieldCheck}
                    title="Insured & Reliable"
                    description="Full cargo insurance and real-time anomaly detection."
                    delay={0.3}
                />
                <TrustSignalCard
                    icon={Clock}
                    title="24/7 Service"
                    description="Autonomous systems never sleep. Delivery at any hour."
                    delay={0.4}
                />
            </div>

            <div className="overflow-hidden cursor-grab active:cursor-grabbing py-10" ref={emblaRef}>
                <div className="flex -ml-6">
                    {testimonials.map((t, i) => (
                        <TestimonialCard key={i} testimonial={t} />
                    ))}
                </div>
            </div>
        </div>
    </section>
  );
};

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
        <TestimonialsSection />
      </main>
      <ProductOverlay isOpen={isProductOverlayVisible} onClose={hideProductOverlay} />
    </div>
  );
}
