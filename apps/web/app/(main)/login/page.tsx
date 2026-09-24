//** apps/web/app/(main)/login/page.tsx **//

'use client';

import React, { useState, Suspense, useEffect, useMemo, memo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload } from '@react-three/drei';
import Image from 'next/image';
import { Mail, Lock, User, ArrowRight, ShieldCheck, Globe, Zap } from 'lucide-react';
import * as THREE from 'three';

// ============================================================================
// --- 1. HIGH-PERFORMANCE 3D BACKGROUND (WHITE STARS) ---
// ============================================================================
const premiumEasing = [0.16, 1, 0.3, 1];

const heroCanvasConfig = {
  camera: { position: [0, 0, 15] as [number, number, number], fov: 75 },
  dpr: [1, 1.5] as [number, number],
  gl: { antialias: false, powerPreference: "high-performance" as const, alpha: true, depth: false, stencil: false },
};

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

const ParticleField = memo(({ count, radius, color, size, rotationSpeed }: any) => {
  const groupRef = useRef<THREE.Group>(null!);
  const pointsRef = useRef<THREE.Points>(null!);
  const positions = useMemo(() => createParticlePositions(count, radius), [count, radius]);
  const materialColor = useMemo(() => new THREE.Color(color), [color]);

  useEffect(() => {
    if (pointsRef.current) pointsRef.current.matrixAutoUpdate = false;
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const safeDelta = delta > 0.1 ? 0.1 : delta;
    groupRef.current.rotation.x += safeDelta * rotationSpeed.x;
    groupRef.current.rotation.y += safeDelta * rotationSpeed.y;
    groupRef.current.rotation.z += safeDelta * rotationSpeed.z;
  });

  return (
    <group ref={groupRef} position={[0, 0, -60]}>
      <points ref={pointsRef} frustumCulled={false}>
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

// ============================================================================
// --- 2. FLOATING PRODUCT CARDS ---
// ============================================================================
const AuthFloatingProduct = memo(({
    title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation
}: any) => (
    <motion.div
        className={`absolute z-0 ${positionClasses} ${sizeClasses} will-change-transform`}
        initial={{ opacity: 0, scale: 0.8, rotate: rotation + 10 }}
        animate={{ opacity: 1, scale: 1, rotate: rotation }}
        transition={{ opacity: { duration: 1, delay }, scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 } }}
    >
        <motion.div animate={{ y: [0, -15, 0] }} transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }} className="w-full h-full will-change-transform">
            <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 pointer-events-none ${colorCls}`}>
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
                <Image src={image} alt={category} fill sizes="(max-width: 768px) 30vw, 20vw" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
                <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
                    <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.2em] opacity-70 text-white line-clamp-1">{category}</span>
                    <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight line-clamp-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
                </div>
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
            </div>
        </motion.div>
    </motion.div>
));
AuthFloatingProduct.displayName = 'AuthFloatingProduct';

// ============================================================================
// --- 3. FLOATING UI COMPONENTS (Directly on Background) ---
// ============================================================================
const PremiumInput = memo(({ icon: Icon, placeholder, ...props }: { icon: any, placeholder: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative group w-full transform-gpu">
        <div className="absolute left-5 top-1/2 -translate-y-1/2 text-cyan-500/70 group-focus-within:text-cyan-400 transition-colors duration-300 z-10">
            <Icon size={20} />
        </div>
        <input
            {...props}
            placeholder={placeholder}
            suppressHydrationWarning={true}
            className="w-full bg-zinc-900/80 border border-white/10 rounded-full py-4 pl-14 pr-6 text-white placeholder-gray-400 focus:border-cyan-500/50 focus:bg-zinc-900 backdrop-blur-2xl transition-all duration-500 text-sm md:text-base shadow-[0_0_30px_rgba(0,0,0,0.5)] focus:shadow-[0_0_40px_rgba(6,182,212,0.2)] outline-none"
        />
    </div>
));
PremiumInput.displayName = 'PremiumInput';

const SubmitButton = memo(({ children, isLoading }: { children: React.ReactNode, isLoading: boolean }) => (
    <motion.button 
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" disabled={isLoading}
        className="relative flex items-center justify-center w-full overflow-hidden rounded-full py-4 px-6 text-sm md:text-base font-bold text-black bg-white hover:bg-cyan-50 hover:text-cyan-900 transition-colors duration-500 shadow-[0_0_30px_rgba(255,255,255,0.15)] group transform-gpu"
    >
        {isLoading ? (
            <span className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce delay-100" />
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce delay-200" />
            </span>
        ) : children}
    </motion.button>
));
SubmitButton.displayName = 'SubmitButton';

// ============================================================================
// --- 4. FORMS (Login / Register - Floating Structure) ---
// ============================================================================
const SignUpForm = memo(({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true); setError('');
        try {
            const result = await signIn('credentials', { redirect: false, email, password });
            if (result?.error) setError('Registration failed. Please check your details.');
            else if (result?.ok) { router.refresh(); router.push('/'); }
        } catch (err) { setError('An error occurred. Please try again later.'); } 
        finally { setIsLoading(false); }
    };

    return (
         <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.8, ease: premiumEasing }} className="w-full space-y-10">
            <div className="text-center space-y-4">
                <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tighter text-white drop-shadow-2xl leading-[1.1]">
                    Create an <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-zinc-400">
                        account
                    </span>
                </h2>
                <p className="text-sm sm:text-lg text-zinc-300 font-light drop-shadow-md max-w-sm mx-auto">
                    Join airdeliver to experience the future of shopping.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 max-w-sm mx-auto w-full relative z-30">
                <PremiumInput icon={User} name="fullName" type="text" placeholder="Full Name" required disabled={isLoading} value={fullName} onChange={(e) => setFullName(e.target.value)} />
                <PremiumInput icon={Mail} name="email" type="email" placeholder="Email Address" required disabled={isLoading} value={email} onChange={(e) => setEmail(e.target.value)} />
                <PremiumInput icon={Lock} name="password" type="password" placeholder="Password" required disabled={isLoading} value={password} onChange={(e) => setPassword(e.target.value)} />
                
                {error && <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-full border border-red-500/20 text-center backdrop-blur-md">{error}</p>}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>Sign Up <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" /></SubmitButton>
                </div>
            </form>

            <div className="text-center pt-4 relative z-30">
                <p className="text-gray-400 text-sm font-light drop-shadow-md">
                    Already have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-300 font-medium transition-colors duration-300 underline underline-offset-4">Sign in</button>
                </p>
            </div>
        </motion.div>
    );
});
SignUpForm.displayName = 'SignUpForm';

const SignInForm = memo(({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true); setError('');
        try {
            const result = await signIn('credentials', { redirect: false, email, password });
            if (result?.error) setError('Invalid email or password.');
            else if (result?.ok) { router.refresh(); router.push('/'); }
        } catch (err) { setError('An error occurred. Please try again later.'); } 
        finally { setIsLoading(false); }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.8, ease: premiumEasing }} className="w-full space-y-10">
            <div className="text-center space-y-4">
                <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tighter text-white drop-shadow-2xl leading-[1.1]">
                    Welcome <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-zinc-400">
                        back
                    </span>
                </h2>
                <p className="text-sm sm:text-lg text-zinc-300 font-light drop-shadow-md max-w-sm mx-auto">
                    Sign in to manage your deliveries and track your orders.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 max-w-sm mx-auto w-full relative z-30">
                <PremiumInput icon={Mail} name="email" type="email" placeholder="Email Address" required disabled={isLoading} value={email} onChange={(e) => setEmail(e.target.value)} />
                <div className="space-y-2">
                    <PremiumInput icon={Lock} name="password" type="password" placeholder="Password" required disabled={isLoading} value={password} onChange={(e) => setPassword(e.target.value)} />
                    <div className="flex justify-end px-2">
                        <button type="button" className="text-xs text-gray-400 hover:text-white transition-colors drop-shadow-md">Forgot password?</button>
                    </div>
                </div>
                
                {error && <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-full border border-red-500/20 text-center backdrop-blur-md">{error}</p>}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>Sign In</SubmitButton>
                </div>
            </form>

            <div className="text-center pt-4 relative z-30">
                <p className="text-gray-400 text-sm font-light drop-shadow-md">
                    Don't have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-300 font-medium transition-colors duration-300 underline underline-offset-4">Create an account</button>
                </p>
            </div>
        </motion.div>
    );
});
SignInForm.displayName = 'SignInForm';

// ============================================================================
// --- 5. PAGE ORCHESTRATOR ---
// ============================================================================
export default function AuthPage() {
    const [variant, setVariant] = useState<'SIGNIN' | 'SIGNUP'>('SIGNIN');
    const [isClient, setIsClient] = useState(false);

    useEffect(() => {
        setIsClient(true);
        const params = new URLSearchParams(window.location.search);
        const mode = params.get('mode');
        if (mode === 'SIGNUP' || mode === 'SIGNIN') setVariant(mode);
    }, []);

    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    // Identical Product Cards to the Hero Section
    const HERO_CARDS = [
      { title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[1%] left-[6%] lg:top-[10%] lg:left-[5%]", sizeClasses: "w-20 h-28 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/20 text-cyan-400" },
      { title: "PS5", category: "Wearables", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[1%] right-[6%] lg:top-[10%] lg:right-[5%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/20 text-purple-400" },
      { title: "Dyson", category: "Aesthetic", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -left-[4%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/20 text-pink-400" },
      { title: "Headphones", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -right-[3%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/20 text-amber-400" },
      { title: "Leather Handbag", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] left-[2%] lg:bottom-[25%] lg:left-[8%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/20 text-emerald-400" },
      { title: "Iphone 17 pro max", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] right-[1%] lg:bottom-[25%] lg:right-[8%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/20 text-blue-400" },
      { title: "Nike Air Max", category: "Fashion", delay: 0.7, rotation: -5, image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] left-[20%] lg:bottom-[5%] lg:left-[25%]", sizeClasses: "w-20 h-28 lg:w-48 lg:h-48", colorCls: "hover:shadow-red-500/20 text-red-400" },
      { title: "Galaxy Buds", category: "Neural Tech", delay: 0.8, rotation: 7, image: "https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] right-[20%] lg:bottom-[5%] lg:right-[25%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-cyan-500/20 text-cyan-400" }
    ];

    if (!isClient) return <div className="min-h-screen bg-black" />;

    return (
        <section className="relative min-h-[100svh] w-full bg-[#050505] overflow-hidden flex items-center pt-20 pb-10 lg:pt-0 lg:pb-0 font-sans">
            
            {/* 3D Background Canvas with WHITE Stars */}
            <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }}>
                <Suspense fallback={null}>
                    <Canvas {...heroCanvasConfig}>
                        <ParticleField count={20000} radius={66} color="#ffffff" size={0.065} rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.001 }} />
                        <Preload all />
                    </Canvas>
                </Suspense>
            </div>
            
            <div className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10 h-full">
                <div className="w-full flex flex-col items-center justify-center min-h-[85vh] lg:min-h-[100svh] relative">
                    
                    {/* Floating Central Content (No Background Container) */}
                    <div className="flex flex-col items-center justify-center w-full relative z-30 pointer-events-auto">
                        <Suspense fallback={<div className="h-[400px] flex items-center justify-center"><div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" /></div>}>
                            <AnimatePresence mode="wait">
                                {variant === 'SIGNIN' ? <SignInForm key="signin" onSwitch={toggleVariant} /> : <SignUpForm key="signup" onSwitch={toggleVariant} />}
                            </AnimatePresence>
                        </Suspense>
                    </div>

                    {/* Floating Product Cards (Absolute) */}
                    <div className="absolute inset-0 pointer-events-none z-20 flex items-center justify-center perspective-1000">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9, rotateY: 10 }} animate={{ opacity: 1, scale: 1, rotateY: 0 }} transition={{ duration: 1.2, ease: premiumEasing, delay: 0.2 }}
                            className="relative w-full h-full flex items-center justify-center"
                        >
                            {HERO_CARDS.map((card, idx) => (
                                <AuthFloatingProduct key={idx} {...card} />
                            ))}
                        </motion.div>
                    </div>

                </div>
            </div>
        </section>
    );
}
