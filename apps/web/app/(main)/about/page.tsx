'use client';

import React, { Suspense, useRef, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Stars, Float, Preload } from '@react-three/drei';
import { motion, useScroll, useTransform, useSpring, useMotionValue } from 'framer-motion';
import { Cpu, Rocket, Leaf, Globe as GlobeIcon, Users, Zap, Map, Video } from 'lucide-react';
import Image from 'next/image';
import * as THREE from 'three';
import dynamic from 'next/dynamic';

// ============================================================================
// --- Hero 3D Visual (New: Matches Main Page) ---
// ============================================================================

const AboutHeroVisual = () => {
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
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        </>
    );
};

// ============================================================================
// --- Dynamic Loaders (Crucial for Build) ---
// ============================================================================

const DynamicAboutHeroVisual = dynamic(() => Promise.resolve(AboutHeroVisual), { 
  ssr: false, 
  loading: () => null
});

// ============================================================================
// --- Re-designed Components ---
// ============================================================================

const PillarSection = ({ 
    icon: Icon, 
    title, 
    text, 
    videoSrc, 
    reverse = false 
}: { 
    icon: React.ElementType, 
    title: string, 
    text: string, 
    videoSrc: string, 
    reverse?: boolean 
}) => {
    const ref = useRef(null);
    const { scrollYProgress } = useScroll({
        target: ref,
        offset: ['start end', 'end start']
    });
    const y = useTransform(scrollYProgress, [0, 1], ['-20%', '20%']);

    return (
        <div ref={ref} className={`flex flex-col md:flex-row items-center gap-12 ${reverse ? 'md:flex-row-reverse' : ''} my-32`}>
            {/* --- Text Content --- */}
            <motion.div 
                initial={{ opacity: 0, x: reverse ? 50 : -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.8 }}
                className="w-full md:w-1/2"
            >
                <Icon className="w-12 h-12 text-cyan-400 mb-4" />
                <h3 className="text-4xl font-bold text-white mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {title}
                </h3>
                <p className="text-lg text-gray-400 leading-relaxed">
                    {text}
                </p>
            </motion.div>

            {/* --- Visual Content (Video) --- */}
            <div className="w-full md:w-1/2 h-96">
                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{ duration: 0.8 }}
                    className="relative h-full w-full rounded-2xl border border-cyan-400/30 overflow-hidden shadow-2xl shadow-cyan-500/20"
                >
                    <motion.video
                        style={{ y }}
                        className="absolute top-0 left-0 w-full h-full object-cover"
                        src={videoSrc}
                        autoPlay
                        loop
                        muted
                        playsInline
                    />
                    <div className="absolute inset-0 bg-black/40" />
                </motion.div>
            </div>
        </div>
    );
};

const AnimatedCounter = ({ value, label, icon }: { value: number; label: string; icon: React.ReactNode; }) => {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 100, stiffness: 100 });

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) motionValue.set(value);
        }, { threshold: 0.5 });
        if (ref.current) observer.observe(ref.current);
        const unsubscribe = springValue.on("change", (latest) => {
            if (ref.current) ref.current.textContent = Intl.NumberFormat('en-US').format(Math.round(latest));
        });
        return () => {
            if (ref.current) observer.unobserve(ref.current);
            unsubscribe();
        };
    }, [springValue, value, motionValue]);

    return (
        <div className="p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10 text-center">
            <div className="h-8 w-8 text-cyan-400 mx-auto mb-3">{icon}</div>
            <span ref={ref} className="text-4xl md:text-5xl font-bold text-white tabular-nums" style={{ fontFamily: "'Orbitron', sans-serif" }}>0</span>
            <p className="text-sm text-gray-400 uppercase tracking-widest mt-2">{label}</p>
        </div>
    );
};

// ============================================================================
// --- Main Page Component ---
// ============================================================================

