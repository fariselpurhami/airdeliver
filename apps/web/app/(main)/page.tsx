'use client';

import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay'; 
import Link from 'next/link';
import Autoplay from 'embla-carousel-autoplay';
import useEmblaCarousel from 'embla-carousel-react';
import { Star } from 'lucide-react';
import { useInView } from 'react-intersection-observer';
import { User } from 'lucide-react';
import React, { Suspense, useRef, useMemo, useEffect, useState, ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Preload, Float, Line, Text, useTexture, OrbitControls } from '@react-three/drei';
import { motion, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion';
import { Bot, BrainCircuit, Leaf, Rocket, Zap, ArrowRight, Cpu, Map } from 'lucide-react';
import { X } from 'lucide-react'; // Using X for Twitter icon
import * as THREE from 'three';

// --- Main Page Component ---
export default function HomePage() {
  const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();

  return (
    <div className="min-h-screen w-full bg-black text-gray-100 overflow-x-hidden" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      <main className="relative z-10">
        <HeroSection onOrderClick={() => setOverlayVisible(true)} />
        <ValuePropositionSection />
        <HowItWorksSection />
        <ExperienceAISection />
        <GlobalScaleSection />
        <TestimonialsSection />
      </main>
      <AIChatOverlay isOpen={isOverlayVisible} onClose={() => setOverlayVisible(false)} />
    </div>
  );
}

// In app/(main)/page.tsx

// ============================================================================
// --- 1. HERO SECTION – "THE FUTURE BEGINS HERE" ---
// ============================================================================
const HeroSection = ({ onOrderClick }: { onOrderClick: () => void }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });
  const parallaxY = useTransform(scrollYProgress, [0, 1], ['0%', '50%']);

  return (
    <section ref={containerRef} className="relative h-screen w-full overflow-hidden">
      {/* ... (3D Background Canvas code remains the same) ... */}
      <div className="absolute inset-0 z-0">
        <Suspense fallback={<div className="w-full h-full bg-black" />}>
          <Canvas camera={{ position: [0, 0, 15], fov: 75 }}>
            <Hero3DBackground />
            <Preload all />
          </Canvas>
        </Suspense>
      </div>

      {/* Foreground Content */}
      <motion.div style={{ y: parallaxY }} className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
        {/* ... (h1 and p tags remain the same) ... */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="mb-4 text-sm font-light tracking-[0.3em] text-gray-400 uppercase"
        >
          AI. AUTONOMY. A NEW AGE OF COMMERCE.
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8 }}
          className="text-5xl md:text-7xl lg:text-8xl font-black uppercase"
          style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
          <span className="text-transparent bg-clip-text bg-gradient-to-br from-white to-gray-400">
            THE FUTURE
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.2 }}
          className="mt-6 max-w-2xl text-base md:text-lg text-gray-300"
        >
          Experience the world’s first AI-driven delivery network merging intelligence, speed, and sustainability.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.5 }}
          className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          {/* THIS BUTTON NOW USES the onOrderClick prop */}
          <button
            onClick={onOrderClick}
            className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 hover:scale-105 overflow-hidden"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative flex items-center">Order with AI <Bot className="ml-2 h-5 w-5" /></span>
          </button>

          <button className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-white bg-transparent border-2 border-white/20 rounded-full shadow-lg transition-all duration-300 hover:border-white/50 hover:bg-white/10">
            Explore Platform <ArrowRight className="ml-2 h-5 w-5" />
          </button>
        </motion.div>
      </motion.div>
    </section>
  );
};

