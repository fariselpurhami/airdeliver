//** apps/web/app/(main)/about/page.tsx **//

'use client';

import React, { Suspense, useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { motion, useScroll, useTransform, useMotionValue, useSpring, useInView } from 'framer-motion';
import { Cpu, Rocket, Leaf, Map, ChevronRight, Target, Zap, Shield, Globe, Users } from 'lucide-react';
import Image from 'next/image';
import * as THREE from 'three';

// ============================================================================
// --- 1. ARCHITECTURAL BACKGROUND (The Nebula) ---
// ============================================================================

const AboutHeroVisual = () => {
    const groupRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
            groupRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.05;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 20, 60]} />
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={2} color="#00C6FF" />
            <pointLight position={[-10, -10, 5]} intensity={2} color="#7F00FF" />
            <Stars radius={100} depth={60} count={7000} factor={4} saturation={0} fade speed={0.5} />
        </group>
    );
};

// ============================================================================
// --- 2. GLOBAL DESIGN COMPONENTS (The Building Blocks) ---
// ============================================================================

const InnovationMonolith = ({ 
    icon: Icon, 
    title, 
    text, 
    videoSrc, 
    index 
}: { 
    icon: React.ElementType, 
    title: string, 
    text: string, 
    videoSrc: string,
    index: number
}) => {
    const isEven = index % 2 === 0;

    return (
        <motion.div 
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="group relative w-full overflow-hidden bg-white/5 backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-2xl shadow-black/50"
        >
            <div className={`flex flex-col lg:flex-row h-full ${isEven ? '' : 'lg:flex-row-reverse'}`}>
                
                <div className="relative w-full lg:w-1/2 h-64 lg:h-auto min-h-[400px] overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent z-10 lg:hidden" />
                    <div className={`absolute inset-0 bg-gradient-to-r ${isEven ? 'from-transparent to-black' : 'from-black to-transparent'} z-10 hidden lg:block opacity-80`} />
                    
                    <div className="absolute inset-0 bg-gray-900">
                        {videoSrc ? (
                            <video 
                                src={videoSrc} 
                                className="w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity duration-700 group-hover:scale-105 transform"
                                autoPlay loop muted playsInline 
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-cyan-900/20 to-purple-900/20 flex items-center justify-center">
                                <Icon className="w-32 h-32 text-white/5" />
                            </div>
                        )}
                    </div>
                </div>

                <div className="relative w-full lg:w-1/2 p-8 lg:p-16 flex flex-col justify-center bg-black/40">
                    <div className="mb-6 p-4 rounded-2xl bg-white/5 w-fit border border-white/10 shadow-[0_0_15px_rgba(0,198,255,0.1)]">
                        <Icon className="w-8 h-8 text-cyan-400" />
                    </div>
                    
                    <h3 className="text-3xl md:text-4xl font-bold text-white mb-6 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {title}
                    </h3>
                    
                    <p className="text-lg text-gray-300 leading-relaxed font-light border-l-2 border-cyan-500/30 pl-6">
                        {text}
                    </p>

                    <div className="mt-8 flex items-center gap-2 text-cyan-400 text-sm font-bold uppercase tracking-widest cursor-pointer hover:text-cyan-300 transition-colors group/btn">
                        <span>Initialize Protocol</span>
                        <ChevronRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

const StatModule = ({ value, label, icon: Icon }: { value: number; label: string; icon: React.ElementType }) => {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 50, stiffness: 50 });
    const isInView = useInView(ref, { once: true });

    useEffect(() => {
        if (isInView) {
            motionValue.set(value);
        }
    }, [isInView, value, motionValue]);

    useEffect(() => {
        const unsubscribe = springValue.on("change", (latest) => {
            if (ref.current) {
                ref.current.textContent = Intl.NumberFormat('en-US').format(Math.floor(latest));
            }
        });
        return () => unsubscribe();
    }, [springValue]);

    return (
        <div className="relative p-8 rounded-[30px] bg-white/5 border border-white/10 backdrop-blur-lg flex flex-col items-center justify-center text-center group hover:border-cyan-500/30 transition-all duration-300 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <Icon className="w-8 h-8 text-gray-500 mb-4 group-hover:text-cyan-400 transition-colors relative z-10" />
            <span 
                ref={ref} 
                className="text-4xl md:text-5xl font-bold text-white mb-2 tabular-nums relative z-10" 
                style={{ fontFamily: "'Orbitron', sans-serif" }}
            >
                0
            </span>
            <span className="text-xs uppercase tracking-[0.2em] text-cyan-500/80 font-bold relative z-10">{label}</span>
        </div>
    );
};

