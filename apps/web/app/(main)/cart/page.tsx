'use client';

import React, { useState, useEffect, Suspense, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { Trash2, Package, Cpu, Zap, Clock, Loader2, ArrowRight, X, CloudSun, Route } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useCartStore, type CartItem } from '@/hooks/useCartStore';
import dynamic from 'next/dynamic';
import * as THREE from 'three';

// ============================================================================
// --- 1. (New) Cart Background Component ---
// ============================================================================
const CartBackground = () => {
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

const DynamicCartBackground = dynamic(() => Promise.resolve(CartBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. (Re-styled) Sub-Components ---
// ============================================================================

const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-screen w-full bg-black">
        <Loader2 className="w-12 h-12 text-cyan-400 animate-spin" />
    </div>
);

const CartItemCard = ({ item }: { item: CartItem }) => {
    const { removeFromCart } = useCartStore();
    return (
        <motion.div
            layout
            initial={{ opacity: 0, x: -50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, transition: { duration: 0.3 } }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="flex items-center gap-6 p-4 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10"
        >
            <div className="relative flex-shrink-0 w-24 h-24 rounded-lg overflow-hidden bg-black/20">
                {item.image_url && (
                    <Image 
                        src={item.image_url} 
                        alt={item.name}
                        width={96}
                        height={96}
                        priority
                        sizes="96px"
                        className="object-contain"
                    />
                )}
            </div>
            <div className="flex-grow">
                <h3 className="text-lg font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{item.name}</h3>
                <p className="text-sm text-gray-400">Quantity: {item.quantity}</p>
                 <p className="text-lg font-medium text-cyan-400" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    ${(item.price * item.quantity).toFixed(2)}
                </p>
            </div>
            <button 
                onClick={() => removeFromCart(item.id)} 
                className="p-3 rounded-full text-red-500/60 hover:text-red-500 hover:bg-red-500/10 transition-colors"
                aria-label="Remove item"
            >
                <X size={20} />
            </button>
        </motion.div>
    );
};

const EmptyCart = () => (
    <motion.div
        layout
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.5, ease: 'easeInOut' }}
        className="w-full flex flex-col items-center justify-center text-center py-16 px-10 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl shadow-lg shadow-cyan-500/10"
    >
        <motion.div
             animate={{ y: [-4, 4, -4], opacity: [0.8, 1, 0.8] }}
             transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
            <Package size={64} className="text-cyan-400/30 mb-6" />
        </motion.div>
        
        <h3
            className="text-2xl font-semibold text-white mb-2"
            style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
            Your Cart is Empty
        </h3>
        <p className="text-gray-500 max-w-sm mb-8">
            Products you add to your cart will appear here, ready for autonomous deployment.
        </p>
        <Link href="/products" passHref>
            <motion.button
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.98 }}
                animate={{ boxShadow: ['0 0 10px rgba(0, 198, 255, 0.3)', '0 0 25px rgba(0, 198, 255, 0.6)', '0 0 10px rgba(0, 198, 255, 0.3)'] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                className="group relative inline-flex items-center justify-center px-8 py-3 text-base font-bold text-cyan-200 bg-cyan-500/20 border-2 border-cyan-500/50 rounded-full shadow-lg"
            >
                Explore The Catalog <ArrowRight className="ml-2 h-5 w-5" />
            </motion.button>
        </Link>
    </motion.div>
);

const AISummaryCard = ({ total, itemCount, clearCart }: { total: number, itemCount: number, clearCart: () => void }) => (
    <motion.div 
        layout
        className="p-6 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl flex flex-col min-h-[300px] shadow-2xl shadow-cyan-500/10"
    >
        <h2 className="text-2xl font-bold text-white mb-6 pb-4 border-b border-cyan-400/30 flex items-center gap-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            <Cpu size={20} className="text-cyan-400" />
	    Flight Plan 
            
        </h2>
        
        {/* --- "Live" Data Panel --- */}
        <div className="flex-grow space-y-4 text-sm text-gray-300 mb-6">
            <div className="flex justify-between items-center">
                <span className="text-gray-400">Subtotal</span> 
                <span className="text-white font-semibold text-base">${total.toFixed(2)}</span>
            </div>
            
            <div className="w-full h-px bg-cyan-400/20 my-2" />

            <div className="flex justify-between items-center">
                <span className="text-gray-400 flex items-center gap-2"><Zap size={14} /> Drone Assigned</span> 
                <span className="text-cyan-300 font-semibold">{itemCount > 0 ? 'A.I.D.A. Mk. IV' : 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
                <span className="text-gray-400 flex items-center gap-2"><Route size={14} /> Flight Path</span> 
                <span className={`text-cyan-300 font-semibold ${itemCount > 0 ? 'animate-pulse' : ''}`}>{itemCount > 0 ? 'Calculating... (12.4km)' : 'N/A'}</span>
            </div>
             <div className="flex justify-between items-center">
                <span className="text-gray-400 flex items-center gap-2"><CloudSun size={14} /> Weather</span> 
                <span className="text-green-300 font-semibold">{itemCount > 0 ? 'Clear / Optimal' : 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
                <span className="text-gray-400 flex items-center gap-2"><Clock size={14} /> Estimated ETA</span> 
                <span className="text-cyan-300 font-semibold">{itemCount > 0 ? '14 Minutes' : 'N/A'}</span>
            </div>
        </div>
        
        <div className="mt-auto space-y-3">
            <Link href="/checkout" passHref>
                <motion.button
                    disabled={itemCount === 0}
                    whileHover={{ scale: itemCount > 0 ? 1.05 : 1 }}
                    whileTap={{ scale: itemCount > 0 ? 0.98 : 1 }}
                    className="w-full group relative inline-flex items-center justify-center px-8 py-3 text-base font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <span className="relative">Proceed to Checkout</span>
                </motion.button>
            </Link>
            <button 
                onClick={clearCart} 
                disabled={itemCount === 0}
                className="w-full text-center text-red-500/60 text-xs hover:text-red-500 disabled:opacity-30 transition-colors"
            >
                Clear Cart
            </button>
        </div>
    </motion.div>
);

// ============================================================================
// --- 3. (Re-built) Main Page Component ---
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
        <div className="min-h-screen w-full bg-black text-gray-100">
             <div className="fixed inset-0 z-0 opacity-70">
                <Canvas>
                    <Suspense fallback={null}>
                        <DynamicCartBackground />
                    </Suspense>
                </Canvas>
            </div>

            <main className="w-full max-w-6xl mx-auto px-4 py-24 md:py-32 relative z-10">
                <motion.section 
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="text-center mb-16"
                >
                    <h1 className="text-5xl md:text-7xl font-black uppercase text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                         <motion.span
                            className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                            animate={{
                            filter: [
                                'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))',
                                'drop-shadow(0 0 16px rgba(0, 198, 255, 0.8)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.8))',
                                'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))'
                            ]
                            }}
                            transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: "easeInOut"
                            }}
                        >
                            YOUR CART
                        </motion.span>
                    </h1>
                    <p className="mt-4 text-gray-400">Review your cart and prepare for autonomous dispatch.</p>
                </motion.section>

                {items.length === 0 ? (
                    
                    <motion.div
                        layout
                        className="flex flex-col items-center gap-8 w-full max-w-lg mx-auto"
                    >
                        <Suspense fallback={<LoadingSpinner />}>
                            <AnimatePresence>
                                <EmptyCart />
                            </AnimatePresence>
                        </Suspense>
                        
                        <div className="w-full">
                           <AISummaryCard total={total} itemCount={items.length} clearCart={clearCart} />
                        </div>
                    </motion.div>

                ) : (
                    
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <motion.div 
                            layout
                            className="lg:col-span-2 space-y-4"
                        >
                            <Suspense fallback={<LoadingSpinner />}>
                                <AnimatePresence>
                                    {items.map(item => <CartItemCard key={item.id} item={item} />)}
                                </AnimatePresence>
                            </Suspense>
                        </motion.div>

                        <div className="relative">
                            <div className="sticky top-24">
                                <AISummaryCard total={total} itemCount={items.length} clearCart={clearCart} />
                            </div>
                        </div>
                    </div>
                )}

            </main>
        </div>
    );
}
