'use client';

import CinematicBackground from '@/components/ui/CinematicBackground';
import React, { useState, Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import { AtSign, Lock, User, ArrowRight, Zap, Globe, ShieldCheck, Gem } from 'lucide-react';
import * as THREE from 'three';

const DiamondDust = () => {
    const particlesRef = React.useRef<THREE.Points>(null!);
    
    useFrame(({ clock, mouse }) => {
        if (particlesRef.current) {
            particlesRef.current.rotation.y = clock.getElapsedTime() * 0.02;
            particlesRef.current.rotation.x = -mouse.y * 0.02;
            particlesRef.current.rotation.z = mouse.x * 0.02;
        }
    });

    const numParticles = 8000; 
    const positions = new Float32Array(numParticles * 3);
    
    for (let i = 0; i < numParticles; i++) {
        const theta = 2 * Math.PI * Math.random();
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 10 + Math.random() * 10; 

        positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);
    }

    return (
        <points ref={particlesRef}>
            <bufferGeometry attach="geometry">
                <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
            </bufferGeometry>
            <pointsMaterial 
                attach="material" 
                size={0.03} 
                color="#b3e5fc" 
                transparent 
                opacity={0.6} 
                sizeAttenuation={true} 
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
};

const FuturisticInput = ({ icon, ...props }: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative group">
        <div className="absolute left-5 top-1/2 -translate-y-1/2 text-cyan-500/50 group-focus-within:text-cyan-400 transition-colors duration-500">
            {icon}
        </div>
        <input
            {...props}
            suppressHydrationWarning={true}
            className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-5 pl-14 pr-6 text-white placeholder-gray-500 focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-500/30 focus:bg-black/40 focus:outline-none transition-all duration-500 font-medium tracking-wide backdrop-blur-sm"
        />
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent opacity-0 group-focus-within:opacity-100 transition-opacity duration-700 pointer-events-none" />
    </div>
);

const ActionButton = ({ children, isLoading, onClick }: { children: React.ReactNode, isLoading: boolean, onClick?: () => void }) => (
    <motion.button 
        whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(6, 182, 212, 0.4)" }} 
        whileTap={{ scale: 0.98 }} 
        onClick={onClick}
        type="submit" 
        disabled={isLoading}
        className="relative w-full overflow-hidden rounded-2xl py-5 text-lg font-black text-white tracking-[0.15em] group border border-cyan-500/30"
        style={{ 
            background: 'linear-gradient(135deg, rgba(6,182,212,0.8) 0%, rgba(59,130,246,0.8) 100%)',
            fontFamily: "'Orbitron', sans-serif"
        }}
    >
        <div className="absolute inset-0 opacity-20 mix-blend-overlay" style={{ backgroundImage: "radial-gradient(transparent 1px, #fff 1px)", backgroundSize: "4px 4px", backdropFilter: "contrast(1.5)" }} />
        <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent opacity-50" />
        
        <span className="relative z-10 flex items-center justify-center gap-3 drop-shadow-md">
            {isLoading ? (
                <span className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-white rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-white rounded-full animate-bounce delay-100" />
                    <span className="w-2 h-2 bg-white rounded-full animate-bounce delay-200" />
                </span>
            ) : children}
        </span>
        
        <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/40 to-transparent skew-x-12" />
    </motion.button>
);

const TrustBadge = ({ icon, text }: { icon: React.ReactNode, text: string }) => (
    <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-black/40 px-4 py-1.5 rounded-full border border-white/5 shadow-inner">
        <span className="text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">{icon}</span>
        {text}
    </div>
);

const SignUpForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            const result = await signIn('credentials', {
                redirect: false,
                email,
                password,
            });

            if (result?.error) {
                setError('Invalid credentials. Access Denied.');
                setIsLoading(false);
            } else if (result?.ok) {
                router.refresh();
                router.push('/');
            }
        } catch (err) {
            setError('System Error. Please try again.');
            setIsLoading(false);
        }
    };

    return (
         <motion.div 
            initial={{ opacity: 0, x: 50, filter: "blur(10px)" }} 
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }} 
            exit={{ opacity: 0, x: -50, filter: "blur(10px)" }} 
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-8"
        >
            <div className="text-center space-y-3 mb-10">
                <h2 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-400 drop-shadow-2xl" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    SECURE & FAST
                </h2>
                <p className="text-sm text-cyan-300/60 tracking-[0.2em] uppercase font-medium">
                    Join the Autonomous Logistics Revolution
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid grid-cols-1 gap-5">
                    <FuturisticInput 
                        icon={<User size={20} />} 
                        name="fullName" 
                        type="text" 
                        placeholder="Enter Your Name" 
                        required 
                        disabled={isLoading}
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                    />
                    <FuturisticInput 
                        icon={<AtSign size={20} />} 
                        name="email" 
                        type="email" 
                        placeholder="Enter Your Email" 
                        required 
                        disabled={isLoading}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <FuturisticInput 
                        icon={<Lock size={20} />} 
                        name="password" 
                        type="password" 
                        placeholder="Enter Your Password" 
                        required 
                        disabled={isLoading}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                </div>
                 {error && <p className="text-xs text-red-400 text-center bg-red-500/10 p-2 rounded-lg border border-red-500/20">{error}</p>}

                <div className="pt-4">
                    <ActionButton isLoading={isLoading}>
                        Sign Up <ArrowRight size={20} />
                    </ActionButton>
                </div>
            </form>

            <div className="text-center pt-6">
                <p className="text-gray-500 text-sm">
                    Already have account?{' '}
                    <button onClick={onSwitch} className="text-cyan-400 hover:text-white font-bold transition-all duration-300 underline decoration-cyan-500/30 underline-offset-8 hover:decoration-cyan-400">
                        Sign In 
                    </button>
                </p>
            </div>
        </motion.div>
    );
};

const SignInForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            const result = await signIn('credentials', {
                redirect: false,
                email,
                password,
            });

            if (result?.error) {
                setError('Invalid credentials. Access Denied.');
                setIsLoading(false);
            } else if (result?.ok) {
                router.refresh();
                router.push('/');
            }
        } catch (err) {
            setError('System Error. Please try again.');
            setIsLoading(false);
        }
    };

    return (
        <motion.div 
            initial={{ opacity: 0, x: -50, filter: "blur(10px)" }} 
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }} 
            exit={{ opacity: 0, x: 50, filter: "blur(10px)" }} 
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-8"
        >
            <div className="text-center space-y-3 mb-10">
                <h2 className="text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-400 drop-shadow-2xl" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    LET'S GET STARTED
                </h2>
                <p className="text-sm text-cyan-300/60 tracking-[0.2em] font-medium">
                    Login in to manage your deliveries without the headache
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                <FuturisticInput 
                    icon={<AtSign size={20} />} 
                    name="email" 
                    type="email" 
                    placeholder="ID / Email" 
                    required 
                    disabled={isLoading}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <FuturisticInput 
                    icon={<Lock size={20} />} 
                    name="password" 
                    type="password" 
                    placeholder="Enter Your Password" 
                    required 
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />
                
                {error && <p className="text-xs text-red-400 text-center bg-red-500/10 p-2 rounded-lg border border-red-500/20">{error}</p>}
                
                <div className="flex justify-end">
                    <button type="button" className="text-xs text-gray-500 hover:text-cyan-400 transition-colors duration-300 font-medium">
                        Forgot Your Password?
                    </button>
                </div>

                <div className="pt-4">
                    <ActionButton isLoading={isLoading}>
                        SIGN IN  <Zap size={20} className="fill-current ml-2" />
                    </ActionButton>
                </div>
            </form>

            <div className="text-center pt-6">
                <p className="text-gray-500 text-sm">
                    Create a new account?{' '}
                    <button onClick={onSwitch} className="text-cyan-400 hover:text-white font-bold transition-all duration-300 underline decoration-cyan-500/30 underline-offset-8 hover:decoration-cyan-400">
                        SIGN UP
                    </button>
                </p>
            </div>
        </motion.div>
    );
};