// --- Hero 3D Background Component (Three.js / R3F) ---
const Hero3DBackground = () => {
  const { viewport, mouse } = useThree();
  const droneRef = useRef<THREE.Group>(null!);

  useFrame(() => {
    // Parallax effect for the drone
    if (droneRef.current) {
      droneRef.current.position.x = THREE.MathUtils.lerp(droneRef.current.position.x, mouse.x * 2, 0.05);
      droneRef.current.position.y = THREE.MathUtils.lerp(droneRef.current.position.y, mouse.y * 2, 0.05);
    }
  });

  return (
    <>
      <ambientLight intensity={1.5} />
      <pointLight position={[10, 10, 10]} intensity={200} color="#00C6FF" />
      <pointLight position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
      <NeuralGrid />
      <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
        <group ref={droneRef}>
          <DroneHologram position={[viewport.width / 4, 0, -2]} scale={0.5} />
          <DroneHologram position={[-viewport.width / 4, viewport.height / 4, -5]} scale={0.3} rotation={[0, Math.PI / 2, 0]} />
        </group>
      </Float>
      {/* City silhouette */}
      <mesh position={[0, -viewport.height / 2 - 2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[100, 20]} />
        <meshBasicMaterial color="#000" transparent opacity={0.8} fog={false} />
      </mesh>
    </>
  );
};

const NeuralGrid = () => {
  const materialRef = useRef<THREE.ShaderMaterial>(null!);
  const time = useRef(0);
  useFrame((_, delta) => {
    if (materialRef.current) {
      time.current += delta;
      materialRef.current.uniforms.time.value = time.current;
    }
  });

  const shader = {
    uniforms: { time: { value: 0 } },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float time;
      varying vec2 vUv;
      void main() {
        vec2 p = -1.0 + 2.0 * vUv;
        float a = atan(p.y, p.x);
        float r = length(p);

        float color = 0.0;

        // Animated grid
        vec2 grid = fract(vUv * 20.0);
        color += smoothstep(0.01, 0.02, grid.x);
        color += smoothstep(0.01, 0.02, grid.y);

        // Pulsing waves
        float wave = sin(r * 10.0 - time * 2.0) * 0.5 + 0.5;
        color *= smoothstep(0.4, 1.0, wave);

        gl_FragColor = vec4(vec3(color * 0.1, color * 0.3, color * 0.5), 1.0);
      }
    `,
  };

  return (
    <mesh>
      <planeGeometry args={[100, 100]} />
      <shaderMaterial ref={materialRef} args={[shader]} transparent opacity={0.3} />
    </mesh>
  );
};

const DroneHologram = (props: any) => {
  return (
    <group {...props}>
      <mesh>
        <boxGeometry args={[2, 0.2, 1]} />
        <meshStandardMaterial color="#00C6FF" emissive="#00C6FF" emissiveIntensity={2} transparent opacity={0.3} />
      </mesh>
      <Line points={[[-1, 0, -0.5], [-1, 0, 0.5], [1, 0, 0.5], [1, 0, -0.5], [-1, 0, -0.5]]} color="#fff" lineWidth={2} />
    </group>
  );
};


// ============================================================================
// --- 2. VALUE PROPOSITION SECTION – "BUILT DIFFERENT" ---
// ============================================================================
const ValuePropositionSection = () => {
  const features = [
    
    { visual: <DroneHologramCanvas />, text: "Self-navigating drones deliver your order in minutes.", title: "Autonomous Drone Network" },
    { visual: <AIBrain />, text: "Your intelligent assistant understands your needs instantly.", title: "AI Personal Shopper" },
    { visual: <MotionTrail />, text: "From order to doorstep in under 15 minutes.", title: "Lightning-Fast Fulfillment" },
    { visual: <EarthHologram />, text: "Zero-emission logistics powered by clean AI.", title: "Eco-Driven by Design" }
  ];

  return (
    <section className="py-24 px-4">
      <div className="container mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          className="text-center text-4xl font-bold mb-16" style={{ fontFamily: "'Orbitron', sans-serif" }}>BUILT DIFFERENT</motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, i) => (
            <GlassCard key={i} visual={feature.visual} title={feature.title} text={feature.text} />
          ))}
        </div>
      </div>
    </section>
  );
};

// --- Value Prop Visuals ---
// --- FIX: Added a dedicated Canvas wrapper for the Drone ---
const DroneHologramCanvas = () => {
  const DroneModel = () => {
    const ref = useRef<THREE.Group>(null!);
    // Adds a slow, continuous rotation to the drone
    useFrame(() => {
      if (ref.current) {
        ref.current.rotation.y += 0.005;
      }
    });

    return (
      <group ref={ref} scale={1.2} position={[0, -0.5, 0]}>
        {/* Main Body */}
        <mesh>
          <boxGeometry args={[1.5, 0.2, 0.8]} />
          <meshStandardMaterial color="#555" roughness={0.3} metalness={0.8} />
        </mesh>
        
        {/* Propeller Arms */}
        <mesh position={[-0.9, 0, 0.6]}>
          <boxGeometry args={[0.2, 0.1, 0.8]} />
          <meshStandardMaterial color="#444" roughness={0.4} metalness={0.7} />
        </mesh>
        <mesh position={[0.9, 0, 0.6]}>
          <boxGeometry args={[0.2, 0.1, 0.8]} />
          <meshStandardMaterial color="#444" roughness={0.4} metalness={0.7} />
        </mesh>
        <mesh position={[-0.9, 0, -0.6]}>
          <boxGeometry args={[0.2, 0.1, 0.8]} />
          <meshStandardMaterial color="#444" roughness={0.4} metalness={0.7} />
        </mesh>
        <mesh position={[0.9, 0, -0.6]}>
          <boxGeometry args={[0.2, 0.1, 0.8]} />
          <meshStandardMaterial color="#444" roughness={0.4} metalness={0.7} />
        </mesh>

        {/* Glowing Front Light */}
        <mesh position={[0, 0.1, -0.45]}>
            <circleGeometry args={[0.1, 16]} />
            <meshBasicMaterial color="#00c6ff" toneMapped={false} />
        </mesh>
      </group>
    );
  };
  
  return (
    <Canvas camera={{ position: [0, 1.5, 4], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={2.5} />
      <pointLight position={[0, 2, -5]} intensity={200} color="#00c6ff" />
      <pointLight position={[0, -2, 5]} intensity={150} color="#7F00FF" />
      
      <Suspense fallback={null}>
        <Float speed={1.5} rotationIntensity={0.5} floatIntensity={0.5}>
          <DroneModel />
        </Float>
      </Suspense>
    </Canvas>
  );
};



const AIBrain = () => (
    <Canvas camera={{position: [0, 0, 5]}}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={100} color="#00C6FF" />
        <Float speed={3}>
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshStandardMaterial wireframe color="#7F00FF" emissive="#7F00FF" emissiveIntensity={1} />
            </mesh>
        </Float>
    </Canvas>
);
const MotionTrail = () => <div className="w-full h-full bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] rounded-full blur-2xl animate-pulse"/>;
// ✅ الكود الصحيح
// 1. هنعمل component جديد للمجسم اللي بيلف
const WireframeGlobe = () => {
    const ref = useRef<THREE.Mesh>(null!);
    // دلوقتي الـ useFrame موجود جوه component هيتحط جوه الـ Canvas
    useFrame(() => {
        if(ref.current) ref.current.rotation.y += 0.01
    });

    return (
        <mesh ref={ref}>
            <sphereGeometry args={[1, 32, 32]} />
            <meshStandardMaterial wireframe color="#00C6FF" />
        </mesh>
    );
}

// 2. هنعدل الـ EarthHologram عشان يستخدم الـ component الجديد
const EarthHologram = () => {
    return (
        <Canvas camera={{position: [0, 0, 2.5]}}>
            <ambientLight intensity={0.2} />
            <pointLight position={[5, 5, 5]} intensity={50} color="#fff" />
            <WireframeGlobe /> {/* <-- بنستخدم الـ component الجديد هنا */}
        </Canvas>
    );
};


// --- Glass Card UI Component ---
interface GlassCardProps { visual: ReactNode; title: string; text: string; }
const GlassCard = ({ visual, title, text }: GlassCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 50, scale: 0.95 }}
    whileInView={{ opacity: 1, y: 0, scale: 1 }}
    whileHover={{ scale: 1.05, y: -10 }}
    viewport={{ once: true, amount: 0.3 }}
    transition={{ duration: 0.5 }}
    className="relative p-6 aspect-square flex flex-col justify-between overflow-hidden rounded-2xl bg-white/[.05] backdrop-blur-xl border border-white/10"
  >
    <div className="absolute -inset-px opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl">
      <div className="absolute inset-[-200%] animate-[spin_4s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#00c2ff_0%,#7F00FF_50%,#00c2ff_100%)]" />
    </div>
    <div className="relative z-10 h-1/2">{visual}</div>
    <div className="relative z-10">
      <h3 className="mb-2 text-lg font-bold" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
      <p className="text-gray-400 text-sm">{text}</p>
    </div>
  </motion.div>
);

// ============================================================================
// --- 3. HOW IT WORKS SECTION – "THE AI SUPPLY CHAIN" ---
// ============================================================================
const timelineSteps = [
  {
    icon: <Bot size={28} />,
    step: 1,
    title: "AI Takes Your Order",
    description: "Simply tell our AI what you need. It understands natural language to start your order instantly."
  },
  {
    icon: <Cpu size={28} />,
    step: 2,
    title: "Smart System Finds Best Option",
    description: "Our AI core analyzes millions of data points to find the fastest, most efficient delivery route for you."
  },
  {
    icon: <Map size={28} />,
    step: 3,
    title: "Instant Order Tracking",
    description: "Monitor your delivery in real-time on a holographic map from the moment of dispatch."
  },
  {
    icon: <Rocket size={28} />,
    step: 4,
    title: "Fast, Optimized Delivery",
    description: "Your order arrives via an autonomous drone, completing the journey with unparalleled speed and precision."
  },
];

const HowItWorksSection = () => {

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.3, // يخلق تأخيرًا بين أنيميشن كل بطاقة
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 50 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: 'easeOut' } },
  };

  return (
    <section className="relative w-full py-24 px-4 bg-black overflow-hidden">
      {/* شبكة خلفية خفية */}
      <div className="absolute inset-0 bg-grid-white/[0.05]" />

      <div className="container mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.8 }}
          className="text-center text-4xl md:text-5xl font-black uppercase text-white mb-20"
          style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
          How It Works
        </motion.h2>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          className="relative max-w-2xl mx-auto"
        >
          {/* الخط الزمني المتوهج */}
          <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-cyan-400/20 -translate-x-1/2">
            <div className="absolute top-0 left-0 h-full w-full bg-cyan-400 blur-md" />
          </div>

          {timelineSteps.map((item, index) => (
            <motion.div
              key={item.step}
              variants={cardVariants}
              className="relative mb-12 flex items-center"
              style={{
                justifyContent: index % 2 === 0 ? 'flex-start' : 'flex-end',
              }}
            >
              <div className={`w-1/2 ${index % 2 === 0 ? 'pr-8 text-right' : 'pl-8 text-left'}`}>
                <motion.div
                  whileHover={{ scale: 1.05, y: -5 }}
                  className="p-6 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl cursor-pointer"
                >
                  <div className={`flex items-center gap-4 mb-3 ${index % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
                    <span className="text-sm text-gray-500">STEP {item.step}</span>
                    <div className="text-cyan-400 glowing-icon">{item.icon}</div>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {item.title}
                  </h3>
                  <p className="text-sm text-gray-400">{item.description}</p>
                </motion.div>
              </div>

              {/* النقطة المتوهجة على الخط الزمني */}
              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-cyan-400 border-2 border-black">
                 <div className="absolute inset-0 rounded-full bg-cyan-400 blur-sm animate-pulse" />
              </div>

            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

// ============================================================================
// --- 4. EXPERIENCE AI INTERACTION (LIVE DEMO) ---
// ============================================================================
// Custom Hook for Parallax Effect
const useParallax = (ref: React.RefObject<HTMLDivElement>) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const xTransform = useTransform(x, [-100, 100], [-15, 15]);
  const yTransform = useTransform(y, [-100, 100], [-15, 15]);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = element.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const xPct = (mouseX / width - 0.5) * 2;
      const yPct = (mouseY / height - 0.5) * 2;

      x.set(xPct * 100);
      y.set(yPct * 100);
    };

    const handleMouseLeave = () => {
      x.set(0);
      y.set(0);
    };

    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [ref, x, y]);

  return { rotateX: yTransform, rotateY: xTransform };
};


const ExperienceAISection = () => {
  const parallaxRef = useRef<HTMLDivElement>(null);
  const { rotateX, rotateY } = useParallax(parallaxRef);

  return (
    <section className="relative py-24 px-4 overflow-hidden">
      <div className="container mx-auto flex flex-col items-center text-center">
        {/* Text Content */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            Try the Future Today.
          </h2>
          <p className="max-w-xl mx-auto text-gray-400 mb-12">
            Talk to our AI Shopper and get your order in seconds.
          </p>
        </motion.div>

        {/* Interactive Mockup */}
        <motion.div
          ref={parallaxRef}
          style={{
            transformStyle: "preserve-3d",
            rotateX,
            rotateY,
          }}
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="relative w-full max-w-2xl aspect-video"
        >
          <div className="absolute inset-[-2px] rounded-2xl bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] blur-md" />

          <div className="relative w-full h-full p-4 md:p-6 flex flex-col bg-black/50 backdrop-blur-2xl border border-white/10 rounded-2xl overflow-hidden" style={{ transform: "translateZ(30px)" }}>
            {/* Window Header */}
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>

            {/* Chat Bubbles */}
            <div className="flex-grow space-y-4 text-left text-sm">
              <div className="flex items-end gap-2 justify-end">
                <p className="max-w-[70%] bg-blue-500/30 text-white p-3 rounded-lg rounded-br-none">
                  I want to buy an iphone 17 pro with and have it delivered to me tomorrow
                </p>
                <User className="w-6 h-6 p-1 bg-white/10 rounded-full text-white"/>
              </div>
              <div className="flex items-end gap-2">
                <Bot className="w-6 h-6 p-1 bg-white/10 rounded-full text-[#00C6FF]"/>
                <p className="max-w-[70%] bg-white/10 p-3 rounded-lg rounded-bl-none">
                  Sure! Please confirm the color and storage size so i can schedule delivery for tomorrow.
                </p>
              </div>
            </div>

            {/* Input Bar */}
            <div className="mt-4 w-full h-10 bg-black/30 rounded-full" />
          </div>
        </motion.div>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="mt-12"
        >
          <button className="group relative inline-flex items-center justify-center px-10 py-5 text-lg font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 hover:scale-105 overflow-hidden">
            <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative flex items-center">Start your first AI order now <Bot className="ml-3 h-6 w-6" /></span>
          </button>
        </motion.div>

      </div>
    </section>
  );
};


// ============================================================================
// --- 5. GLOBAL SCALE SECTION – "POWERING THE WORLD" ---
// ============================================================================
// --- Helper Component: Animated Counter ---
const AnimatedCounter = ({ value, text }: { value: number, text: string }) => {
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.5 });
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { damping: 100, stiffness: 100 });
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (isInView) {
      motionValue.set(value);
    }
  }, [motionValue, isInView, value]);

  useEffect(() =>
    springValue.on("change", (latest) => {
      if (ref.current) {
        (ref.current as HTMLElement).textContent = Intl.NumberFormat('en-US').format(latest.toFixed(0));
      }
    }),
  [springValue, ref]);

  return (
    <div className="text-center">
      <p ref={ref} className="text-4xl md:text-5xl font-bold text-white tabular-nums" style={{fontFamily: "'Orbitron', sans-serif"}} />
      <p className="text-sm text-gray-400 uppercase tracking-widest mt-2">{text}</p>
    </div>
  );
};


