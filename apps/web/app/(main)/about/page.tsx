'use client';

import React, { Suspense, useRef, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import { motion, useScroll, useTransform, useSpring, useMotionValue } from 'framer-motion';
import { Cpu, Rocket, Leaf, Globe as GlobeIcon, Users } from 'lucide-react';
import Image from 'next/image';
import * as THREE from 'three';

const NeuralGridBackground = () => {
    const { mouse } = useThree();
    const groupRef = useRef<THREE.Group>(null!);

    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, mouse.x * 0.1, 0.05);
            groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, -mouse.y * 0.1, 0.05);
        }
    });

    return (
        <group ref={groupRef}>
            <Float speed={0.5} rotationIntensity={0.5} floatIntensity={0.5}>
                <mesh>
                    <sphereGeometry args={[1, 32, 32]} />
                    <meshBasicMaterial wireframe color="#7F00FF" toneMapped={false} />
                </mesh>
            </Float>
        </group>
    );
};

const AICoreVisual = () => (
    <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={150} color="#7F00FF" />
        <Float speed={2} rotationIntensity={1}>
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial wireframe color="#00c6ff" toneMapped={false} />
            </mesh>
        </Float>
    </Canvas>
);

const DroneVisual = () => (
     <Canvas camera={{ position: [0, 0, 4], fov: 50 }}>
        <ambientLight intensity={1} />
        <directionalLight position={[0, 5, 5]} intensity={2}/>
        <Float speed={1.5} floatIntensity={0.5}>
            <group rotation={[0.3, Math.PI / 2, 0]}>
                 <mesh>
                    <boxGeometry args={[1.5, 0.1, 0.7]} />
                    <meshStandardMaterial color="#E0E0E0" roughness={0.3} />
                </mesh>
                 <mesh position={[0, 0.1, 0]}>
                    <cylinderGeometry args={[0.3, 0.2, 0.2, 32]} />
                    <meshStandardMaterial color="#BDBDBD" />
                </mesh>
            </group>
        </Float>
    </Canvas>
);

const SustainableGridVisual = () => (
    <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={100} color="#00c6ff" />
        <Float speed={1}>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.05, 16, 100]} />
                <meshStandardMaterial color="#00ffab" emissive="#00ffab" emissiveIntensity={2} toneMapped={false}/>
            </mesh>
            <mesh scale={0.6}>
                <sphereGeometry args={[1, 32, 32]} />
                <meshStandardMaterial wireframe color="#00c6ff" transparent opacity={0.5}/>
            </mesh>
        </Float>
    </Canvas>
);

const TechnologyCard = ({ icon, title, text }: { icon: React.ReactNode, title: string, text: string }) => (
  <motion.div 
    variants={{ hidden: { opacity: 0, y: 50 }, visible: { opacity: 1, y: 0 } }}
    className="h-96 p-6 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl flex flex-col justify-between"
  >
    <div className="h-2/5">{icon}</div>
    <div className="h-3/5 flex flex-col justify-end">
      <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
      <p className="text-gray-400">{text}</p>
    </div>
  </motion.div>
);

const AnimatedCounter = ({ value, label }: { value: number; label: string; }) => {
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
        <div className="text-center">
            <span ref={ref} className="text-5xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>0</span>
            <p className="text-gray-400 mt-2">{label}</p>
        </div>
    );
};

export default function AboutPage() {
  const scrollRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: scrollRef });
  const missionScale = useTransform(scrollYProgress, [0.1, 0.25], [0.9, 1]);
  const missionOpacity = useTransform(scrollYProgress, [0.1, 0.25], [0.5, 1]);

  return (
    <div ref={scrollRef} className="bg-black text-white" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
      
      <section className="relative h-screen w-full flex items-center justify-center text-center overflow-hidden">
        <div className="absolute inset-0 z-0 opacity-50">
            <Canvas>
                <Suspense fallback={null}>
                    <NeuralGridBackground />
                    <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                </Suspense>
            </Canvas>
        </div>
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: "easeOut" }}
            className="z-10 px-4"
        >
            <h1 className="text-5xl md:text-7xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                We’re Redefining the Meaning of Commerce.
            </h1>
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

      <section className="py-32 px-4 container mx-auto">
         <div className="text-center mb-16">
             <h2 className="text-4xl md:text-5xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>The AI Infrastructure</h2>
         </div>
        <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            transition={{ staggerChildren: 0.2 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto"
        >
            <TechnologyCard icon={<AICoreVisual />} title="AI Core" text="Self-learning algorithms managing global commerce autonomously." />
            <TechnologyCard icon={<DroneVisual />} title="Autonomous Drones" text="A fully automated aerial logistics network." />
            <TechnologyCard icon={<SustainableGridVisual />} title="Sustainable Grid" text="Zero-emission, energy-efficient operations." />
        </motion.div>
      </section>

       <section className="py-32 px-4 relative bg-black bg-grid-white/[0.05]">
            <div className="container mx-auto text-center">
                <p className="text-2xl text-gray-300 mb-12 max-w-3xl mx-auto">We’re not just delivering products — we’re delivering progress.</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <AnimatedCounter value={1200000} label="CO₂ Saved (tons)" />
                    <AnimatedCounter value={10582} label="Drones in Active Flight" />
                    <AnimatedCounter value={127} label="Cities Connected" />
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
                         <Image src={img} alt="Team member" width={128} height={128} className="w-24 h-24 md:w-32 md:h-32 rounded-full object-cover border-4 border-black/50 shadow-2xl" />
                    </motion.div>
                ))}
            </div>
        </div>
      </section>

      <footer className="relative py-20 px-4 text-center border-t border-white/10 overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-black/50 backdrop-blur-md" />
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>Be Part of the Revolution.</h2>
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
