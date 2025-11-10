'use client';

import { ShieldCheck, Lock, Clock } from 'lucide-react';
import { useUIStore } from '@/hooks/useUIStore';
import ProductOverlay from '@/components/products/ProductOverlay';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay'; 
import Link from 'next/link';
import Autoplay from 'embla-carousel-autoplay';
import useEmblaCarousel from 'embla-carousel-react';
import { Star } from 'lucide-react';
import React, { Suspense, useRef, useMemo, useEffect, useState, ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Preload, Float, Line, Text, useTexture, OrbitControls, Stars } from '@react-three/drei';
import { motion, useScroll, useSpring, useInView, useTransform, useMotionValue } from 'framer-motion';
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
          className="text-6xl md:text-7xl lg:text-8xl font-black uppercase"
          style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
          <motion.span
            className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
            animate={{
              filter: [
                'drop-shadow(0 0 16px rgba(0, 198, 255, 0.7)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.7))',
                'drop-shadow(0 0 24px rgba(0, 198, 255, 1)) drop-shadow(0 0 24px rgba(168, 85, 247, 1))',
                'drop-shadow(0 0 16px rgba(0, 198, 255, 0.7)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.7))'
              ]
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            COMMERCE. TAKES FLIGHT.
          </motion.span>
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
            <span className="relative flex items-center">Order with air <Bot className="ml-2 h-5 w-5" /></span>
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
        count={44000}
        factor={6}
        saturation={0}
        fade
        speed={1.5}
      />
    </group>
  );
};

// ============================================================================
// --- 3. HOW IT WORKS SECTION (Definition) ---
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
        staggerChildren: 0.3, 
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 50 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: 'easeOut' } },
  };

  return (
    <section className="relative w-full py-24 px-4 bg-black overflow-hidden">
      <div className="absolute inset-0 bg-grid-cyan-400/[0.05]" />

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
          <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-cyan-400/20 -translate-x-1/2">
            <div className="absolute top-0 left-0 h-full w-full bg-cyan-400 blur-md animate-pulse" />
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
                  whileHover={{ 
                    scale: 1.03, 
                    y: -5,
                    borderColor: 'rgba(0, 198, 255, 0.7)', 
                    boxShadow: '0 0 24px rgba(0, 198, 255, 0.3)' 
                  }}
                  className="p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl cursor-pointer shadow-lg shadow-cyan-500/10 transition-all duration-300"
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
// --- 5. GLOBAL SCALE SECTION (Definition) ---
// ============================================================================

const AnimatedCounter = ({ value, text }: { value: number, text: string }) => {
  const ref = useRef<HTMLParagraphElement>(null);
  const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { damping: 100, stiffness: 100 });

  useEffect(() => {
    if (isInView) {
      motionValue.set(value);
    }
  }, [motionValue, isInView, value]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      if (ref.current) {
        ref.current.textContent = Intl.NumberFormat('en-US').format(Math.round(latest));
      }
    });
    return unsubscribe;
  }, [springValue]);

  return (
    <>
      <p ref={ref} className="text-4xl md:text-5xl font-bold text-white tabular-nums" style={{fontFamily: "'Orbitron', sans-serif"}}>
        0
      </p>
      <p className="text-sm text-gray-400 uppercase tracking-widest mt-2">{text}</p>
    </>
  );
};

const Globe = () => {
    const globeRef = useRef<THREE.Group>(null!);
    const texture = useTexture('/textures/dark_earth.jpg');

    const points = useMemo(() => [
        { lat: 40.7128, lon: -74.0060 },
        { lat: 51.5074, lon: -0.1278 },
        { lat: 35.6895, lon: 139.6917 },
        { lat: 34.0522, lon: -118.2437 },
        { lat: -33.8688, lon: 151.2093 },
    ], []);

    const [paths, setPaths] = useState<THREE.CatmullRomCurve3[]>([]);
    const pulseRef = useRef<THREE.Mesh>(null!);
    const pulseIndex = useRef(0);
    const pulseProgress = useRef(0);

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
            <mesh>
                <sphereGeometry args={[5, 64, 64]} />
                <meshStandardMaterial map={texture} color="#666" emissive="#333" roughness={0.7} />
            </mesh>
            {paths.map((curve, i) => (
                <mesh key={i}>
                    <tubeGeometry args={[curve, 64, 0.02]} />
                    <meshBasicMaterial color="#7F00FF" toneMapped={false} />
                </mesh>
            ))}
            <mesh ref={pulseRef}>
                <sphereGeometry args={[0.08, 8, 8]} />
                <meshBasicMaterial color="#00C6FF" toneMapped={false} />
            </mesh>
        </group>
    );
};

const GlobeScene = () => {
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
            <fog attach="fog" args={['#000000', 10, 30]} />
            <ambientLight intensity={0.4} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
            <Starfield />
            <Suspense fallback={null}>
                <Globe />
            </Suspense>
            <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.4} />
            <Cleanup />
        </>
    );
}