// --- Helper Component: 3D Globe ---
const Globe = () => {
    const globeRef = useRef<THREE.Group>(null!);
    const texture = useTexture('/textures/dark_earth.jpg'); // ضع هنا مسار صورة خريطة العالم

    // بيانات المدن والمسارات
    const points = useMemo(() => [
        { lat: 40.7128, lon: -74.0060 }, // New York
        { lat: 51.5074, lon: -0.1278 },  // London
        { lat: 35.6895, lon: 139.6917 }, // Tokyo
        { lat: 34.0522, lon: -118.2437 },// LA
        { lat: -33.8688, lon: 151.2093 },// Sydney
    ], []);

    const [paths, setPaths] = useState<THREE.CatmullRomCurve3[]>([]);
    const pulseRef = useRef<THREE.Mesh>(null!);
    const pulseIndex = useRef(0);
    const pulseProgress = useRef(0);

    // تحويل الإحداثيات وإنشاء المسارات
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
        const routes = [
            [points[0], points[1]],
            [points[2], points[3]],
            [points[3], points[4]],
            [points[1], points[2]],
        ];
        const curves = routes.map(([p1, p2]) => {
            const v1 = getPos(p1.lat, p1.lon);
            const v2 = getPos(p2.lat, p2.lon);
            const midPoint = new THREE.Vector3().addVectors(v1, v2).multiplyScalar(0.5).normalize().multiplyScalar(radius * 1.2);
            return new THREE.CatmullRomCurve3([v1, midPoint, v2]);
        });
        setPaths(curves);
    }, [points]);

    useFrame((state, delta) => {
        globeRef.current.rotation.y += delta * 0.1;

        // Pulse Animation
        if (paths.length > 0 && pulseRef.current) {
            pulseProgress.current += delta * 0.5;
            if (pulseProgress.current >= 1) {
                pulseProgress.current = 0;
                pulseIndex.current = (pulseIndex.current + 1) % paths.length;
            }
            const currentPath = paths[pulseIndex.current];
            currentPath.getPointAt(pulseProgress.current, pulseRef.current.position);
        }
    });

    return (
        <group ref={globeRef}>
            {/* The Globe */}
            <mesh>
                <sphereGeometry args={[5, 64, 64]} />
                <meshStandardMaterial map={texture} color="#333" roughness={0.7} />
            </mesh>
            {/* The Routes */}
            {paths.map((curve, i) => (
                <mesh key={i}>
                    <tubeGeometry args={[curve, 64, 0.02]} />
                    <meshBasicMaterial color="#7F00FF" toneMapped={false} />
                </mesh>
            ))}
            {/* The Pulse */}
            <mesh ref={pulseRef}>
                <sphereGeometry args={[0.08, 8, 8]} />
                <meshBasicMaterial color="#00C6FF" toneMapped={false} />
            </mesh>
        </group>
    );
};


