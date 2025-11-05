'use client';

import { CalendarDays, Route, CloudSun, Zap, Cpu, Lock, CreditCard, User, MapPin, Clock } from 'lucide-react';
import React, { Suspense, useRef } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button'; 
import { Input } from '@/components/ui/input'; 
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';

// ============================================================================
// --- 1. (New) Checkout Background Component ---
// ============================================================================
const CheckoutBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.x = Math.sin(time * 0.5) * 15;
            light1Ref.current.position.y = Math.cos(time * 0.5) * 15;
            light1Ref.current.position.z = Math.cos(time * 0.5) * 10;
        }
        if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(time * 0.3) * -15;
            light2Ref.current.position.y = Math.cos(time * 0.3) * -15;
            light2Ref.current.position.z = Math.sin(time * 0.3) * 5;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 10, 30]} />
            <ambientLight intensity={1.0} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        </>
    );
};

const DynamicCheckoutBackground = dynamic(() => Promise.resolve(CheckoutBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. (Re-styled) Sub-Components ---
// ============================================================================
const FuturisticInput = ({ icon, ...props }: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative">
        <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500">{icon}</div>
        <Input 
            {...props} 
            className="w-full pl-11 pr-4 py-3 bg-black/20 border border-cyan-400/30 rounded-lg text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-0 focus-visible:ring-offset-black/10"
        />
    </div>
);

const FlightPlanItem = ({ icon, label, value, valueColor = 'text-cyan-300' }: {
    icon: React.ReactNode;
    label: string;
    value: string;
    valueColor?: string;
}) => (
    <div className="flex justify-between items-center">
        <span className="text-gray-400 flex items-center gap-2"><span className="opacity-70">{icon}</span> {label}</span> 
        <span className={`font-semibold ${valueColor}`}>{value}</span>
    </div>
);

// ============================================================================
// --- 3. (Re-built) Main Page Component ---
// ============================================================================
export default function CheckoutPage() {
    
   
    const mockOrder = {
        subtotal: 96.00,
        drone: 'A.I.D.A. Mk. IV',
        path: 'Calculating... (12.4km)',
        weather: 'Clear / Optimal',
        eta: '14 Minutes (Pending Auth.)'
    };

    return (
        <main className="min-h-screen w-full bg-black text-gray-100 p-4 py-24 md:py-32" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            <div className="fixed inset-0 z-0 opacity-70">
                <Canvas>
                    <Suspense fallback={null}>
                        <DynamicCheckoutBackground />
                    </Suspense>
                </Canvas>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                className="relative z-10 w-full max-w-6xl mx-auto"
            >
                <div className="text-center mb-12">
                    <h1 className="text-4xl md:text-5xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Launch Sequence
                    </h1>
                    <p className="text-gray-400 mt-2 max-w-lg mx-auto">Authorize payment to deploy your autonomous fleet. Please confirm your flight plan.</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">

                   
                    <div className="lg:col-span-3">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
                            className="relative p-6 md:p-8 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl shadow-2xl shadow-cyan-500/10"
                        >
                            <form className="space-y-6">
                                <div>
                                    <h2 className="text-lg font-semibold text-cyan-400 border-b border-white/10 pb-2 mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                        1. Shipping Details
                                    </h2>
                                    <div className="space-y-4">
                                        <FuturisticInput icon={<User size={18} />} type="text" placeholder="Full Name" />
                                        <FuturisticInput icon={<MapPin size={18} />} type="text" placeholder="Delivery Address" />
                                    </div>
                                </div>
                                
                                <div>
                                    <h2 className="text-lg font-semibold text-cyan-400 border-b border-white/10 pb-2 mb-4 pt-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                        2. Payment Authorization
                                    </h2>
                                    <div className="space-y-4">
                                        <FuturisticInput icon={<CreditCard size={18} />} type="text" placeholder="Card Number" />
                                        <div className="grid grid-cols-2 gap-4">
                                            <FuturisticInput icon={<CalendarDays size={18} />} type="text" placeholder="MM / YY" />
                                            <FuturisticInput icon={<Lock size={18} />} type="text" placeholder="CVC" />
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </motion.div>
                    </div>

                    <div className="lg:col-span-2">
                         <div className="sticky top-24">
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.7, delay: 0.4, ease: "easeOut" }}
                                className="p-6 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl flex flex-col shadow-2xl shadow-cyan-500/10"
                            >
                                <h2 className="text-2xl font-bold text-white mb-6 pb-4 border-b border-cyan-400/30 flex items-center gap-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    <Cpu size={20} className="text-cyan-400" />
                                    Flight Plan
                                </h2>
                                
                                <div className="flex-grow space-y-4 text-sm text-gray-300 mb-6">
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-400">Subtotal</span> 
                                        <span className="text-white font-semibold text-base">${mockOrder.subtotal.toFixed(2)}</span>
                                    </div>
                                    
                                    <div className="w-full h-px bg-cyan-400/20 my-2" />

                                    <FlightPlanItem icon={<Zap size={14} />} label="Drone Assigned" value={mockOrder.drone} />
                                    <FlightPlanItem icon={<Route size={14} />} label="Flight Path" value={mockOrder.path} valueColor="text-cyan-300 animate-pulse" />
                                    <FlightPlanItem icon={<CloudSun size={14} />} label="Weather" value={mockOrder.weather} valueColor="text-green-300" />
                                    <FlightPlanItem icon={<Clock size={14} />} label="Estimated ETA" value={mockOrder.eta} />
                                </div>
                                
                                <div className="mt-auto pt-6">
                                    <motion.button
                                        type="submit"
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.98 }}
                                        className="w-full group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 overflow-hidden"
                                    >
                                        <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                        <span className="relative">Authorize & Launch Fleet</span>
                                    </motion.button>
                                </div>
                            </motion.div>
                        </div>
                    </div>
                </div>
            </motion.div>
        </main>
    );
}