export default function AboutPage() {
  const scrollRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: scrollRef });
  const missionScale = useTransform(scrollYProgress, [0.1, 0.25], [0.9, 1]);
  const missionOpacity = useTransform(scrollYProgress, [0.1, 0.25], [0.5, 1]);

  return (
    <div ref={scrollRef} className="bg-black text-white" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
      
      <section className="relative h-screen w-full flex items-center justify-center text-center overflow-hidden">
        <div className="absolute inset-0 z-0 opacity-70">
            <Canvas>
                <Suspense fallback={null}>
                    <DynamicAboutHeroVisual />
                </Suspense>
            </Canvas>
        </div>
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: "easeOut" }}
            className="z-10 px-4"
        >
            <motion.h1 
              className="text-5xl md:text-7xl font-black text-white" 
              style={{ fontFamily: "'Orbitron', sans-serif" }}
            >
                We’re Redefining the Meaning of Commerce.
            </motion.h1>

            <p className="mt-4 text-lg text-gray-300 max-w-3xl mx-auto">
                From intelligence to autonomy — we’re building the next evolution of global trade.
            </p>
             <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="group relative inline-flex items-center justify-center px-8 py-4 mt-8 text-lg font-bold text-black bg-white rounded-full shadow-lg overflow-hidden">
                <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <span className="relative">Discover Our Vision</span>
            </motion.button>
        </motion.div>
      </section>

      <section className="py-32 px-4 container mx-auto">
        <motion.div 
            style={{ scale: missionScale, opacity: missionOpacity }}
            className="max-w-4xl mx-auto text-center"
        >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                Accelerating the World’s Transition to Autonomous Commerce.
            </h2>
            <p className="text-lg text-gray-400 leading-relaxed">
                We believe commerce should be instant, intelligent, and sustainable.
                airdeliver is not just a company — it’s a movement towards autonomy powered by AI and clean energy.
            </p>
        </motion.div>
      </section>

      {/* --- BEGIN NEW "PILLARS" SECTION --- */}
      <section className="py-32 px-4 container mx-auto max-w-6xl">
         <div className="text-center mb-16">
             <h2 className="text-4xl md:text-5xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>The Pillars of Autonomy</h2>
         </div>
        
         <PillarSection 
            icon={Cpu}
            title="AI Core"
            text="Our self-learning neural network optimizes millions of routes in real-time, managing the entire global logistics network autonomously and efficiently."
            videoSrc="/videos/ai_core_visual.mp4"
         />

         <PillarSection 
            icon={Rocket}
            title="Autonomous Drones"
            text="A fully automated aerial fleet. Our drones are engineered for speed, reliability, and all-weather operation, ensuring your package arrives instantly."
            videoSrc="/videos/drone_visual.mp4"
            reverse={true}
         />

         <PillarSection 
            icon={Leaf}
            title="Sustainable Grid"
            text="We built our network on a zero-emission foundation. Our operations are powered by clean energy, redefining commerce to be as good for the planet as it is for you."
            videoSrc="/videos/grid_visual.mp4"
         />

      </section>
      {/* --- END NEW "PILLARS" SECTION --- */}


       <section className="py-32 px-4 relative bg-black bg-grid-cyan-400/[0.05]">
            <div className="container mx-auto text-center">
                <p className="text-2xl text-gray-300 mb-12 max-w-3xl mx-auto">We’re not just delivering products — we’re delivering progress.</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <AnimatedCounter value={1200000} label="CO₂ Saved (tons)" icon={<Leaf size={32} />} />
                    <AnimatedCounter value={10582} label="Drones in Active Flight" icon={<Rocket size={32} />} />
                    <AnimatedCounter value={127} label="Cities Connected" icon={<Map size={32} />} />
                </div>
            </div>
       </section>

      <section className="py-32 px-4">
        <div className="container mx-auto max-w-4xl text-center">
            <h2 className="text-4xl md:text-5xl font-bold mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>Powered by People & AI</h2>
            <p className="text-lg text-gray-400 mb-12">Behind every line of code, there’s a human mind shaping the intelligence that drives airdeliver.</p>
            <div className="relative h-64 w-full max-w-2xl mx-auto flex justify-center items-center">
                {['/team/faris.png', '/team/maria.png', '/team/chen.png'].map((img, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, scale: 0.8 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true, amount: 0.3 }}
                        transition={{ delay: i * 0.2, type: "spring" }}
                        className="absolute"
                        style={{ left: `${25 + i * 25}%`, transform: 'translateX(-50%)' }}
                    >
                         <Image src={img} alt="Team member" width={128} height={128} className="w-24 h-24 md:w-32 md:h-32 rounded-full object-cover border-4 border-cyan-400/30 shadow-2xl shadow-cyan-500/20" />
                    </motion.div>
                ))}
            </div>
        </div>
      </section>

      <footer className="relative py-20 px-4 text-center border-t border-white/10 overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-black/50 backdrop-blur-md" />
        <motion.h2 
            className="text-3xl md:text-4xl font-bold text-white mb-4" 
            style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
            Be Part of the Revolution.
        </motion.h2>

        <p className="text-lg text-gray-400 mb-8 max-w-xl mx-auto">"The sky is no longer the limit — it’s our infrastructure."</p>
         <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-full shadow-lg overflow-hidden">
            <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative flex items-center">Join the Movement</span>
          </motion.button>
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-white bg-transparent border-2 border-white/20 rounded-full shadow-lg transition-all duration-300 hover:border-white/50 hover:bg-white/10">
            Contact Us
          </motion.button>
        </div>
        <p className="mt-16 text-xs text-gray-500">airdeliver © 2025 – Built by Intelligence, Driven by Autonomy.</p>
      </footer>
    </div>
  );
}