const GlobalScaleSection = () => {
    return (
        <section className="relative py-24 px-4 h-[100vh] flex flex-col justify-center items-center overflow-hidden">
            {/* 3D Canvas */}
            <div className="absolute inset-0 z-0">
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <ambientLight intensity={0.2} />
                    <directionalLight position={[5, 5, 5]} intensity={1} />
                    <Suspense fallback={null}>
                       <Globe />
                    </Suspense>
                    <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
                </Canvas>
            </div>

            {/* Foreground Content */}
            <div className="relative z-10 container mx-auto text-center">
                 <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.5 }}
                    transition={{ duration: 0.8 }}
                >
                    <h2 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Global Scale
                    </h2>
                    <p className="max-w-xl mx-auto text-gray-400 mb-16">
                        Expanding Worldwide. Powered by AI.
                    </p>
                </motion.div>

                {/* Animated Stats */}
                <motion.div
                     initial={{ opacity: 0, y: 30 }}
                     whileInView={{ opacity: 1, y: 0 }}
                     viewport={{ once: true, amount: 0.5 }}
                     transition={{ duration: 0.8, delay: 0.2 }}
                     className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto"
                >
                    <AnimatedCounter value={1843} text="Drones in Flight" />
                    <AnimatedCounter value={212} text="Cities Connected" />
                    <AnimatedCounter value={947204} text="Orders Delivered" />
                </motion.div>
            </div>
        </section>
    );
};
// ============================================================================
// --- 6. TESTIMONIALS / PARTNERS ---
// ============================================================================

