//** apps/web/components/products/ProductDetailsCard.tsx **//

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Check, Rocket, Package, TrendingUp, Bot, Star, ShieldCheck, Zap } from 'lucide-react';
import Image from 'next/image';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore'; // ✅ REPLACED: useCartStore -> useAIOrderingStore
import { type Product } from './ProductCard';

export const ProductDetailsCard = ({ product, onClose }: { product: Product, onClose: () => void }) => {
    
    // ✅ AI LINK: Using the Global AI Store
    const addProductById = useAIOrderingStore((state) => state.addProductById);
    
    const [isAdded, setIsAdded] = useState(false);
    // Unique ID for the button to serve as the start point for the flight animation
    const uniqueBtnId = `details-add-btn-${product.id}`; 

    const handleAddToCart = (e: React.MouseEvent) => {
        e.stopPropagation();
        
        // 🚀 ACTION: Trigger AI Logic & Flight Animation
        // This will make the product fly from this button to the Order With Air icon
        addProductById(product, uniqueBtnId);
        
        setIsAdded(true);
        setTimeout(() => setIsAdded(false), 2000);
    };

    return (
        <motion.div
            layoutId={`product-card-${product.id}`} 
            className="relative w-full h-full max-h-[85vh] flex flex-col md:flex-row gap-0 overflow-hidden bg-black/80 backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-[0_0_50px_rgba(0,198,255,0.15)]"
        >
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-900/10 via-transparent to-purple-900/10 pointer-events-none" />
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 blur-[80px] pointer-events-none" />

            <motion.button
                initial={{ opacity: 0, rotate: -90 }}
                animate={{ opacity: 1, rotate: 0 }}
                transition={{ delay: 0.2 }}
                onClick={onClose}
                className="absolute top-6 right-6 z-50 p-2.5 rounded-full bg-black/40 border border-white/10 text-gray-400 hover:text-white hover:bg-red-500/20 hover:border-red-500/30 transition-all duration-300"
                aria-label="Close"
            >
                <X size={20} />
            </motion.button>

            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="w-full md:w-1/2 relative bg-gradient-to-b from-white/5 to-transparent flex items-center justify-center p-12 overflow-hidden"
            >
                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.05]" />
                <motion.div 
                    className="relative z-10 w-full h-full max-h-[400px]"
                    animate={{ y: [0, -15, 0], rotate: [0, 2, 0] }}
                    transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                >
                    {product.image_url && (
                        <Image
                            src={product.image_url}
                            alt={product.name}
                            fill
                            className="object-contain drop-shadow-[0_25px_50px_rgba(0,0,0,0.5)]"
                            sizes="(max-width: 768px) 100vw, 50vw"
                            priority
                        />
                    )}
                </motion.div>
                
                <div className="absolute bottom-8 left-8 flex gap-2">
                    <div className="px-3 py-1 rounded-lg bg-black/40 border border-white/10 backdrop-blur-md text-[10px] text-cyan-400 font-mono">
                        SKU: {product.id.toString().padStart(6, '0')}
                    </div>
                    {product.isAIRec && (
                        <div className="px-3 py-1 rounded-lg bg-purple-500/20 border border-purple-500/30 backdrop-blur-md text-[10px] text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1">
                            <Bot size={12} /> AI Verified
                        </div>
                    )}
                </div>
            </motion.div>

            <motion.div
                 initial={{ opacity: 0, x: 20 }}
                 animate={{ opacity: 1, x: 0 }}
                 transition={{ duration: 0.5, delay: 0.2 }}
                 className="w-full md:w-1/2 flex flex-col p-8 md:p-10 relative"
            >
                <div className="flex-grow overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    
                    <div className="mb-6">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="flex text-yellow-400">
                                {[...Array(5)].map((_, i) => <Star key={i} size={14} className={i < 4 ? "fill-current" : "text-gray-700"} />)}
                            </div>
                            <span className="text-xs text-gray-500 font-mono">(4.8/5.0 RATING)</span>
                        </div>
                        <h2 className="text-4xl font-black text-white mb-2 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            {product.name}
                        </h2>
                        <div className="flex items-baseline gap-3">
                            <span className="text-3xl font-mono text-cyan-400 font-bold tracking-tight">
                                ${product.price.toFixed(2)}
                            </span>
                            {product.stock_level && (
                                <span className="text-xs text-green-400 font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-green-500/10 border border-green-500/20">
                                    {product.stock_level}
                                </span>
                            )}
                        </div>
                    </div>

                    <p className="text-gray-400 leading-relaxed mb-8 border-l-2 border-white/10 pl-4">
                        {product.description || "Specifications classified. High-performance unit ready for deployment."}
                    </p>

                    <div className="grid grid-cols-2 gap-3 mb-8">
                        <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                                <Rocket size={14} />
                                <span className="text-[10px] uppercase tracking-wider">Delivery ETA</span>
                            </div>
                            <span className="text-sm font-bold text-white">{product.predicted_delivery || "12 Mins"}</span>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                                <TrendingUp size={14} />
                                <span className="text-[10px] uppercase tracking-wider">Demand</span>
                            </div>
                            <span className="text-sm font-bold text-white">{product.trending_status || "High Velocity"}</span>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                                <ShieldCheck size={14} />
                                <span className="text-[10px] uppercase tracking-wider">Warranty</span>
                            </div>
                            <span className="text-sm font-bold text-white">Global Coverage</span>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                                <Zap size={14} />
                                <span className="text-[10px] uppercase tracking-wider">Power Cell</span>
                            </div>
                            <span className="text-sm font-bold text-white">Included</span>
                        </div>
                    </div>
                </div>

                <div className="mt-4 pt-6 border-t border-white/10">
                    <AnimatePresence mode="wait">
                        {isAdded ? (
                            <motion.button
                                key="added"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="w-full py-4 rounded-2xl bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 font-bold uppercase tracking-widest flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.3)]"
                            >
                                <Check size={20} /> System Acquired
                            </motion.button>
                        ) : (
                            <motion.button 
                                id={uniqueBtnId}
                                key="add" 
                                onClick={handleAddToCart} 
                                className="group w-full py-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold uppercase tracking-widest flex items-center justify-center gap-3 transition-all duration-300 hover:shadow-[0_0_30px_rgba(6,182,212,0.4)] hover:scale-[1.02]"
                                whileTap={{ scale: 0.98 }}
                            >
                                <Plus size={20} className="group-hover:rotate-90 transition-transform" /> 
                                Add to Manifest
                            </motion.button>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
        </motion.div>
    );
};