const GlobalScaleSection = () => {
    return (
        <section className="relative h-screen w-full overflow-hidden bg-black">
            <div className="absolute inset-0 z-0 opacity-70">
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <GlobeScene />
                </Canvas>
            </div>

            <div className="relative z-10 container mx-auto h-full flex flex-col justify-between text-center py-24 px-4">
                 <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.5 }}
                    transition={{ duration: 0.8 }}
                >
                    <h2 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        GLOBAL SCALE
                    </h2>
                    <p className="max-w-xl mx-auto text-gray-400 mb-16">
                        Powering the Autonomous Future. One Delivery at a Time.
                    </p>
                </motion.div>

                <motion.div
                     initial={{ opacity: 0, y: 30 }}
                     whileInView={{ opacity: 1, y: 0 }}
                     viewport={{ once: true, amount: 0.5 }}
                     transition={{ duration: 0.8, delay: 0.2 }}
                     className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto w-full"
                >
                    <div className="p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10">
                        <Rocket className="h-8 w-8 text-cyan-400 mx-auto mb-3" />
                        <AnimatedCounter value={1843} text="Drones in Flight" />
                    </div>
                     <div className="p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10">
                        <Map className="h-8 w-8 text-cyan-400 mx-auto mb-3" />
                        <AnimatedCounter value={212} text="Cities Connected" />
                    </div>
                     <div className="p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10">
                        <Zap className="h-8 w-8 text-cyan-400 mx-auto mb-3" />
                        <AnimatedCounter value={947204} text="Orders Delivered" />
                    </div>
                </motion.div>
            </div>
        </section>
    );
};

// ============================================================================
// --- 6. TESTIMONIALS (Definition) ---
// ============================================================================

const testimonials = [
  {
    name: 'Elena',
    title: 'CEO, Neo',
    quote: "airdeliver isn't justa service; it's the future of logistics. The speed and autonomy are unparalleled.",
    rating: 5,
    avatar: '/avatars/avatar1.png'
  },
  {
    name: 'Kenji',
    title: 'Lead Futurist, QuantumLeap',
    quote: "The AI's efficiency in optimizing routes is something we thought was years away. It's here now.",
    rating: 5,
    avatar: '/avatars/avatar2.png'
  },
  {
    name: 'Fatima',
    title: 'Head of Innovation, EcoSpear',
    quote: "Sustainability is key for us. airdeliver's zero-emission network is a game-changer for green commerce.",
    rating: 5,
    avatar: '/avatars/avatar3.png'
  },
];

const TrustSignal = ({ icon, text }: { icon: React.ReactNode; text: string }) => (
    <div className="flex flex-col items-center justify-center h-full text-center gap-2 text-white">
        <div className="text-cyan-400 h-8 w-8 flex items-center justify-center">{icon}</div>
        <span className="text-xs font-semibold tracking-wider uppercase">{text}</span>
    </div>
);

const trustSignals = [
    { name: 'Secure Payments', component: () => <TrustSignal icon={<Lock size={24} />} text="Secure Payments" /> },
    { name: 'Eco-Friendly', component: () => <TrustSignal icon={<Leaf size={24} />} text="Eco-Friendly" /> },
    { name: 'Insured', component: () => <TrustSignal icon={<ShieldCheck size={24} />} text="Insured & Reliable" /> },
    { name: '24/7 Service', component: () => <TrustSignal icon={<Clock size={24} />} text="24/7 Service" /> },
];

const TestimonialCard = ({ testimonial }: { testimonial: typeof testimonials[0] }) => {
    return (
        <motion.div
            whileHover={{ scale: 1.05, zIndex: 10, y: -10 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            className="flex-shrink-0 w-[80%] md:w-[40%] p-6 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl cursor-pointer shadow-lg shadow-cyan-500/10"
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
                        <Star className={`w-4 h-4 ${i < testimonial.rating ? 'text-cyan-400 fill-cyan-400' : 'text-gray-600'}`} />
                    </motion.div>
                ))}
            </div>
        </motion.div>
    );
};

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
    <section className="py-24 px-4 overflow-hidden relative bg-black">
      <div className="absolute inset-0 -z-10 bg-black bg-grid-cyan-400/[0.05]" />
      <div className="container mx-auto">
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

        <div className="overflow-hidden" ref={emblaRef}>
            <div className="flex gap-4">
                {testimonials.map((t, i) => (
                    <TestimonialCard key={i} testimonial={t} />
                ))}
            </div>
        </div>

        <div className="mt-24">
            <motion.div
                variants={partnerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.2 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center"
            >
                {trustSignals.map((signal, i) => (
                    <motion.div
                        key={i}
                        variants={partnerVariants}
                        className="flex justify-center"
                    >
                        <motion.div
                            whileHover={{
                                scale: 1.1,
                                borderColor: 'rgba(0, 198, 255, 0.5)',
                                boxShadow: '0 0 16px rgba(0, 198, 255, 0.3)',
                                opacity: 1,
                            }}
                            className="h-full w-full p-4 bg-white/5 border border-white/10 rounded-lg opacity-70 transition-all duration-300"
                        >
                            <signal.component />
                        </motion.div>
                    </motion.div>
                ))}

            </motion.div>
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

export default function HomePage() {
  const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();
  const { isProductOverlayVisible, showProductOverlay, hideProductOverlay } = useUIStore();

  return (
    <div className="min-h-screen w-full text-gray-100 overflow-x-hidden bg-black" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      <main className="relative z-10">
        <DynamicHeroSection onOrderClick={() => setOverlayVisible(true)} onExploreClick={showProductOverlay} />
        <HowItWorksSection />
        <DynamicGlobalScaleSection />
        <TestimonialsSection />
      </main>
      <ProductOverlay isOpen={isProductOverlayVisible} onClose={hideProductOverlay} />
    </div>
  );
}
