'use client';

import React, { useState, Suspense, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { AtSign, Lock, User, ChevronsRight } from 'lucide-react';
import * as THREE from 'three';

const SignUpForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setIsLoading(true);

        try {
            
            const response = await fetch('/api/v1/users', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: fullName, email, password }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to create account.');
            }
            
            setSuccess('Account created! Switching to Sign In...');
            setTimeout(() => {
                onSwitch();
            }, 2000);

        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
         <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
            <div className="text-center mb-8">
                <h1 className="text-4xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Join the AI Revolution</h1>
                <p className="text-gray-400 mt-2">Seamless access. Infinite intelligence.</p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
                <FuturisticInput icon={<User size={18} />} value={fullName} onChange={(e) => setFullName(e.target.value)} name="fullName" type="text" placeholder="Full Name" required disabled={isLoading} />
                <FuturisticInput icon={<AtSign size={18} />} value={email} onChange={(e) => setEmail(e.target.value)} name="email" type="email" placeholder="Email Address" required disabled={isLoading} />
                <FuturisticInput icon={<Lock size={18} />} value={password} onChange={(e) => setPassword(e.target.value)} name="password" type="password" placeholder="Password" required disabled={isLoading} />
                {error && <p className="text-sm text-red-400 text-center">{error}</p>}
                {success && <p className="text-sm text-green-400 text-center">{success}</p>}
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" className="w-full glowing-button rounded-full py-3 text-lg font-bold mt-4" disabled={isLoading}>
                    {isLoading ? 'Creating Account...' : <>Activate My AI Experience <ChevronsRight className="inline ml-2" size={20} /></>}
                </motion.button>
            </form>
            <div className="text-center text-sm text-gray-500 mt-6">
                <button onClick={onSwitch} className="hover:text-cyan-400 transition-colors">Already have an account? Sign In</button>
            </div>
        </motion.div>
    );
};

const AIBackground = () => {
    const particlesRef = useRef<THREE.Points>(null!);
    useFrame(({ mouse }) => {
        if (particlesRef.current) {
            particlesRef.current.rotation.y = THREE.MathUtils.lerp(particlesRef.current.rotation.y, mouse.x * 0.2, 0.05);
            particlesRef.current.rotation.x = THREE.MathUtils.lerp(particlesRef.current.rotation.x, mouse.y * 0.2, 0.05);
        }
    });
    const numParticles = 5000;
    const positions = new Float32Array(numParticles * 3);
    for (let i = 0; i < numParticles; i++) {
        positions[i * 3 + 0] = (Math.random() - 0.5) * 10;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
    }
    return (
        <points ref={particlesRef}>
            <bufferGeometry attach="geometry">
                <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
            </bufferGeometry>
            <pointsMaterial attach="material" size={0.005} color="#00c6ff" transparent opacity={0.7} />
        </points>
    );
};

const FuturisticInput = ({ icon, ...props }: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
            {icon}
        </div>
        <input
            {...props}
            className="w-full bg-white/5 border border-white/10 rounded-lg py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none transition-all"
        />
    </div>
);

const SignInForm = ({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            const result = await signIn('credentials', {
                redirect: false,
                email,
                password,
            });

            if (result?.error) {
                setError('Invalid credentials. Please try again.');
            } else if (result?.ok) {
                router.push('/profile');
            }
        } catch (err) {
            setError('An unexpected error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
            <div className="text-center mb-8">
                <h1 className="text-4xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Access Granted</h1>
                <p className="text-gray-400 mt-2">Your identity in the new era of AI commerce.</p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-6">
                <FuturisticInput icon={<AtSign size={18} />} value={email} onChange={(e) => setEmail(e.target.value)} name="email" type="email" placeholder="Email Address" required disabled={isLoading} />
                <FuturisticInput icon={<Lock size={18} />} value={password} onChange={(e) => setPassword(e.target.value)} name="password" type="password" placeholder="Password" required disabled={isLoading} />
                {error && <p className="text-sm text-red-400 text-center">{error}</p>}
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" className="w-full glowing-button rounded-full py-3 text-lg font-bold" disabled={isLoading}>
                    {isLoading ? 'Authenticating...' : 'Sign In to the Future'}
                </motion.button>
            </form>
            <div className="text-center text-sm text-gray-500 mt-6">
                <button onClick={onSwitch} className="hover:text-cyan-400 transition-colors">Create AI Account</button>
            </div>
        </motion.div>
    );
};

export default function AuthPage() {
    const [variant, setVariant] = useState<'SIGNIN' | 'SIGNUP'>('SIGNIN');
    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    return (
        <main className="relative min-h-screen w-full bg-black text-gray-100 flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 z-0 opacity-40">
                <Canvas camera={{ position: [0, 0, 5], fov: 75 }}>
                    <Suspense fallback={null}>
                        <AIBackground />
                        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={0.5} />
                    </Suspense>
                </Canvas>
            </div>
            
             <motion.div 
                initial={{ y: '-100%', height: '5px' }}
                animate={{ y: '200vh' }}
                transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                className="absolute top-0 left-0 right-0 z-20 bg-cyan-400/50 blur-2xl"
             />

            <div className="relative z-10 container mx-auto grid grid-cols-1 md:grid-cols-2 items-center gap-16 px-4">
                <div className="hidden md:block text-left">
                    <motion.h1 
                        initial={{ opacity: 0, x: -50 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 1, ease: 'easeOut' }}
                        className="text-6xl font-black text-white leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}
                    >
                        THE FUTURE RECOGNIZES YOU.
                    </motion.h1>
                     <motion.p 
                        initial={{ opacity: 0, x: -50 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
                        className="mt-4 text-lg text-gray-400 max-w-md"
                    >
                        Secure by Intelligence. Powered by You. Your identity in the new era of AI commerce.
                    </motion.p>
                </div>

                <motion.div
                    initial={{ opacity: 0, y: 50, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                    className="relative w-full max-w-md p-8 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50"
                >
                    <AnimatePresence mode="wait">
                        {variant === 'SIGNIN' ? (
                            <SignInForm key="signin" onSwitch={toggleVariant} />
                        ) : (
                            <SignUpForm key="signup" onSwitch={toggleVariant} />
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>
        </main>
    );
}