export default function AuthPage() {
    const [variant, setVariant] = useState<'SIGNIN' | 'SIGNUP'>('SIGNIN');
    const [isClient, setIsClient] = useState(false);

    useEffect(() => {
        setIsClient(true);
        const params = new URLSearchParams(window.location.search);
        const mode = params.get('mode');
        
        if (mode === 'SIGNUP' || mode === 'SIGNIN') {
            setVariant(mode);
        }
    }, []);

    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    return (
        <>
            <style dangerouslySetInnerHTML={{ __html: `
                html, body {
                    background-color: #050505 !important;
                }
            ` }} />
            <main className="relative min-h-screen w-full bg-[#050505] text-gray-100 flex items-center justify-center pt-24 overflow-hidden selection:bg-cyan-500/30">
                <div className="absolute inset-0 z-0">
                    {isClient && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 1 }}
                            className="absolute inset-0"
                        >
                            <CinematicBackground />
                            <Canvas camera={{ position: [0, 0, 20], fov: 40 }}> 
                                <Suspense fallback={null}>
                                    <color attach="background" args={['#000000']} />
                                    <Stars radius={150} depth={80} count={12000} factor={6} saturation={0} fade speed={0.5} />
                                    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.4}>
                                         <DiamondDust />
                                    </Float>
                                    <ambientLight intensity={0.2} />
                                    <pointLight position={[10, 10, 10]} intensity={1.5} color="#00C6FF" />
                                    <pointLight position={[-10, -10, -10]} intensity={0.5} color="#7F00FF" />
                                </Suspense>
                            </Canvas>
                        </motion.div>
                    )}
                    
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black pointer-events-none opacity-80" />
                    <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-black/50 pointer-events-none" />
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />
                </div>

                <div className="relative z-10 w-full max-w-[500px] px-6">
                    <motion.div 
                        initial={{ y: -80, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                        className="text-center mb-12 relative"
                    >
                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-[1px] h-12 bg-gradient-to-b from-transparent to-cyan-500/50" />
                        
                        <h1 className="text-5xl md:text-5xl font-medium text-white tracking-tighter leading-none drop-shadow-[0_0_40px_rgba(6,182,212,0.3)]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="bg-clip-text text-transparent bg-gradient-to-b from-white via-cyan-100 to-cyan-900">
                                Turning every interaction into a moment of delight.
                            </span>
                        </h1>
                        
                        <div className="flex items-center justify-center gap-4 mt-6">
                            <div className="h-[1px] w-12 bg-gradient-to-r from-transparent to-cyan-500/50" />
                            <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: "auto" }}
                                className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/30 border border-cyan-500/20 backdrop-blur-md"
                            >
                                <Gem size={10} className="text-cyan-400" />
                                <span className="text-[10px] font-mono text-cyan-300 uppercase tracking-[0.2em]">Frictionless</span>
                            </motion.div>
                            <div className="h-[1px] w-12 bg-gradient-to-l from-transparent to-cyan-500/50" />
                        </div>
                        
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.8 }}
                            className="text-xs text-gray-500 mt-4 uppercase tracking-[0.4em] font-light"
                        >
                            Delivering pure peace of mind
                        </motion.p>
                    </motion.div>

                    <motion.div
                        layout
                        initial={{ opacity: 0, scale: 0.9, y: 40 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        transition={{ duration: 0.8, type: "spring", stiffness: 80, damping: 25 }}
                        className="relative overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-black/40 backdrop-blur-3xl rounded-[40px] border border-white/10 shadow-2xl shadow-cyan-900/10" />
                        
                        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                        <div className="absolute bottom-0 right-0 w-64 h-64 bg-cyan-500/5 blur-[80px] rounded-full pointer-events-none" />
                        <div className="absolute top-0 left-0 w-64 h-64 bg-purple-500/5 blur-[80px] rounded-full pointer-events-none" />

                        <div className="relative p-10 md:p-12 z-10">
                            <Suspense fallback={
                                <div className="flex flex-col items-center justify-center min-h-[300px] text-cyan-400 font-mono text-xs tracking-widest animate-pulse gap-4">
                                    <Gem size={24} className="animate-spin duration-3000" />
                                    <span>INITIALIZING INTERFACE...</span>
                                </div>
                            }>
                                <AnimatePresence mode="wait">
                                    {variant === 'SIGNIN' ? (
                                        <SignInForm key="signin" onSwitch={toggleVariant} />
                                    ) : (
                                        <SignUpForm key="signup" onSwitch={toggleVariant} />
                                    )}
                                </AnimatePresence>
                            </Suspense>
                        </div>

                        <div className="relative bg-black/20 border-t border-white/5 p-5 flex justify-between items-center px-10 backdrop-blur-md">
                            <TrustBadge icon={<Globe size={12} />} text="Global Network" />
                            <TrustBadge icon={<ShieldCheck size={12} />} text="Quantum Secure" />
                        </div>
                    </motion.div>
                    
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1.5 }}
                        className="text-center mt-12 flex flex-col items-center gap-2"
                    >
                        <div className="w-1 h-8 bg-gradient-to-b from-cyan-500/20 to-transparent" />
                        <p className="text-gray-600 text-[10px] tracking-[0.2em] font-mono">
                            © 2026 airdeliver systems. operating globally.

                        </p>
                    </motion.div>
                </div>
            </main>
        </>
    );
}
