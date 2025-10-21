// file: components/products/ProductCard.tsx (Corrected - Duplicate Removed)
'use client';

import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Plus, Check, Bot, Rocket, Package, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useCartStore } from '@/hooks/useCartStore';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

// Custom Hook for the 3D tilt effect (Defined ONCE here)
const useParallax = (ref: React.RefObject<HTMLDivElement>) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const xTransform = useTransform(x, [-100, 100], [15, -15]);
  const yTransform = useTransform(y, [-100, 100], [-15, 15]);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = element.getBoundingClientRect();
      x.set(((e.clientX - rect.left) / rect.width - 0.5) * 200);
      y.set(((e.clientY - rect.top) / rect.height - 0.5) * 200);
    };
    const handleMouseLeave = () => { x.set(0); y.set(0); };
    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [ref, x, y]);

  return { rotateX: yTransform, rotateY: xTransform };
};

// The Product interface
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

// --- The main Product Card Component ---
export const ProductCard = ({ product, priority = false, onOpen }: { product: Product, priority?: boolean, onOpen: (product: Product) => void }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const { rotateX, rotateY } = useParallax(cardRef); // Using the hook defined above
  const { suggestedProductIds } = useAIOrderingStore();
  const isRecommendedByAI = product.isAIRec || suggestedProductIds?.includes(product.id);

  return (
    <motion.div
      layoutId={`product-card-${product.id}`}
      ref={cardRef}
      onClick={() => onOpen(product)}
      variants={{ hidden: { opacity: 0, y: 50 }, visible: { opacity: 1, y: 0 } }}
      style={{ transformStyle: "preserve-3d", rotateX, rotateY }}
      className="group relative h-96 w-full cursor-pointer"
    >
      <div className="absolute -inset-px bg-gradient-to-tr from-cyan-500 to-violet-500 rounded-2xl blur-lg opacity-0 group-hover:opacity-40 transition-opacity duration-500" />

      <div className="relative w-full h-full rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 p-6 flex flex-col justify-between overflow-hidden">

        {isRecommendedByAI && (
          <div className="absolute top-4 right-4 bg-cyan-400/20 text-cyan-300 text-xs px-2 py-1 rounded-full border border-cyan-400/50 flex items-center gap-1 z-10" style={{ transform: "translateZ(50px)" }}>
            <Bot size={12} /> Suggested by AI
          </div>
        )}

        <div className="absolute inset-0 flex justify-center items-center p-6 opacity-80 group-hover:opacity-100 transition-opacity" style={{ transform: "translateZ(40px)" }}>
          {product.image_url && (
              <Image
                src={product.image_url}
                alt={product.name}
                width={200}
                height={200}
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
		            priority={priority}
                className="w-auto h-auto max-h-[60%] max-w-[80%] object-contain drop-shadow-[0_10px_15px_rgba(0,0,0,0.5)] transition-transform duration-500 group-hover:scale-110"
              />
          )}
        </div>

        <div className="relative mt-auto z-10" style={{ transform: "translateZ(20px)" }}>
          <h3 className="text-xl font-bold text-white mb-1 truncate" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            {product.name}
          </h3>
          <p className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-violet-400 mb-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              ${product.price}
          </p>
           {product.predicted_delivery && <div className="flex items-center gap-2 text-xs text-gray-400"><Rocket size={14} className="text-cyan-400"/><span>{product.predicted_delivery}</span></div>}
        </div>

         <div
            className="absolute inset-0 flex justify-center items-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/30 backdrop-blur-sm"
            style={{ transform: "translateZ(60px)" }}
        >
             <span className="text-white font-bold text-lg">View Details</span>
        </div>
      </div>
    </motion.div>
  );
};

// --- The duplicate useParallax function that was here has been DELETED ---
