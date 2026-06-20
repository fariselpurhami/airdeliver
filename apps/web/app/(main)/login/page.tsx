//** apps/web/app/(main)/login/page.tsx **//

'use client';

import React, { useState, Suspense, useEffect, useMemo, memo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import { Mail, Lock, User, ArrowRight, ShieldCheck, Globe, Zap } from 'lucide-react';
import * as THREE from 'three';

// ============================================================================
// --- 1. PREMIUM BACKGROUND: SUBTLE MICRO-DUST ---
// ============================================================================

const PremiumDust = memo(() => {
    const particlesRef = React.useRef<THREE.Points>(null!);
    const count = 3000;

    const positions = useMemo(() => {
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i * 3] = (Math.random() - 0.5) * 20;
            pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
            pos[i * 3 + 2] = (Math.random() - 0.5) * 10;
        }
        return pos;
    }, []);

    useFrame(({ clock, pointer }) => {
        if (particlesRef.current) {
            // Very slow, elegant rotation
            particlesRef.current.rotation.y = clock.getElapsedTime() * 0.01;
            particlesRef.current.rotation.x = THREE.MathUtils.lerp(particlesRef.current.rotation.x, -pointer.y * 0.05, 0.05);
            particlesRef.current.rotation.z = THREE.MathUtils.lerp(particlesRef.current.rotation.z, pointer.x * 0.05, 0.05);
        }
    });

    return (
        <points ref={particlesRef}>
            <bufferGeometry attach="geometry">
                <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
            </bufferGeometry>
            <PointMaterial transparent color="#ffffff" size={0.015} sizeAttenuation={true} depthWrite={false} opacity={0.3} />
        </points>
    );
});
PremiumDust.displayName = 'PremiumDust';

const AuthBackground = memo(() => (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.5 }} className="absolute inset-0 z-0 pointer-events-none">
        {/* Subtle Aurora Gradients */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80vw] h-[50vh] bg-cyan-900/20 blur-[120px] rounded-full mix-blend-screen" />
        <div className="absolute bottom-0 left-0 w-[50vw] h-[50vh] bg-blue-900/10 blur-[120px] rounded-full mix-blend-screen" />
        
        <Canvas camera={{ position: [0, 0, 10], fov: 45 }} dpr={[1, 1.5]} gl={{ powerPreference: "high-performance", antialias: false, alpha: true }}>
            <Suspense fallback={null}>
                <PremiumDust />
            </Suspense>
        </Canvas>
    </motion.div>
));
AuthBackground.displayName = 'AuthBackground';

// ============================================================================
// --- 2. ENTERPRISE UI COMPONENTS ---
// ============================================================================

