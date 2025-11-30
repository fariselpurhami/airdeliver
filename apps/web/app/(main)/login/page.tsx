//** apps/web/app/(main)/login/page.tsx **//

'use client';

import React, { useState, Suspense, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import { AtSign, Lock, User, ArrowRight, Zap, Globe, ShieldCheck } from 'lucide-react';
import * as THREE from 'three';

// ============================================================================
// --- 1. ARCHITECTURAL COMPONENTS (Building Blocks) ---
// ============================================================================

const NeuralNetwork = () => {
    const particlesRef = React.useRef<THREE.Points>(null!);
    
    useFrame(({ clock, mouse }) => {
        if (particlesRef.current) {
          
            particlesRef.current.rotation.y = clock.getElapsedTime() * 0.05;
            particlesRef.current.rotation.x = -mouse.y * 0.05;
            particlesRef.current.rotation.y += mouse.x * 0.05;
        }
    });

    const numParticles = 20000; 
    const positions = new Float32Array(numParticles * 3);
    
    for (let i = 0; i < numParticles; i++) {
   
        const theta = 2 * Math.PI * Math.random();
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 12 + Math.random() * 4; 

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
                size={0.025} 
                color="#00C6FF" 
                transparent 
                opacity={0.8} 
                sizeAttenuation={true} 
            />
        </points>
    );
};

const FuturisticInput = ({ icon, ...props }: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan-500/50 group-focus-within:text-cyan-400 transition-colors duration-300">
            {icon}
        </div>
        <input
            {...props}
            className="w-full bg-black/40 border border-white/10 rounded-full py-4 pl-12 pr-6 text-white placeholder-gray-600 
                       focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-500/20 focus:outline-none 
                       transition-all duration-300 hover:border-white/20 hover:bg-black/60"
        />
        <div className="absolute inset-0 rounded-full bg-cyan-400/5 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 pointer-events-none" />
    </div>
);

const ActionButton = ({ children, isLoading, onClick }: { children: React.ReactNode, isLoading: boolean, onClick?: () => void }) => (
    <motion.button 
        whileHover={{ scale: 1.02, boxShadow: "0 0 20px rgba(0, 198, 255, 0.4)" }} 
        whileTap={{ scale: 0.98 }} 
        onClick={onClick}
        type="submit" 
        disabled={isLoading}
        className="relative w-full overflow-hidden rounded-full py-4 text-base font-bold text-black uppercase tracking-wider group"
        style={{ 
            background: 'linear-gradient(90deg, #00C6FF 0%, #0072FF 100%)',
            fontFamily: "'Orbitron', sans-serif"
        }}
    >
        <span className="relative z-10 flex items-center justify-center gap-2">
            {isLoading ? (
                <span className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-black rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-black rounded-full animate-bounce delay-100" />
                    <span className="w-2 h-2 bg-black rounded-full animate-bounce delay-200" />
                </span>
            ) : children}
        </span>
        <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/30 to-transparent" />
    </motion.button>
);

const TrustBadge = ({ icon, text }: { icon: React.ReactNode, text: string }) => (
    <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase tracking-widest bg-white/5 px-3 py-1 rounded-full border border-white/5">
        <span className="text-cyan-500">{icon}</span>
        {text}
    </div>
);

// ============================================================================
// --- 2. FORMS (Logic & Layout) ---
// ============================================================================

const SignUpForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [fullName, setFullName] = useState('');
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
                window.location.href = '/'; 
            }
        } catch (err) {
            setError('System Error. Please try again.');
            setIsLoading(false);
        }
    };

    return (
         <motion.div 
            initial={{ opacity: 0, x: 20 }} 
            animate={{ opacity: 1, x: 0 }} 
            exit={{ opacity: 0, x: -20 }} 
            transition={{ duration: 0.4 }}
            className="space-y-6"
        >
            <div className="text-center space-y-2 mb-8">
             
                <h2 className="text-3xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    SECURE & FAST
                </h2>
                <p className="text-sm text-cyan-400/80 tracking-wide uppercase font-medium">
                    Join the Autonomous Logistics Revolution
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                    <FuturisticInput 
                        icon={<User size={18} />} 
                        name="fullName" 
                        type="text" 
                        placeholder="Enter Your Name" 
                        required 
                        disabled={isLoading}
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                    />
                    <FuturisticInput 
                        icon={<AtSign size={18} />} 
                        name="email" 
                        type="email" 
                        placeholder="Enter Your Email" 
                        required 
                        disabled={isLoading}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <FuturisticInput 
                        icon={<Lock size={18} />} 
                        name="password" 
                        type="password" 
                        placeholder="Enter Your Password" 
                        required 
                        disabled={isLoading}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                </div>
                 {error && <p className="text-xs text-red-400 text-center">{error}</p>}

                <div className="pt-2">
                    <ActionButton isLoading={isLoading}>
                        SIGN UP <ArrowRight size={18} />
                    </ActionButton>
                </div>
            </form>

            <div className="text-/center pt-4">
                <p className="text-gray-500 text-sm">
                    Already have account?{' '}
                    <button onClick={onSwitch} className="text-white hover:text-cyan-400 font-bold transition-colors underline decoration-cyan-500/50 underline-offset-4">
                        Sign In 
                    </button>
                </p>
            </div>
        </motion.div>
    );
};

const SignInForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
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
             
                router.push('/profile');
                router.refresh();
            }
        } catch (err) {
            setError('System Error. Please try again.');
            setIsLoading(false);
        }
    };

    return (
        <motion.div 
            initial={{ opacity: 0, x: -20 }} 
            animate={{ opacity: 1, x: 0 }} 
            exit={{ opacity: 0, x: 20 }} 
            transition={{ duration: 0.4 }}
            className="space-y-6"
        >
            <div className="text-center space-y-2 mb-8">
                <h2 className="text-3xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Access Network
                </h2>
                <p className="text-sm text-cyan-400/80 tracking-wide uppercase font-medium">
                    Secure Command Center Login
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <FuturisticInput 
                    icon={<AtSign size={18} />} 
                    name="email" 
                    type="email" 
                    placeholder="ID / Email" 
                    required 
                    disabled={isLoading}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <FuturisticInput 
                    icon={<Lock size={18} />} 
                    name="password" 
                    type="password" 
                    placeholder="Enter Your Password" 
                    required 
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />
                
                {error && <p className="text-xs text-red-400 text-center">{error}</p>}
                
                <div className="flex justify-end">
                    <button type="button" className="text-xs text-gray-500 hover:text-cyan-400 transition-colors">
                        Forgot Your Password?
                    </button>
                </div>

                <div className="pt-2">
                    <ActionButton isLoading={isLoading}>
                        SIGN IN  <Zap size={18} className="fill-current" />
                    </ActionButton>
                </div>
            </form>

            <div className="text-center pt-4">
                <p className="text-gray-500 text-sm">
                    Create a new account?{' '}
                    <button onClick={onSwitch} className="text-white hover:text-cyan-400 font-bold transition-colors underline decoration-cyan-500/50 underline-offset-4">
                        Sign Up
                    </button>
                </p>
            </div>
        </motion.div>
    );
};

// ============================================================================
// --- 3. MAIN AUTH PAGE (The Global Gateway) ---
// ============================================================================

export default function AuthPage() {
    const [variant, setVariant] = useState<'SIGNIN' | 'SIGNUP'>('SIGNIN');
    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    return (
        <main className="relative min-h-screen w-full bg-black text-gray-100 flex items-center justify-center overflow-hidden selection:bg-cyan-500/30">
            
            <div className="absolute inset-0 z-0 bg-black">
                <Canvas camera={{ position: [0, 0, 18], fov: 35 }}> 
                    <Suspense fallback={null}>
                        <color attach="background" args={['#000000']} />
                        <Stars  radius={300} depth={60} count={25000} factor={10} saturation={0.5} fade speed={0.8} />
                        <Float speed={2} rotationIntensity={0.6} floatIntensity={0.8}>
                             <NeuralNetwork />
                        </Float>
                        <ambientLight intensity={0.4} />
                        <pointLight position={[10, 10, 10]} intensity={0.5} color="#00C6FF" />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/90 pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/40 pointer-events-none" />
            </div>

            <div className="relative z-10 w-full max-w-md px-4">
                
                <motion.div 
                    initial={{ y: -60, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                    className="text-center mb-10"
                >
                    <span className="text-5xl font-bold text-white tracking-tighter lowercase drop-shadow-[0_0_15px_rgba(0,198,255,0.5)]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Welcome to airdeliver. 
                    </span>
                    <motion.div 
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 96, opacity: 1 }}
                        transition={{ delay: 0.5, duration: 0.8 }}
                        className="h-0.5 bg-gradient-to-r from-transparent via-cyan-500 to-transparent mx-auto mt-3" 
                    />
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                        className="text-xs text-cyan-300/70 mt-2 uppercase tracking-[0.3em]"
                    >
                        Beyond Logistics
                    </motion.p>
                </motion.div>

                <motion.div
                    layout
                    initial={{ opacity: 0, scale: 0.95, y: 30 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.8, type: "spring", stiffness: 90, damping: 20 }}
                 
                    className="relative overflow-hidden bg-black/30 backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-2xl shadow-cyan-900/10"
                >
                   
                    <div className="absolute inset-0 rounded-[40px] border border-cyan-500/10 pointer-events-none" />
                    
                    <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" />
                    
                    <div className="p-8 md:p-10 relative z-10">
                        <AnimatePresence mode="wait">
                            {variant === 'SIGNIN' ? (
                                <SignInForm key="signin" onSwitch={toggleVariant} />
                            ) : (
                                <SignUpForm key="signup" onSwitch={toggleVariant} />
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="bg-white/5 border-t border-white/5 p-4 flex justify-between items-center px-8 backdrop-blur-sm">
                        <TrustBadge icon={<Globe size={12} />} text="Global Network" />
                        <TrustBadge icon={<ShieldCheck size={12} />} text="Quantum Secure" />
                    </div>
                </motion.div>
                
                <motion.p 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 }}
                    className="text-center text-gray-600 text-[10px] mt-8 tracking-widest"
                >
                    &copy; 2025 airdeliver systems. Operating globally.
                </motion.p>
            </div>
        </main>
    );
}

