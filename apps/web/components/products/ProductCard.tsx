//** apps/web/components/products/ProductCard.tsx **//

'use client';

import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Plus, Check, Bot, Rocket, Package, TrendingUp, Zap } from 'lucide-react';
import Image from 'next/image';
import { useCartStore } from '@/hooks/useCartStore';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

const useParallax = (ref: React.RefObject<HTMLDivElement>) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [10, -10]);
  const rotateY = useTransform(x, [-100, 100], [-10, 10]);

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
  const { suggestedProductIds } = useAIOrderingStore();
  const isRecommendedByAI = product.isAIRec || suggestedProductIds?.includes(product.id);

  return (
    <motion.div
      layoutId={`product-card-${product.id}`}
      ref={cardRef}
      onClick={() => onOpen(product)}
      variants={{ hidden: { opacity: 0, y: 50 }, visible: { opacity: 1, y: 0 } }}
      style={{ perspective: 1000 }}
      className="group relative h-96 w-full cursor-pointer z-0 hover:z-10"
    >
      <motion.div
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
        className="relative w-full h-full rounded-[32px] bg-black/40 backdrop-blur-md border border-white/10 p-6 flex flex-col justify-between overflow-hidden transition-all duration-300 group-hover:border-cyan-500/30 group-hover:shadow-[0_0_40px_rgba(0,198,255,0.1)]"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

        {isRecommendedByAI && (
          <div className="absolute top-4 right-4 bg-cyan-500/20 text-cyan-300 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg border border-cyan-500/40 flex items-center gap-1 z-20" style={{ transform: "translateZ(30px)" }}>
            <Bot size={12} /> AI Match
          </div>
        )}

        <div className="absolute inset-0 flex justify-center items-center p-8 z-10" style={{ transform: "translateZ(50px)" }}>
          {product.image_url && (
              <Image
                src={product.image_url}
                alt={product.name}
                fill
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                priority={priority}
                className="object-contain drop-shadow-2xl transition-transform duration-500 group-hover:scale-110 group-hover:-translate-y-2"
              />
          )}
        </div>

        <div className="relative mt-auto z-20 p-2" style={{ transform: "translateZ(30px)" }}>
          <h3 className="text-lg font-bold text-white mb-1 truncate" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            {product.name}
          </h3>
          <div className="flex items-center justify-between">
              <p className="text-xl font-mono text-cyan-400 font-bold">
                  ${product.price.toFixed(2)}
              </p>
              {product.predicted_delivery && (
                  <div className="flex items-center gap-1.5 text-[10px] text-gray-400 bg-white/5 px-2 py-1 rounded-full">
                      <Rocket size={10} className="text-purple-400"/>
                      <span>{product.predicted_delivery}</span>
                  </div>
              )}
          </div>
        </div>

         <div
            className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-30"
            style={{ transform: "translateZ(60px)" }}
        >
             <div className="px-6 py-3 rounded-full border border-white/20 bg-white/10 backdrop-blur-md text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2">
                <Zap size={14} className="fill-current" /> Initialize View
             </div>
        </div>
      </motion.div>
    </motion.div>
  );
};
