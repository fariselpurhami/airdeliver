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
import { CatalogImage as Image } from '@/components/products/CatalogImage';
import { useCartStore, type CartItem } from '@/hooks/useCartStore';
import { api } from '@/lib/api';
import { parseCartItems } from '@/lib/cart-snapshot';
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

const CartItemCapsule = ({ item, index, pending, onRemove }: { item: CartItem, index: number, pending: boolean, onRemove: (id: number) => void }) => {
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
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Total</p>
                        <p className="text-lg font-mono text-white">${(item.price * item.quantity).toFixed(2)}</p>
                    </div>
                </div>
            </div>

            {/* Action Module */}
            <button 
                onClick={() => onRemove(item.id)}
                disabled={pending}
                aria-label={`Remove ${item.name}`}
                aria-busy={pending}
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
            Your cart is empty
        </h3>
        <p className="text-gray-400 max-w-md mb-10 leading-relaxed">
            Browse the catalog and add items to get started.
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

const LogisticsPanel = ({ total, itemCount, clearCart, pending, uncertain }: { total: number, itemCount: number, clearCart: () => void, pending: boolean, uncertain: boolean }) => (
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
                <h2 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Order Summary</h2>
                            </div>
        </div>
        
        <div className="flex-grow space-y-5 mb-8">

            <div className="flex justify-between items-end">
                <span className="text-sm text-gray-400 uppercase tracking-widest">Total Value</span> 
                <span className="text-3xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>${total.toFixed(2)}</span>
            </div>
        </div>
        
        <div className="mt-auto space-y-4">
            <Link href="/checkout" passHref className={itemCount === 0 || pending || uncertain ? 'pointer-events-none' : ''} aria-disabled={itemCount === 0 || pending || uncertain} tabIndex={itemCount === 0 || pending || uncertain ? -1 : undefined} onClick={(event) => { if (itemCount === 0 || pending || uncertain) event.preventDefault(); }}>
                <motion.button
                    disabled={itemCount === 0 || pending || uncertain}
                    whileHover={{ scale: itemCount > 0 ? 1.02 : 1 }}
                    whileTap={{ scale: itemCount > 0 ? 0.98 : 1 }}
                    className="w-full group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-2xl shadow-lg transition-all overflow-hidden disabled:opacity-50 disabled:grayscale"
                >
                    <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <span className="relative flex items-center gap-2">
                        Proceed to Checkout
                    </span>
                </motion.button>
            </Link>
            
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-2 text-[10px] text-green-500 uppercase tracking-wider">
                    <ShieldCheck size={12} /> Secure Connection
                </div>
                <button 
                    onClick={clearCart} 
                    disabled={itemCount === 0 || pending || uncertain}
                    className="text-[10px] uppercase tracking-wider text-red-500/70 hover:text-red-500 disabled:opacity-30 transition-colors hover:underline decoration-red-500/30 underline-offset-4"
                >
                    Clear Cart
                </button>
            </div>
        </div>
    </motion.div>
);

// ============================================================================
// --- 3. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function CartPage() {
    const { items, clearCart, removeFromCart, replaceItems } = useCartStore();
    const [pending, setPending] = useState(false);
    const [mutationError, setMutationError] = useState<string | null>(null);
    const inFlight = useRef(false);
    const mutateCart = async (productId?: number) => {
        if (inFlight.current || mutationError) return;
        inFlight.current = true;
        setPending(true);
        try {
            if (productId !== undefined) {
                await api.post('/ai-ordering/cart/remove', { product_id: productId });
                removeFromCart(productId);
            } else {
                await api.post('/ai-ordering/cart/clear');
                clearCart();
            }
        } catch {
            setMutationError('We could not confirm the cart update. Your items are kept here. Refresh and check your cart before trying again or checking out.');
        } finally {
            inFlight.current = false;
            setPending(false);
        }
    };
    const refreshCart = async () => {
        if (inFlight.current) return;
        inFlight.current = true;
        setPending(true);
        try {
            const response = await api.get('/ai-ordering/cart');
            replaceItems(parseCartItems(response.data));
            setMutationError(null);
        } catch {
            setMutationError('We could not refresh your cart. Your items are kept here. Check your connection and refresh the cart before checking out.');
        } finally {
            inFlight.current = false;
            setPending(false);
        }
    };
    const handleClearCart = () => { void mutateCart(); };
    const total = items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    
    const [isMounted, setIsMounted] = useState(false);
    useEffect(() => {
        setIsMounted(true);
        void refreshCart();
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
                        Review your items before placing the order.
                    </p>
                </motion.section>

                {mutationError && (
                    <div role="alert" className="mb-8 rounded-2xl border border-red-400/50 bg-red-950/80 p-5 text-red-100">
                        <p>{mutationError}</p>
                        <button className="mt-3 underline font-semibold" disabled={pending} onClick={() => { void refreshCart(); }}>Refresh cart</button>
                    </div>
                )}
                {pending && <p role="status" className="mb-6 text-cyan-200">Updating your cart...</p>}
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
                                    {items.map((item, i) => <CartItemCapsule key={item.id} item={item} index={i} pending={pending || !!mutationError} onRemove={(id) => { void mutateCart(id); }} />)}
                                </AnimatePresence>
                            </Suspense>
                        </div>

                        {/* Right: Flight Panel */}
                        <div className="lg:col-span-4">
                            <LogisticsPanel total={total} itemCount={items.length} clearCart={handleClearCart} pending={pending} uncertain={!!mutationError} />
                        </div>
                    </div>
                )}

            </main>
        </div>
    );
}
