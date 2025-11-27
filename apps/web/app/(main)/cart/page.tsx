'use client';

import React, { useState, useEffect, Suspense, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { 
    Trash2, Package, Cpu, Zap, Clock, Loader2, ArrowRight, X, 
    CloudSun, Route, ShieldCheck, Box, Barcode, Plane 
} from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useCartStore, type CartItem } from '@/hooks/useCartStore';
import dynamic from 'next/dynamic';
import * as THREE from 'three';

// ============================================================================
// --- 1. ARCHITECTURAL BACKGROUND (The Deep Grid) ---
// ============================================================================

const CartBackground = () => {
    const groupRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.02;
            groupRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.02;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 20, 80]} />
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={2} color="#00C6FF" />
            <pointLight position={[-10, -10, 5]} intensity={2} color="#7F00FF" />
            <Stars radius={100} depth={60} count={6000} factor={4} saturation={0} fade speed={0.5} />
            
            {/* Abstract Cargo Grid */}
            {Array.from({ length: 10 }).map((_, i) => (
                <mesh key={i} position={[Math.sin(i) * 20, Math.cos(i) * 20, -30 + i * 2]} rotation={[0, 0, i * 0.5]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#00C6FF" wireframe transparent opacity={0.1} />
                </mesh>
            ))}
        </group>
    );
};