const TeamOperative = ({ image, name, role, delay }: { image: string, name: string, role: string, delay: number }) => (
    <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ delay, duration: 0.5 }}
        className="relative group rounded-[30px] overflow-hidden aspect-[3/4] border border-white/10 shadow-lg bg-black"
    >
        <Image 
            src={image} 
            alt={name} 
            fill 
            className="object-cover transition-transform duration-700 group-hover:scale-110 grayscale group-hover:grayscale-0 opacity-80 group-hover:opacity-100"
            onError={(e) => { e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0F172A&color=fff&size=512` }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent opacity-90" />
        
        <div className="absolute bottom-0 left-0 right-0 p-8 translate-y-2 group-hover:translate-y-0 transition-transform">
            <div className="h-1 w-12 bg-cyan-500 mb-4 rounded-full" />
            <h4 className="text-2xl font-bold text-white mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>{name}</h4>
            <p className="text-cyan-400 text-xs uppercase tracking-widest font-bold">{role}</p>
        </div>
    </motion.div>
);

// ============================================================================
// --- 3. MAIN PAGE COMPONENT (The Structure) ---
// ============================================================================

export default function AboutPage() {
  const scrollRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: scrollRef });
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
      setIsMounted(true);
  }, []);

  return (
    <div ref={scrollRef} className="bg-black text-white min-h-screen selection:bg-cyan-500/30 font-sans">
      
      <section className="relative pt-40 pb-20 px-4 text-center">
        <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
            {isMounted && (
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <Suspense fallback={null}>
                        <AboutHeroVisual />
                    </Suspense>
                </Canvas>
            )}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/40 to-black z-0 pointer-events-none" />
        </div>

        <div className="relative z-10 container mx-auto max-w-5xl">
            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
            >
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-900/10 backdrop-blur-md mb-8">
                    <Globe size={14} className="text-cyan-400" />
                    <span className="text-xs font-bold uppercase tracking-widest text-cyan-200/80">Global Infrastructure V2.0</span>
                </div>
                
                <h1 className="text-5xl md:text-7xl font-black text-white mb-6 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    ABOUT <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600">AIRDELIVER</span>
                </h1>
                
                <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
                    From artificial intelligence to full autonomy — we are engineering the nervous system of global trade.
                </p>
            </motion.div>
        </div>
      </section>

      <section className="relative py-32 px-4 bg-black overflow-hidden z-10">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
        <div className="container mx-auto max-w-5xl text-center">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-8 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                Accelerating the World’s Transition to <br/>
                <span className="text-cyan-400 drop-shadow-[0_0_15px_rgba(6,182,212,0.5)]">Autonomous Logistics.</span>
            </h2>
            <p className="text-lg md:text-xl text-gray-400 leading-relaxed max-w-4xl mx-auto border-l-2 border-purple-500/50 pl-6 text-left md:text-center md:border-l-0 md:pl-0">
                We believe commerce should be instant, intelligent, and sustainable. 
                <strong className="text-white"> airdeliver </strong> is not just a company — it’s a movement towards autonomy powered by AI and clean energy. We don't just move packages; we move the world forward.
            </p>
        </div>
      </section>

      <section className="relative py-20 px-4 z-10">
         <div className="container mx-auto max-w-7xl space-y-20">
            
            <InnovationMonolith 
                index={0}
                icon={Cpu}
                title="AI Core Intelligence"
                text="Our self-learning neural network optimizes millions of routes in real-time, managing the entire global logistics network autonomously. It predicts demand, reroutes instantly, and ensures efficiency beyond human capability."
                videoSrc="/videos/ai_core_visual.mp4"
            />

            <InnovationMonolith 
                index={1}
                icon={Rocket}
                title="Autonomous Fleet"
                text="A fully automated aerial fleet. Our drones are engineered for speed, reliability, and all-weather operation. They communicate with each other to form a cohesive swarm, ensuring your package arrives instantly, anywhere."
                videoSrc="/videos/drone_visual.mp4"
            />

            <InnovationMonolith 
                index={2}
                icon={Leaf}
                title="Sustainable Grid"
                text="We built our network on a zero-emission foundation. Our operations are powered by clean energy sources and optimized for minimal consumption, redefining commerce to be as good for the planet as it is for you."
                videoSrc="/videos/grid_visual.mp4"
            />

         </div>
      </section>

       <section className="py-32 px-4 relative overflow-hidden z-10">
            <div className="absolute inset-0 bg-grid-cyan-400/[0.03] -z-10" />
            <div className="container mx-auto max-w-6xl">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <StatModule value={1200000} label="CO₂ Tons Offset" icon={Leaf} />
                    <StatModule value={10582} label="Active Drone Units" icon={Target} />
                    <StatModule value={127} label="Connected Cities" icon={Map} />
                </div>
            </div>
       </section>

      <section className="py-32 px-4 z-10">
        <div className="container mx-auto max-w-6xl">
            <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
                <div>
                    <h2 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>Human Intelligence</h2>
                    <p className="text-gray-400 max-w-md">Behind every line of code, there’s a visionary mind shaping the intelligence that drives airdeliver.</p>
                </div>
                <button className="px-8 py-3 rounded-full border border-white/20 hover:bg-white/10 hover:border-cyan-400/50 transition-all text-sm font-bold uppercase tracking-wider text-white">
                    Access Personnel Files
                </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <TeamOperative image="/team/faris.png" name="Faris Elpurhami" role="CEO & CO-Founder" delay={0} />
                <TeamOperative image="/team/maria.png" name="Maria" role="Head of AI" delay={0.2} />
                <TeamOperative image="/team/chen.png" name="Chen" role="Drone Engineering" delay={0.4} />
            </div>
        </div>
      </section>

      <footer className="relative py-32 px-4 text-center overflow-hidden border-t border-white/5 z-10">
        <div className="absolute inset-0 bg-gradient-to-t from-cyan-900/20 to-transparent -z-10 opacity-50" />
        <div className="container mx-auto max-w-3xl relative z-10">
            <motion.h2 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
                className="text-4xl md:text-7xl font-bold text-white mb-8" 
                style={{ fontFamily: "'Orbitron', sans-serif" }}
            >
                Ready for Takeoff?
            </motion.h2>

            <p className="text-xl text-gray-400 mb-12">"The sky is no longer the limit — it’s our infrastructure."</p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                <motion.button 
                    whileHover={{ scale: 1.05 }} 
                    whileTap={{ scale: 0.95 }} 
                    className="group relative inline-flex items-center justify-center px-8 py-4 w-full sm:w-auto text-base font-bold text-black bg-white rounded-full shadow-[0_0_30px_rgba(255,255,255,0.2)] overflow-hidden"
                >
                    <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <span className="relative flex items-center gap-2">
                        Initialize Partnership <Zap size={18} fill="currentColor" />
                    </span>
                </motion.button>
            </div>
            
            <div className="mt-24 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center text-xs text-gray-600 gap-4 uppercase tracking-widest">
                <p>AIRDELIVER SYSTEMS © 2025</p>
                <div className="flex gap-6">
                    <span className="hover:text-cyan-400 cursor-pointer transition-colors">PRIVACY PROTOCOL</span>
                    <span className="hover:text-cyan-400 cursor-pointer transition-colors">TERMS OF ENGAGEMENT</span>
                    <span className="text-green-500">SYSTEM STATUS: NOMINAL</span>
                </div>
            </div>
        </div>
      </footer>
    </div>
  );
}
