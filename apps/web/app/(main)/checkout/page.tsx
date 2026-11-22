//** apps/web/app/(main)/checkout/page.tsx **//

'use client';

import React, { useState, Suspense, useRef, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { 
    CreditCard, MapPin, User, Calendar, Lock, 
    Plane, ShieldCheck, Cpu, Wifi, Wind, Navigation, 
    Rocket, Clock, ScanLine
} from 'lucide-react';
import * as THREE from 'three';

// ============================================================================
// --- 1. THE HYPERDRIVE ENGINE (Background) ---
// ============================================================================

const HyperdriveStars = () => {
    const pointsRef = useRef<THREE.Points>(null!);
    const particleCount = 10000;
    const [positions, colors] = useMemo(() => {
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const color = new THREE.Color();

        for (let i = 0; i < particleCount; i++) {
            const x = (Math.random() - 0.5) * 400;
            const y = (Math.random() - 0.5) * 400;
            const z = (Math.random() - 0.5) * 400;
            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;
            const shade = Math.random();
            if (shade > 0.8) color.setHex(0xFFFFFF);
            else if (shade > 0.5) color.setHex(0x00FFFF);
            else color.setHex(0x0066FF);
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;
        }
        return [positions, colors];
    }, []);

    useFrame((state) => {
        if (pointsRef.current) {
            pointsRef.current.position.z += 0.5;
            if (pointsRef.current.position.z > 100) pointsRef.current.position.z = -100;
            pointsRef.current.rotation.z = state.clock.getElapsedTime() * 0.05;
        }
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" args={[positions, 3]} />
                <bufferAttribute attach="attributes-color" args={[colors, 3]} />
            </bufferGeometry>
            <pointsMaterial size={0.3} vertexColors transparent opacity={0.8} sizeAttenuation blending={THREE.AdditiveBlending} />
        </points>
    );
};

const BackgroundScene = () => (
    <>
        <fog attach="fog" args={['#000000', 50, 200]} />
        <ambientLight intensity={0.5} />
        <HyperdriveStars />
    </>
);

// ============================================================================
// --- 2. UI COMPONENTS (Refined for Silver Blur Glassmorphism) ---
// ============================================================================

const InputField = ({ icon: Icon, label, placeholder, type = "text", half = false }: any) => (
    <div className={`flex flex-col gap-2 ${half ? 'col-span-1' : 'col-span-2'}`}>
        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400 ml-1 whitespace-nowrap">
            {label}
        </label>
        <div className="relative group w-full">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-cyan-400 transition-colors pointer-events-none">
                <Icon size={18} />
            </div>
            <input 
                type={type}
                placeholder={placeholder}
                className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 focus:bg-white/10 transition-all shadow-inner"
            />
        </div>
    </div>
);

// ============================================================================
// --- 3. THE MAIN PAGE ---
// ============================================================================

export default function CheckoutPage() {
    const [isMounted, setIsMounted] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    useEffect(() => { setIsMounted(true); }, []);

    const handleLaunch = () => {
        setIsProcessing(true);
        setTimeout(() => setIsProcessing(false), 4000);
    };

    return (
        <div className="relative min-h-screen w-full bg-black text-gray-100 font-sans selection:bg-cyan-500/30 overflow-x-hidden">
            
            <div className="fixed inset-0 z-0">
                {isMounted && (
                    <Canvas camera={{ position: [0, 0, 50], fov: 60 }} dpr={[1, 2]}>
                        <Suspense fallback={null}>
                            <BackgroundScene />
                        </Suspense>
                    </Canvas>
                )}
            </div>

            <main className="relative z-20 container mx-auto px-4 pt-24 pb-24">
                
                <motion.div 
                    initial={{ opacity: 0, y: -20 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ duration: 0.8 }}
                    className="text-center mb-16 max-w-4xl mx-auto"
                >
                    <div className="inline-flex items-center gap-3 px-6 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-xl mb-6 shadow-[0_0_30px_rgba(6,182,212,0.15)]">
                        <Rocket size={14} className="text-cyan-400" />
                        <span className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-100">Orbital Launchpad</span>
                    </div>
                    <h1 className="text-4xl md:text-6xl font-black text-white mb-4 tracking-tighter drop-shadow-2xl" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        LAUNCH <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">SEQUENCE</span>
                    </h1>
                </motion.div>

                <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-5 gap-8">
                    
                    <div className="lg:col-span-3 space-y-6">
                        
                        <motion.div 
                            initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
                            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[30px] p-6 md:p-8 shadow-2xl relative overflow-hidden"
                        >
                            <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500/50" />
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 bg-cyan-500/10 rounded-xl border border-cyan-500/20 text-cyan-400">
                                    <MapPin size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold text-white tracking-wide" style={{ fontFamily: "'Orbitron', sans-serif" }}>Target Coordinates</h2>
                                    <p className="text-xs text-gray-500 uppercase tracking-widest">Delivery Vector</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-6 w-full">
                                <InputField icon={User} label="Recipient ID" placeholder="Full Name" />
                                <InputField icon={MapPin} label="Drop Zone" placeholder="Street Address" />
                                <InputField icon={ScanLine} label="Postal Sector" placeholder="ZIP Code" half />
                                <InputField icon={Wifi} label="Comm Link" placeholder="Phone Number" half type="tel" />
                            </div>
                        </motion.div>

                        <motion.div 
                            initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}
                            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[30px] p-6 md:p-8 shadow-2xl relative overflow-hidden"
                        >
                            <div className="absolute top-0 left-0 w-1 h-full bg-green-500/50" />
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 bg-green-500/10 rounded-xl border border-green-500/20 text-green-400">
                                    <ShieldCheck size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold text-white tracking-wide" style={{ fontFamily: "'Orbitron', sans-serif" }}>Authorization</h2>
                                    <p className="text-xs text-gray-500 uppercase tracking-widest">Payment Protocol</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-6 w-full">
                                <InputField icon={CreditCard} label="Card Sequence" placeholder="0000 0000 0000 0000" />
                                <InputField icon={Calendar} label="Exp. Cycle" placeholder="MM / YY" half />
                                <InputField icon={Lock} label="Security Key" placeholder="CVC" half type="password" />
                            </div>
                        </motion.div>

                    </div>

                    <div className="lg:col-span-2">
                        <div className="sticky top-24">

                            <motion.div 
                                initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
                                className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[30px] p-6 md:p-8 shadow-[0_0_50px_rgba(0,0,0,0.3)] w-full"
                            >
                                <div className="flex justify-between items-start mb-8">
                                    <h2 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Review & Place Order</h2>
                                    <Cpu size={24} className="text-cyan-500" />
                                </div>

                                <button 
                                    onClick={handleLaunch}
                                    disabled={isProcessing}
                                    className="group relative w-full overflow-hidden rounded-xl p-5 bg-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 shadow-lg shadow-cyan-500/20"
                                >
                                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                                    <div className="relative flex items-center justify-center gap-3 z-10">
                                        {isProcessing ? (
                                            <><div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" /><span className="text-black font-black uppercase tracking-[0.2em] text-xs">PLACING ORDER...</span></>
                                        ) : (
                                            <><span className="text-black font-black uppercase tracking-[0.2em] text-xs group-hover:text-white transition-colors">PLACE ORDER</span></>
                                        )}
                                    </div>
                                </button>
                            </motion.div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