const PremiumInput = memo(({ icon: Icon, label, ...props }: { icon: any, label: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="space-y-1.5">
        <label className="text-xs font-medium text-gray-400 pl-1 tracking-wide">{label}</label>
        <div className="relative group w-full">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-cyan-400 transition-colors duration-300">
                <Icon size={18} />
            </div>
            <input
                {...props}
                suppressHydrationWarning={true}
                className="w-full bg-[#0A0A0A]/80 border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder-gray-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 focus:bg-black transition-all duration-300 text-sm shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)]"
            />
        </div>
    </div>
));
PremiumInput.displayName = 'PremiumInput';

const SubmitButton = memo(({ children, isLoading }: { children: React.ReactNode, isLoading: boolean }) => (
    <motion.button 
        whileHover={{ scale: 1.01 }} 
        whileTap={{ scale: 0.99 }} 
        type="submit" 
        disabled={isLoading}
        className="relative w-full overflow-hidden rounded-xl py-4 text-sm font-semibold text-white bg-white/10 hover:bg-white border border-white/10 hover:text-black transition-all duration-300 shadow-lg group"
    >
        <span className="relative z-10 flex items-center justify-center gap-2">
            {isLoading ? (
                <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" />
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce delay-100" />
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce delay-200" />
                </span>
            ) : children}
        </span>
    </motion.button>
));
SubmitButton.displayName = 'SubmitButton';

const ValueProp = memo(({ icon: Icon, title }: { icon: any, title: string }) => (
    <div className="flex items-center gap-2 text-xs text-gray-400">
        <Icon size={14} className="text-cyan-500" />
        <span>{title}</span>
    </div>
));
ValueProp.displayName = 'ValueProp';

// ============================================================================
// --- 3. FORMS (Login / Register) ---
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
         <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.4 }} className="space-y-8">
            <div className="space-y-2">
                <h2 className="text-3xl font-semibold text-white tracking-tight">Create an account</h2>
                <p className="text-sm text-gray-400 leading-relaxed">
                    Join airdeliver to experience the future of shopping.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                <PremiumInput icon={User} label="Full Name" name="fullName" type="text" placeholder="John Doe" required disabled={isLoading} value={fullName} onChange={(e) => setFullName(e.target.value)} />
                <PremiumInput icon={Mail} label="Email Address" name="email" type="email" placeholder="john@example.com" required disabled={isLoading} value={email} onChange={(e) => setEmail(e.target.value)} />
                <PremiumInput icon={Lock} label="Password" name="password" type="password" placeholder="••••••••" required disabled={isLoading} value={password} onChange={(e) => setPassword(e.target.value)} />
                
                {error && <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">{error}</p>}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>
                        Create Account <ArrowRight size={16} />
                    </SubmitButton>
                </div>
            </form>

            <div className="text-center pt-2">
                <p className="text-gray-400 text-sm">
                    Already have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-400 font-medium transition-colors duration-300">
                        Sign in
                    </button>
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
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.4 }} className="space-y-8">
            <div className="space-y-2">
                <h2 className="text-3xl font-semibold text-white tracking-tight">Welcome back</h2>
                <p className="text-sm text-gray-400 leading-relaxed">
                    Sign in to manage your deliveries and track your orders.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                <PremiumInput icon={Mail} label="Email Address" name="email" type="email" placeholder="name@company.com" required disabled={isLoading} value={email} onChange={(e) => setEmail(e.target.value)} />
                <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                        <label className="text-xs font-medium text-gray-400 pl-1 tracking-wide">Password</label>
                        <button type="button" className="text-xs text-gray-500 hover:text-white transition-colors">Forgot password?</button>
                    </div>
                    <div className="relative group w-full">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-cyan-400 transition-colors duration-300">
                            <Lock size={18} />
                        </div>
                        <input
                            type="password" name="password" placeholder="••••••••" required disabled={isLoading} value={password} onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-[#0A0A0A]/80 border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder-gray-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 focus:bg-black transition-all duration-300 text-sm shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)]"
                        />
                    </div>
                </div>
                
                {error && <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">{error}</p>}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>
                        Sign In
                    </SubmitButton>
                </div>
            </form>

            <div className="text-center pt-2">
                <p className="text-gray-400 text-sm">
                    Don't have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-400 font-medium transition-colors duration-300">
                        Create an account
                    </button>
                </p>
            </div>
        </motion.div>
    );
});
SignInForm.displayName = 'SignInForm';

// ============================================================================
// --- 4. PAGE ORCHESTRATOR ---
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

    return (
        <main className="relative min-h-screen w-full bg-[#050505] text-gray-100 flex items-center justify-center pt-20 pb-10 overflow-hidden selection:bg-cyan-500/30 font-sans">
            {isClient && <AuthBackground />}
            
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.02] pointer-events-none z-0" />

            <div className="relative z-10 w-full max-w-md px-6">
                
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                >
                    {/* Premium Glass Panel */}
                    <div className="relative bg-[#0D0D0C]/60 backdrop-blur-2xl rounded-3xl border border-white/10 shadow-[0_30px_60px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] p-8 md:p-10 overflow-hidden">
                        
                        {/* Subtle top edge highlight */}
                        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                        
                        <Suspense fallback={<div className="h-[400px] flex items-center justify-center"><div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" /></div>}>
                            <AnimatePresence mode="wait">
                                {variant === 'SIGNIN' ? <SignInForm key="signin" onSwitch={toggleVariant} /> : <SignUpForm key="signup" onSwitch={toggleVariant} />}
                            </AnimatePresence>
                        </Suspense>

                    </div>

                    {/* Trust Signals Footer */}
                    <div className="mt-8 flex flex-wrap items-center justify-center gap-6">
                        <ValueProp icon={ShieldCheck} title="End-to-end encrypted" />
                        <ValueProp icon={Zap} title="Instant autonomous delivery" />
                        <ValueProp icon={Globe} title="Global logistics network" />
                    </div>

                </motion.div>
            </div>
        </main>
    );
}