const DynamicCartBackground = dynamic(() => Promise.resolve(CartBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. UI MODULES (The Interface) ---
// ============================================================================

const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-screen w-full bg-black">
        <div className="relative">
            <div className="absolute inset-0 bg-cyan-500 blur-xl opacity-20 animate-pulse" />
            <Loader2 className="w-16 h-16 text-cyan-400 animate-spin relative z-10" />
        </div>
    </div>
);

const CartItemCapsule = ({ item, index }: { item: CartItem, index: number }) => {
    const { removeFromCart } = useCartStore();
    
    return (
        <motion.div
            layout
            initial={{ opacity: 0, x: -50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -50, scale: 0.8 }}
            transition={{ delay: index * 0.1, type: 'spring', stiffness: 200, damping: 25 }}
            className="group relative flex flex-col sm:flex-row items-center gap-6 p-6 bg-black/40 backdrop-blur-xl border border-white/10 rounded-[30px] shadow-lg hover:border-cyan-500/30 transition-all duration-300 overflow-hidden"
        >
            {/* Holographic Glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-3xl -z-10 group-hover:bg-cyan-500/10 transition-colors" />

            {/* Product Visual */}
            <div className="relative flex-shrink-0 w-32 h-32 rounded-2xl overflow-hidden bg-white/5 border border-white/5 p-2">
                {item.image_url ? (
                    <Image 
                        src={item.image_url} 
                        alt={item.name}
                        fill
                        className="object-contain hover:scale-110 transition-transform duration-500"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-600">
                        <Package size={32} />
                    </div>
                )}
            </div>

            {/* Data Core */}
            <div className="flex-grow text-center sm:text-left w-full">
                <div className="flex flex-col sm:flex-row justify-between items-start mb-2">
                    <h3 className="text-xl font-bold text-white mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {item.name}
                    </h3>
                    <span className="text-xs font-mono text-cyan-500/70 flex items-center gap-1 bg-cyan-950/30 px-2 py-1 rounded border border-cyan-500/20">
                        <Barcode size={10} /> SKU-{item.id.toString().padStart(4, '0')}
                    </span>
                </div>
                
                <p className="text-sm text-gray-400 mb-4 font-light max-w-md">
                    Automated handling unit ready for dispatch.
                </p>

                <div className="flex items-center justify-between sm:justify-start gap-8 border-t border-white/5 pt-4">
                    <div className="text-left">
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Unit Price</p>
                        <p className="text-lg font-mono text-white">${item.price.toFixed(2)}</p>
                    </div>
                    <div className="text-left">
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Quantity</p>
                        <p className="text-lg font-mono text-cyan-400">x{item.quantity}</p>
                    </div>
                    <div className="text-left hidden sm:block">
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Total Payload</p>
                        <p className="text-lg font-mono text-white">${(item.price * item.quantity).toFixed(2)}</p>
                    </div>
                </div>
            </div>

            {/* Action Module */}
            <button 
                onClick={() => removeFromCart(item.id)} 
                className="absolute top-4 right-4 sm:relative sm:top-0 sm:right-0 p-3 rounded-xl text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
                title="Eject Item"
            >
                <Trash2 size={20} />
            </button>
        </motion.div>
    );
};

const VoidState = () => (
    <motion.div
        layout
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="w-full flex flex-col items-center justify-center text-center py-24 px-10 bg-black/40 backdrop-blur-xl border border-white/10 rounded-[40px] shadow-2xl relative overflow-hidden"
    >
        <div className="absolute inset-0 bg-grid-white/[0.02] -z-10" />
        
        <motion.div
             animate={{ 
                 y: [-10, 10, -10],
                 opacity: [0.5, 1, 0.5],
                 filter: ['drop-shadow(0 0 0px rgba(0,198,255,0))', 'drop-shadow(0 0 20px rgba(0,198,255,0.5))', 'drop-shadow(0 0 0px rgba(0,198,255,0))']
             }}
             transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
             className="mb-8 p-8 rounded-full border border-cyan-500/20 bg-cyan-900/10"
        >
            <Box size={64} className="text-cyan-400" />
        </motion.div>
        
        <h3 className="text-3xl font-bold text-white mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            Manifest Empty
        </h3>
        <p className="text-gray-400 max-w-md mb-10 leading-relaxed">
            The cargo bay is currently clear. Initiate product acquisition to begin autonomous dispatch sequence.
        </p>
        
        <Link href="/products" passHref>
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="group relative inline-flex items-center justify-center px-8 py-4 text-sm font-bold text-black bg-white rounded-full overflow-hidden shadow-[0_0_20px_rgba(255,255,255,0.3)]"
            >
                <span className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <span className="relative flex items-center gap-2">
                    Access Catalog <ArrowRight size={16} />
                </span>
            </motion.button>
        </Link>
    </motion.div>
);

const LogisticsPanel = ({ total, itemCount, clearCart }: { total: number, itemCount: number, clearCart: () => void }) => (
    <motion.div 
        layout
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="sticky top-28 p-8 bg-black/60 backdrop-blur-2xl border border-white/10 rounded-[40px] shadow-2xl flex flex-col min-h-[400px]"
    >
        <div className="flex items-center gap-3 mb-8 pb-6 border-b border-white/10">
            <div className="p-3 rounded-xl bg-cyan-900/20 border border-cyan-500/20 text-cyan-400">
                <Cpu size={24} />
            </div>
            <div>
                <h2 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Flight Manifest</h2>
                <p className="text-xs text-gray-500 uppercase tracking-wider">System Status: Active</p>
            </div>
        </div>
        
        {/* --- Telemetry Data --- */}
        <div className="flex-grow space-y-5 mb-8">
            <div className="flex justify-between items-center group">
                <span className="text-sm text-gray-400 flex items-center gap-2 group-hover:text-cyan-400 transition-colors"><Zap size={16} /> Assigned Unit</span> 
                <span className="text-white font-mono text-sm border border-white/10 px-2 py-1 rounded bg-white/5">{itemCount > 0 ? 'DRONE-X1' : '--'}</span>
            </div>
            <div className="flex justify-between items-center group">
                <span className="text-sm text-gray-400 flex items-center gap-2 group-hover:text-cyan-400 transition-colors"><Route size={16} /> Vector</span> 
                <span className={`text-sm font-mono ${itemCount > 0 ? 'text-cyan-400 animate-pulse' : 'text-gray-600'}`}>{itemCount > 0 ? 'Calculating...' : '--'}</span>
            </div>
             <div className="flex justify-between items-center group">
                <span className="text-sm text-gray-400 flex items-center gap-2 group-hover:text-green-400 transition-colors"><CloudSun size={16} /> Conditions</span> 
                <span className="text-green-400 font-mono text-sm">{itemCount > 0 ? 'Optimal' : '--'}</span>
            </div>
            <div className="flex justify-between items-center group">
                <span className="text-sm text-gray-400 flex items-center gap-2 group-hover:text-cyan-400 transition-colors"><Clock size={16} /> ETA</span> 
                <span className="text-white font-mono text-sm">{itemCount > 0 ? '14m 30s' : '--'}</span>
            </div>

            <div className="w-full h-px bg-white/10 my-4" />

            <div className="flex justify-between items-end">
                <span className="text-sm text-gray-400 uppercase tracking-widest">Total Value</span> 
                <span className="text-3xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>${total.toFixed(2)}</span>
            </div>
        </div>
        
        <div className="mt-auto space-y-4">
            <Link href="/checkout" passHref className={itemCount === 0 ? 'pointer-events-none' : ''}>
                <motion.button
                    disabled={itemCount === 0}
                    whileHover={{ scale: itemCount > 0 ? 1.02 : 1 }}
                    whileTap={{ scale: itemCount > 0 ? 0.98 : 1 }}
                    className="w-full group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-2xl shadow-lg transition-all overflow-hidden disabled:opacity-50 disabled:grayscale"
                >
                    <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <span className="relative flex items-center gap-2">
                        Initialize Checkout <Plane size={18} fill="currentColor" />
                    </span>
                </motion.button>
            </Link>
            
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-2 text-[10px] text-green-500 uppercase tracking-wider">
                    <ShieldCheck size={12} /> Secure Connection
                </div>
                <button 
                    onClick={clearCart} 
                    disabled={itemCount === 0}
                    className="text-[10px] uppercase tracking-wider text-red-500/70 hover:text-red-500 disabled:opacity-30 transition-colors hover:underline decoration-red-500/30 underline-offset-4"
                >
                    Abort & Clear
                </button>
            </div>
        </div>
    </motion.div>
);

// ============================================================================
// --- 3. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function CartPage() {
    const { items, clearCart } = useCartStore(); 
    const total = items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    
    const [isMounted, setIsMounted] = useState(false);
    useEffect(() => {
        setIsMounted(true);
    }, []);

    if (!isMounted) {
        return <LoadingSpinner />;
    }

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 selection:bg-cyan-500/30 font-sans">
             {/* Background */}
             <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <Suspense fallback={null}>
                        <DynamicCartBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
            </div>

            <main className="relative z-10 w-full max-w-7xl mx-auto px-4 py-32 md:py-40">
                
                {/* Header */}
                <motion.section 
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="text-center mb-20"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-900/10 backdrop-blur-md mb-8">
                        <Box size={14} className="text-cyan-400" />
                        <span className="text-xs font-bold uppercase tracking-widest text-cyan-200/80">Logistics Hub V2.4</span>
                    </div>
                    <h1 className="text-5xl md:text-7xl font-black text-white mb-6 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                         <motion.span
                            className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600"
                            animate={{
                                filter: [
                                    'drop-shadow(0 0 10px rgba(6,182,212,0.3))',
                                    'drop-shadow(0 0 20px rgba(6,182,212,0.6))',
                                    'drop-shadow(0 0 10px rgba(6,182,212,0.3))'
                                ]
                            }}
                            transition={{ duration: 4, repeat: Infinity }}
                        >
                            CARGO BAY
                        </motion.span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
                        Review manifest for autonomous dispatch. Ensure payload parameters are correct before initializing flight sequence.
                    </p>
                </motion.section>

                {items.length === 0 ? (
                    <motion.div layout className="max-w-2xl mx-auto">
                        <Suspense fallback={<LoadingSpinner />}>
                            <AnimatePresence>
                                <VoidState />
                            </AnimatePresence>
                        </Suspense>
                    </motion.div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                        {/* Left: Items List */}
                        <div className="lg:col-span-8 space-y-6">
                            <Suspense fallback={<LoadingSpinner />}>
                                <AnimatePresence>
                                    {items.map((item, i) => <CartItemCapsule key={item.id} item={item} index={i} />)}
                                </AnimatePresence>
                            </Suspense>
                        </div>

                        {/* Right: Flight Panel */}
                        <div className="lg:col-span-4">
                            <LogisticsPanel total={total} itemCount={items.length} clearCart={clearCart} />
                        </div>
                    </div>
                )}

            </main>
        </div>
    );
}
