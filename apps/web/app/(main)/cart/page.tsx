'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { Trash2 } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useCartStore, type CartItem } from '@/hooks/useCartStore';

const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-screen w-full bg-black">
        <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
);

const CartItemCard = ({ item }: { item: CartItem }) => {
    const { removeFromCart } = useCartStore();
    return (
        <motion.div
            layout
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50, transition: { duration: 0.3 } }}
            className="flex items-center gap-6 p-4 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl"
        >
            <div className="relative flex-shrink-0 w-24 h-24">
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
            </div>
            <div className="flex-shrink-0 text-right">
                <p className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>${(item.price * item.quantity).toFixed(2)}</p>
                <button onClick={() => removeFromCart(item.id)} className="text-red-500/50 hover:text-red-500 transition-colors mt-2 text-xs flex items-center gap-1 ml-auto">
                    <Trash2 size={14} /> Remove
                </button>
            </div>
        </motion.div>
    );
};

export default function CartPage() {
    const { items } = useCartStore();
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
             <div className="fixed inset-0 -z-10">
                <Canvas><Stars radius={50} depth={50} count={5000} factor={4} saturation={0} fade speed={1} /></Canvas>
            </div>

            <main className="container mx-auto px-4 py-24">
                <motion.section 
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="text-center mb-16"
                >
                    <h1 className="text-5xl md:text-7xl font-black uppercase text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Your Cart
                    </h1>
                    <p className="mt-4 text-gray-400">Precision Engineered by AI</p>
                </motion.section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-4">
                        <Suspense fallback={<LoadingSpinner />}>
                            <AnimatePresence>
                                {items.length > 0 ? (
                                    items.map(item => <CartItemCard key={item.id} item={item} />)
                                ) : (
                                    <div className="text-center py-16 text-gray-500">
                                        <h2 className="text-2xl font-bold mb-2">Your Cart is Empty</h2>
                                        <Link href="/products" className="text-cyan-400 hover:underline">Start Shopping</Link>
                                    </div>
                                )}
                            </AnimatePresence>
                        </Suspense>
                    </div>

                    <div className="relative">
                         <div className="sticky top-24">
                           
                            <motion.div className="p-6 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl flex flex-col min-h-[300px]">
                                <h2 className="text-2xl font-bold text-white mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>AI Summary</h2>
                                
                               
                                <div className="flex-grow space-y-3 text-sm text-gray-300 border-b border-white/10 pb-4 mb-4">
                                    <div className="flex justify-between"><span>Subtotal</span> <span>${total.toFixed(2)}</span></div>
                                    <div className="flex justify-between"><span>Drone Allocation</span> <span>{items.length > 0 ? '1 Medium Fleet' : 'N/A'}</span></div>
                                    <div className="flex justify-between"><span>Estimated ETA</span> <span>{items.length > 0 ? '14 Minutes' : 'N/A'}</span></div>
                                </div>
                                
                                <Link href="/checkout" passHref>
                                    <motion.button
                                        disabled={items.length === 0}
                                        className="w-full glowing-button rounded-full py-3 text-lg font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Proceed to Checkout
                                    </motion.button>
                                </Link>
                            </motion.div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