// --- Dummy Data ---
const testimonials = [
  {
    name: 'Elena M.',
    title: 'CEO, NeoCommerce',
    quote: "airdeliver isn't just a service; it's the future of logistics. The speed and autonomy are unparalleled.",
    rating: 5,
    avatar: '/avatars/avatar1.png'
  },
  {
    name: 'Kenji T.',
    title: 'Lead Futurist, QuantumLeap',
    quote: "The AI's efficiency in optimizing routes is something we thought was years away. It's here now.",
    rating: 5,
    avatar: '/avatars/avatar2.png'
  },
  {
    name: 'Fatima Z.',
    title: 'Head of Innovation, EcoSpear',
    quote: "Sustainability is key for us. airdeliver's zero-emission network is a game-changer for green commerce.",
    rating: 5,
    avatar: '/avatars/avatar3.png'
  },
];

// --- STEP 1: Define logos as proper components ---
const OpenAILogo = () => <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12.012 24c-2.48.006-4.885-1.02-6.6-2.857a8.21 8.21 0 0 1-2.92-6.319c.045-4.572 3.655-8.23 8.16-8.28a8.21 8.21 0 0 1 8.353 7.5c.012.35.024.7.024 1.05a8.21 8.21 0 0 1-8.21 8.21v.696zm-4.74-13.416a5.53 5.53 0 0 0-1.812 4.128c-.024 3.09 2.469 5.61 5.52 5.634 3.052.024 5.544-2.445 5.568-5.538a5.53 5.53 0 0 0-5.568-5.538 5.53 5.53 0 0 0-3.708 1.314zm9.432-3.348a1.2 1.2 0 0 0-1.2-1.206 1.2 1.2 0 0 0-1.206 1.206 1.2 1.2 0 0 0 1.206 1.206 1.2 1.2 0 0 0 1.2-1.206zm-3.372 0a1.2 1.2 0 0 0-1.2-1.206 1.2 1.2 0 0 0-1.206 1.206 1.2 1.2 0 0 0 1.206 1.206 1.2 1.2 0 0 0 1.2-1.206zm-6.72-.012a1.2 1.2 0 0 0-1.206-1.206 1.2 1.2 0 0 0-1.206 1.206 1.2 1.2 0 0 0 1.206 1.218 1.2 1.2 0 0 0 1.206-1.218zm-3.36.012a1.2 1.2 0 0 0-1.2-1.206 1.2 1.2 0 0 0-1.206 1.206 1.2 1.2 0 0 0 1.206 1.206 1.2 1.2 0 0 0 1.2-1.206zm12.24-2.52a1.2 1.2 0 0 0-1.2-1.206 1.2 1.2 0 0 0-1.206 1.206 1.2 1.2 0 0 0 1.206 1.206 1.2 1.2 0 0 0 1.2-1.206z"/></svg>;
const AmazonLogo = () => <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M22.51 16.42c-.22 2.6-2.53 3.52-5.74 3.52-2.1 0-3.4-.6-4.5-1.58-.95.8-2.1 1.48-3.9 1.48-2.9 0-5.38-1.5-5.38-4.48 0-2.3 1.2-3.6 3.4-3.6 1.8 0 2.9.8 3.8 1.68h.1l3.5-3.3c.2-.2.4-.3.7-.3.3 0 .5.1.7.3l2.8 2.8c.2.2.3.4.3.7s-.1.5-.3.7l-3.3 3.3v.1c.9.9 2.1 1.9 4.3 1.9.9 0 1.5-.2 2.1-.4.2.9.4 1.7.5 2.6zm-12.8-1.4c-1.2 0-2 .6-2 1.7 0 .8.5 1.6 1.6 1.6.8 0 1.3-.4 1.9-.9l.2-.2c-.8-1.3-1.6-2.2-3.3-2.2zm7.6 0c-1.7 0-2.6.9-3.4 2.2l.1.1c.6.5 1.1.9 1.9.9 1.1 0 1.6-.8 1.6-1.6 0-1.1-.8-1.6-1.8-1.6zM2.5 11.83c.7-1.1 1.8-1.7 2.9-1.7 1.4 0 2.3.6 2.3 1.9 0 1.1-.7 1.6-1.6 1.6-.9 0-1.5-.3-2.2-.8-.8.6-1.3 1.6-1.3 2.6 0 1.5 1.1 2.2 2.3 2.2 1.3 0 2.4-.6 3-1.6h.1l-1.1-3.6-1.2-3.8c-.2-.5-.3-.7-.9-.7s-.6.2-.8.6L.4 12.83c-.3.8-.4 1.5-.4 2.3 0 3.2 2.3 4.8 5.4 4.8 3.1 0 5.4-1.6 5.4-4.8 0-2.3-1.3-3.6-3.4-3.6-1.9 0-3 .8-4-1.6L2.5 11.83z"/></svg>;
const AppleLogo = () => <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12.15.2h-.03C9.9.22 7.74 1.83 6.9 3.84c-1.32 3.13.2 6.7 2.3 8.63.95.9 2.08 1.44 3.32 1.44.1 0 .2-.02.3-.02.9-.06 2.2-1.07 3.3-2.67-1.4-.87-2.28-2.4-2.28-4.08 0-2.58 1.83-4.58 4.22-4.82-.1-.02-.22-.04-.33-.04-1.47 0-2.83.65-3.8 1.7-1.02-1.24-2.58-2-4.3-2.02zm8.13 11.23c-.6-.78-1.25-1.53-2.23-1.82-.9.27-1.93.5-2.93.5-1.33 0-2.6-.4-3.68-1.1-.9.28-1.85.52-2.85.52-1.4 0-2.8-.48-3.83-1.2-.55 1.78-.55 3.53.03 5.23.8 2.43 2.43 4.5 4.63 5.8 1.1.65 2.3.97 3.55.97.22 0 .43-.02.65-.05.18-.03.35-.07.52-.13 1.15-.35 2.2-1.04 2.95-2.02-.18-.1-.35-.22-.52-.35a6.4 6.4 0 0 1-2.96-3.8c.85-.23 1.9-.7 2.73-1.38z"/></svg>;
const TeslaLogo = () => <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12.33 23.32a.3.3 0 0 1-.2-.07.32.32 0 0 1-.13-.25l-1.2-10.32H5.33c-.2 0-.3-.1-.3-.29a.3.3 0 0 1 .1-.2L11.8.68a.3.3 0 0 1 .5 0L19 12.19a.3.3 0 0 1 .1.2c0 .19-.1.29-.3.29h-5.48l-1.2 10.32c0 .12-.05.2-.13.25a.3.3 0 0 1-.2.07zm-5.4-11h4.63a.3.3 0 0 1 .3.28l.8 6.9 4.18-7.18h-4.6a.3.3 0 0 1-.3-.28l-.8-6.9-4.18 7.18z"/></svg>;

