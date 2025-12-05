//** apps/web/components/products/ProductCard.tsx **//

'use client';

import React, { useRef, useEffect, useState } from 'react';
import { motion, useMotionValue, useTransform, AnimatePresence } from 'framer-motion';
import { Bot, Rocket, Zap, ScanLine, ShoppingBag, Eye, Check } from 'lucide-react';
import Image from 'next/image';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore'; // ✅ LINKED TO AI BRAIN

// --- 3D PARALLAX HOOK (Unchanged logic, just cleaner) ---
const useParallax = (ref: React.RefObject<HTMLDivElement>) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [5, -5]); 
  const rotateY = useTransform(x, [-100, 100], [-5, 5]);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = element.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      x.set(((e.clientX - rect.left) - centerX) / centerX * 100);
      y.set(((e.clientY - rect.top) - centerY) / centerY * 100);
    };
    const handleMouseLeave = () => { x.set(0); y.set(0); };
    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [ref, x, y]);

  return { rotateX, rotateY };
};

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  inventory: number;
  predicted_delivery?: string;
  trending_status?: string;
  stock_level?: string;
  isAIRec?: boolean;
}

export const ProductCard = ({ product, priority = false, onOpen }: { product: Product, priority?: boolean, onOpen: (product: Product) => void }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const { rotateX, rotateY } = useParallax(cardRef); 
  
  // ✅ INTELLIGENCE INTEGRATION
  const { suggestedProductIds, addProductById } = useAIOrderingStore();
  const isRecommendedByAI = product.isAIRec || suggestedProductIds?.includes(product.id);
  
  const [isAdded, setIsAdded] = useState(false);
  const uniqueBtnId = `card-add-btn-${product.id}`; // Critical for FlyToCartAnimator to find start position

  const handleAddToCart = (e: React.MouseEvent) => {
      e.stopPropagation(); // Stop propagation to prevent opening details
      
      // 🚀 FLIGHT INITIATION
      addProductById(product, uniqueBtnId);
      
      // Visual feedback
      setIsAdded(true);
      setTimeout(() => setIsAdded(false), 2000);
  };

  return (
    <motion.div
      layoutId={`product-card-${product.id}`}
      ref={cardRef}
      onClick={() => onOpen(product)}
      variants={{ hidden: { opacity: 0, scale: 0.9 }, visible: { opacity: 1, scale: 1 } }}
      style={{ perspective: 1200 }}
      className="group relative h-[450px] w-full cursor-pointer z-0 hover:z-20"
    >
      <motion.div
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
        className="relative w-full h-full rounded-[36px] bg-[#050505] border border-white/10 overflow-hidden transition-all duration-500 group-hover:border-cyan-500/50 group-hover:shadow-[0_0_50px_rgba(6,182,212,0.15)] flex flex-col"
      >
        {/* --- IMAGE SECTION --- */}
        <div className="relative w-full flex-grow bg-gradient-to-b from-white/5 to-transparent p-6 flex items-center justify-center overflow-hidden">
            
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.05] bg-center" />
            
            {isRecommendedByAI && (
                <div 
                    className="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                    style={{ transform: "translateZ(40px)" }}
                >
                    <Bot size={12} className="text-cyan-400 animate-pulse" />
                    <span className="text-[10px] font-bold text-cyan-300 uppercase tracking-wider">AI Pick</span>
                </div>
            )}

            <div className="relative w-full h-full max-h-[220px]" style={{ transform: "translateZ(60px)" }}>
                {product.image_url ? (
                    <Image
                        src={product.image_url}
                        alt={product.name}
                        fill
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        priority={priority}
                        className="object-contain drop-shadow-[0_20px_40px_rgba(0,0,0,0.6)] transition-transform duration-700 ease-out group-hover:scale-110 group-hover:-translate-y-4"
                    />
                ) : (
                    <div className="flex items-center justify-center w-full h-full text-white/10">
                        <ScanLine size={48} />
                    </div>
                )}
            </div>
        </div>

        {/* --- INFO SECTION --- */}
        <div 
            className="relative w-full bg-[#080808]/95 backdrop-blur-xl border-t border-white/5 p-5 flex flex-col justify-between transition-colors duration-500 group-hover:bg-[#0a0a0a]"
            style={{ transform: "translateZ(20px)" }}
        >
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            <div className="mb-3">
                <div className="flex justify-between items-start gap-2 mb-1">
                    <h3 className="text-base font-bold text-white leading-tight line-clamp-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {product.name}
                    </h3>
                    <div className="p-1.5 rounded-lg bg-white/5 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <Zap size={12} className="fill-current" />
                    </div>
                </div>
                
                <p className="text-[10px] text-gray-500 font-mono tracking-wider uppercase">
                    {product.stock_level || "Ready for Dispatch"}
                </p>
            </div>

            {/* --- ACTION AREA (CONNECTED TO AI) --- */}
            <div className="mt-auto">
                <div className="flex items-end justify-between mb-3">
                    <div className="flex flex-col">
                        <span className="text-[10px] text-gray-600 uppercase font-bold">Unit Price</span>
                        <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-500" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            ${product.price.toFixed(2)}
                        </span>
                    </div>
                    {product.predicted_delivery && (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 border border-white/5 text-[10px] text-gray-400 group-hover:text-cyan-400 group-hover:border-cyan-500/20 transition-colors">
                            <Rocket size={10} />
                            <span>{product.predicted_delivery}</span>
                        </div>
                    )}
                </div>

                <AnimatePresence mode="wait">
                    {isAdded ? (
                        <motion.button
                            key="added"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="w-full py-2.5 rounded-xl bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 font-bold text-[10px] uppercase tracking-widest flex items-center justify-center gap-2"
                        >
                            <Check size={14} className="text-cyan-300" /> Uplinked
                        </motion.button>
                    ) : (
                        <div className="flex gap-2 h-10">
                            <motion.button 
                                id={uniqueBtnId}
                                key="add"
                                onClick={handleAddToCart}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.95 }}
                                className="flex-1 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500 hover:text-black font-bold text-[10px] uppercase tracking-widest flex items-center justify-center gap-2 transition-all duration-300 group/btn"
                            >
                                <ShoppingBag size={14} className="group-hover/btn:text-black transition-colors" /> 
                                <span className="group-hover/btn:text-black">Add to Manifest</span>
                            </motion.button>
                            <motion.button
                                key="view"
                                onClick={(e) => { e.stopPropagation(); onOpen(product); }}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                className="px-3 rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/20 hover:border-white/30 transition-all flex items-center justify-center"
                            >
                                <Eye size={16} />
                            </motion.button>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>

        <div className="absolute inset-0 rounded-[36px] ring-1 ring-white/0 group-hover:ring-white/10 transition-all duration-500 pointer-events-none" />
      </motion.div>
    </motion.div>
  );
};
