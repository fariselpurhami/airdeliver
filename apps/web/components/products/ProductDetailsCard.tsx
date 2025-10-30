// apps/web/components/products/ProductDetailsCard.tsx 

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Check, Rocket, Package, TrendingUp, Bot, Star, MessageSquare } from 'lucide-react';
import Image from 'next/image';
import { useCartStore } from '@/hooks/useCartStore';
import { type Product } from './ProductCard';

export const ProductDetailsCard = ({ product, onClose }: { product: Product, onClose: () => void }) => {
    const { addToCart } = useCartStore();
    const [isAdded, setIsAdded] = useState(false);

    const handleAddToCart = (e: React.MouseEvent) => {
        e.stopPropagation();
        addToCart(product);
        setIsAdded(true);
        setTimeout(() => setIsAdded(false), 1200);
    };

    return (
        <motion.div
            layoutId={`product-card-${product.id}`} 
            className="relative w-[90vw] max-w-3xl h-[80vh] max-h-[600px] rounded-2xl bg-gradient-to-br from-gray-900 via-black to-gray-800 border border-white/10 p-8 flex flex-col md:flex-row gap-8 overflow-hidden shadow-2xl shadow-black/50"
        >
         
            <motion.button
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                onClick={onClose}
                className="absolute top-4 right-4 z-20 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white"
                aria-label="Close"
            >
                <X size={20} />
            </motion.button>

            <motion.div
                initial={{ opacity: 0, x: -50 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="w-full md:w-1/2 h-1/2 md:h-full flex justify-center items-center"
            >
                {product.image_url && (
                    <Image
                        src={product.image_url}
                        alt={product.name}
                        width={400} 
                        height={400}
                        sizes="(max-width: 768px) 90vw, 40vw"
                        priority 
                        className="w-auto h-auto max-h-full max-w-full object-contain drop-shadow-[0_15px_20px_rgba(0,198,255,0.2)]"
                    />
                )}
            </motion.div>

            <motion.div
                 initial={{ opacity: 0, x: 50 }}
                 animate={{ opacity: 1, x: 0 }}
                 transition={{ duration: 0.5, delay: 0.2 }}
                 className="w-full md:w-1/2 flex flex-col justify-center text-white overflow-y-auto pr-4 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent" 
            >
                {product.isAIRec && (
                    <div className="mb-3 bg-cyan-400/20 text-cyan-300 text-xs px-2 py-1 rounded-full border border-cyan-400/50 inline-flex items-center gap-1 self-start">
                        <Bot size={12} /> Suggested by AI
                    </div>
                 )}

                <h2 className="text-3xl font-bold mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {product.name}
                </h2>
                <p className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-violet-400 mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    ${product.price}
                </p>

                 <div className="space-y-3 text-sm text-gray-300 mb-6">
                   
                    <div className="flex items-center gap-1">
                        {[...Array(5)].map((_, i) => <Star key={i} size={16} className={i < 4 ? "text-yellow-400 fill-yellow-400" : "text-gray-600"}/>)}
                        <span className="text-gray-500 ml-1">(4.7)</span>
                    </div>
                     {product.predicted_delivery && <div className="flex items-center gap-2"><Rocket size={16} className="text-cyan-400"/><span>{product.predicted_delivery}</span></div>}
                     {product.trending_status && <div className="flex items-center gap-2"><TrendingUp size={16} className="text-violet-400"/><span>{product.trending_status}</span></div>}
                     {product.stock_level && <div className="flex items-center gap-2 text-yellow-400"><Package size={16} /><span>{product.stock_level}</span></div>}
                     
                     <p className="text-gray-400 pt-2">{product.description || "No description available."}</p>
                 </div>
                 <div className="mt-auto pt-6">
                    <AnimatePresence mode="wait">
                        {isAdded ? (
                        <motion.div key="added" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center justify-center gap-2 text-white font-semibold py-3 border border-green-500/50 bg-green-500/10 rounded-full">
                            <Check size={20} /> Added to Cart
                        </motion.div>
                        ) : (
                        <motion.button key="button" onClick={handleAddToCart} className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold px-6 py-3 rounded-full shadow-lg transition-all duration-300 transform hover:scale-105">
                            <Plus size={18} /> Add to Cart
                        </motion.button>
                        )}
                    </AnimatePresence>
                 </div>
            </motion.div>
        </motion.div>
    );
};