// --- STEP 2: Reference them in the array ---
const partners = [
    { name: 'OpenAI', logo: OpenAILogo },
    { name: 'Amazon', logo: AmazonLogo },
    { name: 'Apple', logo: AppleLogo },
    { name: 'Tesla', logo: TeslaLogo },
];

// --- Sub-Component: Testimonial Card ---
const TestimonialCard = ({ testimonial }: { testimonial: typeof testimonials[0] }) => {
    return (
        <motion.div
            whileHover={{ scale: 1.05, zIndex: 10, y: -10 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            className="flex-shrink-0 w-[80%] md:w-[40%] p-6 bg-white/[.05] backdrop-blur-xl border border-white/10 rounded-2xl cursor-pointer"
        >
            <div className="flex items-start gap-4">
                <div className="relative">
                    <img src={testimonial.avatar} alt={testimonial.name} className="w-14 h-14 rounded-full object-cover" />
                    <div className="absolute -inset-0.5 rounded-full border-2 border-[#00C6FF] blur-sm" />
                </div>
                <div>
                    <p className="font-bold text-white">{testimonial.name}</p>
                    <p className="text-xs text-gray-400">{testimonial.title}</p>
                </div>
            </div>
            <p className="text-gray-300 mt-4 text-sm">"{testimonial.quote}"</p>
            <div className="flex mt-4">
                {Array.from({ length: 5 }).map((_, i) => (
                    <motion.div
                        key={i}
                        animate={{ scale: i < testimonial.rating ? [1, 1.2, 1] : 1 }}
                        transition={{ duration: 1, repeat: Infinity, delay: i * 0.1 }}
                    >
                        <Star className={`w-4 h-4 ${i < testimonial.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`} />
                    </motion.div>
                ))}
            </div>
        </motion.div>
    );
};

// --- Main Section Component ---
const TestimonialsSection = () => {
  const [emblaRef] = useEmblaCarousel({ loop: true, align: 'start' }, [Autoplay({ delay: 4000 })]);

  const partnerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  return (
    <section className="py-24 px-4 overflow-hidden relative">
      <div className="absolute inset-0 -z-10 bg-black bg-grid-white/[0.05]" />
      <div className="container mx-auto">
        {/* Main Title */}
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12"
        >
            <h2 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                Trusted by Innovators. Loved by Visionaries.
            </h2>
            <p className="max-w-2xl mx-auto text-gray-400">
                From global tech leaders to first-time users — airdeliver is redefining what commerce feels like.
            </p>
        </motion.div>

        {/* Testimonials Carousel */}
        <div className="overflow-hidden" ref={emblaRef}>
            <div className="flex gap-4">
                {testimonials.map((t, i) => (
                    <TestimonialCard key={i} testimonial={t} />
                ))}
            </div>
        </div>

        {/* Partners Grid */}
        <div className="mt-24">
            <motion.div
                variants={partnerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.2 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center"
            >
                {partners.map((p, i) => (
                    <motion.div
                        key={i}
                        variants={partnerVariants}
                        className="flex justify-center"
                    >
                        <motion.div
                            whileHover={{
                                scale: 1.1,
                                filter: 'grayscale(0%) drop-shadow(0 0 8px #7F00FF)',
                                opacity: 1,
                            }}
                            className="w-24 h-12 fill-current text-gray-400 opacity-60 transition-all duration-300 filter grayscale"
                        >
                            <p.logo />
                        </motion.div>
                    </motion.div>
                ))}
            </motion.div>
        </div>
      </div>
    </section>
  );
};
