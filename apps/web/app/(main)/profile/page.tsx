'use client';

import React, { useState, Suspense, useRef } from 'react';
import { useSession, signIn, signOut } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { AtSign, Lock, User, Bot, ChevronsRight } from 'lucide-react';
import * as THREE from 'three';

// --- 3D Background Component ---
const AIBackground = () => {
    const particlesRef = useRef<THREE.Points>(null!);
    useFrame(({ mouse, viewport }) => {
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

// --- Futuristic Input Component ---
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

// --- Sign In Form Component ---
const SignInForm = ({ onSwitch }: { onSwitch: () => void }) => (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
        <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Access Granted</h1>
            <p className="text-gray-400 mt-2">Your identity in the new era of AI commerce.</p>
        </div>
        <form className="space-y-6">
            <FuturisticInput icon={<AtSign size={18} />} name="email" type="email" placeholder="Email Address" required />
            <FuturisticInput icon={<Lock size={18} />} name="password" type="password" placeholder="Password" required />
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" className="w-full glowing-button rounded-full py-3 text-lg font-bold">
                Sign In to the Future
            </motion.button>
        </form>
        <div className="flex items-center my-6">
            <div className="flex-grow h-px bg-white/10"></div>
            <span className="mx-4 text-xs text-gray-500">Or continue with</span>
            <div className="flex-grow h-px bg-white/10"></div>
        </div>
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="w-full flex items-center justify-center gap-2 glowing-button-outline rounded-full py-3 font-bold">
            <Bot size={18} /> Sign in with AI Account
        </motion.button>
        <div className="text-center text-sm text-gray-500 mt-6">
            <button onClick={onSwitch} className="hover:text-cyan-400 transition-colors">Create AI Account</button>
        </div>
    </motion.div>
);

// --- Sign Up Form Component ---
const SignUpForm = ({ onSwitch }: { onSwitch: () => void }) => (
     <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
        <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Join the AI Revolution</h1>
            <p className="text-gray-400 mt-2">Seamless access. Infinite intelligence.</p>
        </div>
        <form className="space-y-4">
            <FuturisticInput icon={<User size={18} />} name="fullName" type="text" placeholder="Full Name" required />
            <FuturisticInput icon={<AtSign size={18} />} name="email" type="email" placeholder="Email Address" required />
            <FuturisticInput icon={<Lock size={18} />} name="password" type="password" placeholder="Password" required />
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" className="w-full glowing-button rounded-full py-3 text-lg font-bold mt-4">
                Activate My AI Experience <ChevronsRight className="inline ml-2" size={20} />
            </motion.button>
        </form>
        <div className="text-center text-sm text-gray-500 mt-6">
            <button onClick={onSwitch} className="hover:text-cyan-400 transition-colors">Already have an account? Sign In</button>
        </div>
    </motion.div>
);


// --- Main Authentication Page ---
export default function AuthPage() {
    const [variant, setVariant] = useState<'SIGNIN' | 'SIGNUP'>('SIGNIN');
    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    return (
        <main className="relative min-h-screen w-full bg-black text-gray-100 flex items-center justify-center overflow-hidden">
            {/* 3D Background */}
            <div className="absolute inset-0 z-0 opacity-40">
                <Canvas camera={{ position: [0, 0, 5], fov: 75 }}>
                    <Suspense fallback={null}>
                        <AIBackground />
                        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={0.5} />
                    </Suspense>
                </Canvas>
            </div>
            
            {/* Holographic Scan Animation */}
             <motion.div 
                initial={{ y: '-100%', height: '5px' }}
                animate={{ y: '200vh' }}
                transition={{ duration: 2, ease: "easeInOut" }}
                className="absolute top-0 left-0 right-0 z-20 bg-cyan-400/50 blur-2xl"
             />

            {/* Layout Split */}
            <div className="relative z-10 container mx-auto grid grid-cols-1 md:grid-cols-2 items-center gap-16 px-4">
                {/* Left Section: Hero Visual */}
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

                {/* Right Section: Auth Card */}
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
