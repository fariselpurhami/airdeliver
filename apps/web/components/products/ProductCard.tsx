//** apps/web/components/products/ProductCard.tsx **//

'use client';

import React, { useRef, useEffect, useState } from 'react';
import { motion, useMotionValue, useTransform, AnimatePresence } from 'framer-motion';
import { Bot, ScanLine, ShoppingBag, Check } from 'lucide-react';
import Image from 'next/image';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore'; 

const formatPrice = (value: number | string | undefined | null): string => {
    if (value === undefined || value === null) return '0.00';
    const num = Number(value);
    return isNaN(num) ? '0.00' : num.toFixed(2);
};

// 🛡️ L8 FIX: إيقاف الـ Parallax تماماً على شاشات اللمس (الموبايل) لمنع تسريب الذاكرة
const useParallax = (ref: React.RefObject<HTMLDivElement | null>) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [5, -5]); 
  const rotateY = useTransform(x, [-100, 100], [-5, 5]);

  useEffect(() => {
    const isTouchDevice = window.matchMedia("(pointer: coarse)").matches;
    if (isTouchDevice) return; 

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
    
    element.addEventListener('mousemove', handleMouseMove, { passive: true });
    element.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    return () => {
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [ref, x, y]);

  return { rotateX, rotateY };
};

// Canonical product contract lives in types/index; re-exported here for
// existing importers (ProductDetailsCard).
export type { Product } from '@/types';
import type { Product } from '@/types';

export const ProductCard = ({ product, priority = false, onOpen }: { product: Product, priority?: boolean, onOpen: (product: Product) => void }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const { rotateX, rotateY } = useParallax(cardRef); 
  
  const { suggestedProductIds, addProductById } = useAIOrderingStore();
  const isRecommendedByAI = product.isAIRec || suggestedProductIds?.includes(product.id);
  
  const [isAdded, setIsAdded] = useState(false);
  const uniqueBtnId = `card-add-btn-${product.id}`; 
  const safePrice = formatPrice(product.price); 

  const handleAddToCart = (e: React.MouseEvent) => {
      e.stopPropagation(); 
      addProductById(product as any, uniqueBtnId);
      setIsAdded(true);
      setTimeout(() => setIsAdded(false), 2000);
  };

  return (
    <motion.div
      layoutId={`product-card-${product.id}`}
      ref={cardRef}
      onClick={() => onOpen(product as any)}
      variants={{ hidden: { opacity: 0 }, visible: { opacity: 1 } }}
      style={{ perspective: 1200 }}
      // 📱 UX FIX: w-full عشان يملى العمود بتاعه في الـ Grid، وطول 320px للموبايل عشان يكون متناسق
      className="group relative min-h-[320px] md:min-h-[450px] h-full w-full flex-shrink-0 cursor-pointer z-0 hover:z-20 transform-gpu flex flex-col"
    >
      <motion.div
        style={{ rotateX, rotateY }} 
        // تصغير الحواف المدوّرة في الموبايل لتناسب الحجم الجديد rounded-[24px]
        className="relative w-full h-full rounded-[24px] md:rounded-[36px] bg-[#050505] border border-white/10 overflow-hidden transition-all duration-500 md:group-hover:border-cyan-500/50 md:group-hover:shadow-[0_0_50px_rgba(6,182,212,0.15)] flex flex-col md:[transform-style:preserve-3d]"
      >
        {/* تقليل الـ Padding الداخلي في الموبايل لـ p-3 عشان ندي مساحة أكبر للمحتوى */}
        <div className="relative w-full flex-grow bg-gradient-to-b from-white/5 to-transparent p-3 md:p-6 flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.05] bg-center" />
            
            {isRecommendedByAI && (
                <div className="absolute top-2 right-2 md:top-4 md:right-4 z-20 flex items-center gap-1 px-1.5 py-1 md:px-3 md:py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(6,182,212,0.2)] md:[transform:translateZ(40px)]">
                    <Bot size={10} className="text-cyan-400 animate-pulse md:w-[12px] md:h-[12px]" />
                    <span className="text-[8px] md:text-[10px] font-bold text-cyan-300 uppercase tracking-wider">AI Pick</span>
                </div>
            )}

            {/* تصغير أقصى ارتفاع للصورة في الموبايل لـ 140px عشان متتفعصش على النصوص */}
            <div className="relative w-full h-full max-h-[140px] md:max-h-[220px] md:[transform:translateZ(60px)]">
                {product.image_url ? (
                    <Image
                        src={product.image_url}
                        alt={product.name}
                        fill
                        sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
                        priority={priority}
                        className="object-contain drop-shadow-[0_15px_30px_rgba(0,0,0,0.6)] transition-transform duration-700 ease-out md:group-hover:scale-110 md:group-hover:-translate-y-4"
                    />
                ) : (
                    <div className="flex items-center justify-center w-full h-full text-white/10">
                        <ScanLine size={36} className="md:w-[48px] md:h-[48px]" />
                    </div>
                )}
            </div>
        </div>

        {/* تعديل مقاسات النصوص والمسافات السفلية لضمان عدم خروجها عن الكارت */}
        <div className="relative w-full bg-[#080808]/95 backdrop-blur-md md:backdrop-blur-xl border-t border-white/5 p-3 md:p-5 flex flex-col justify-between transition-colors duration-500 md:group-hover:bg-[#0a0a0a] md:[transform:translateZ(20px)]">
            <div className="mb-2 md:mb-3">
                <div className="w-full mb-1">
                    <h3 className="w-full text-[10px] md:text-sm font-medium text-white/90 leading-snug break-words font-sans">
                        {product.name}
                    </h3>
                </div>
                <p className="text-[7px] md:text-[9px] text-gray-400 font-sans leading-relaxed line-clamp-3 mt-1">
                    {product.description || "Specifications classified. High-performance unit ready for deployment."}
                </p>
            </div>

            <div className="mt-auto">
                <div className="flex items-center justify-between w-full mb-2 md:mb-3">
                   <span className="text-[10px] md:text-[10px] text-gray-600 uppercase font-bold">Price</span>
                   <span className="text-base md:text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-500" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                       ${safePrice}
                   </span>
               </div>

               <AnimatePresence mode="wait">
                    {isAdded ? (
                        <motion.button
                            key="added"
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                            className="w-full py-1.5 md:py-2.5 rounded-lg md:rounded-xl bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 font-bold text-[9px] md:text-[10px] uppercase tracking-widest flex items-center justify-center gap-2"
                        >
                            <Check size={14} className="text-cyan-300" /> Uplinked
                        </motion.button>
                    ) : (
                        <div className="flex gap-2 h-8 md:h-10">
                            <motion.button 
                                id={uniqueBtnId} key="add" onClick={handleAddToCart} whileTap={{ scale: 0.95 }}
                                className="flex-1 rounded-lg md:rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 md:hover:bg-cyan-500 md:hover:text-black font-bold text-[8px] md:text-[10px] tracking-widest flex items-center justify-center gap-1.5 md:gap-2 transition-all duration-300"
                            >
                                <ShoppingBag size={12} className="md:w-[14px] md:h-[14px]" /> 
                                <span>order with air</span>
                            </motion.button>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
      </motion.div>
    </motion.div>
  );
};
