// apps/web/app/(main)/products/page.tsx

'use client';

import React, { useState, Suspense, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence, useScroll, useTransform, useSpring } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { type Product } from '@/types';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AlertTriangle, Bot, ShoppingBag, Zap, Layers, ChevronLeft, ChevronRight, Activity, Crosshair, ArrowRight, Package } from 'lucide-react';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay';

// ============================================================================
// --- INFRASTRUCTURE & UTILS ---
// ============================================================================

const fetcher = (url: string) => api.get(url).then(res => res.data);

const formatCurrency = (value: number | string | undefined | null): string => {
    if (value === undefined || value === null) return '0.00';
    const num = Number(value);
    return isNaN(num) ? '0.00' : num.toFixed(2);
};

const CATEGORIES = ["ALL", "ELECTRONICS", "FASHION", "BEAUTY", "ESSENTIALS"];
const ITEMS_PER_PAGE = 24;

// ============================================================================
// --- 1. WEBGL BACKGROUND: NEURAL NETWORK GRID ---
// ============================================================================
const NeuralGrid = React.memo(() => {
    const groupRef = useRef<THREE.Group>(null!);
    
    const positions = useMemo(() => {
        const count = 4000;
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i * 3] = (Math.random() - 0.5) * 40;
            pos[i * 3 + 1] = (Math.random() - 0.5) * 40;
            pos[i * 3 + 2] = (Math.random() - 0.5) * 20 - 10;
        }
        return pos;
    }, []);

    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.elapsedTime * 0.015;
            groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.5;
        }
    });

    return (
        <group ref={groupRef}>
            <Points positions={positions} stride={3} frustumCulled={false}>
                <PointMaterial transparent color="#00C6FF" size={0.03} sizeAttenuation={true} depthWrite={false} opacity={0.3} />
            </Points>
        </group>
    );
});
NeuralGrid.displayName = 'NeuralGrid';

const DynamicBackground = dynamic(() => Promise.resolve(NeuralGrid), { ssr: false, loading: () => null });

// ============================================================================
// --- 2. IMMERSIVE SPATIAL HERO SECTION ---
// ============================================================================

// Component for the Floating Spatial Cards (Fully Responsive & GPU Optimized)
const FloatingCategoryCard = React.memo(({ 
    title, image, category, delay, yOffset, colorCls, rotation, sizeClasses 
}: { 
    title: string, image: string, category: string, delay: number, yOffset: any, colorCls: string, rotation: number, sizeClasses: string 
}) => (
    // Outer Layer: Handles Scroll Parallax only
    <motion.div 
        style={{ y: yOffset }}
        className={`absolute z-0 ${sizeClasses} will-change-transform`}
        initial={{ opacity: 0, scale: 0.8, rotate: rotation + 10 }}
        animate={{ opacity: 1, scale: 1, rotate: rotation }}
        transition={{ 
            opacity: { duration: 1, delay },
            scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
        }}
    >
        {/* Inner Layer: Handles Continuous Floating Animation only (Prevents CSS collision) */}
        <motion.div
            animate={{ y: [0, -15, 0] }}
            transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
            className="w-full h-full will-change-transform"
            style={{ transform: "translateZ(0)" }} // Hardware Acceleration
        >
            <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] lg:shadow-[0_30px_60px_rgba(0,0,0,0.8)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 ${colorCls}`}>
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
                <Image src={image} alt={category} fill sizes="(max-width: 768px) 30vw, 20vw" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
                
                <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
                    <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.2em] lg:tracking-[0.3em] opacity-70 text-white mix-blend-overlay line-clamp-1">{category}</span>
                    <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight line-clamp-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
                </div>
                
                {/* Holographic Edge Glow */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
            </div>
        </motion.div>
    </motion.div>
));
FloatingCategoryCard.displayName = 'FloatingCategoryCard';

const AICatalogHero = React.memo(() => {
    const { scrollY } = useScroll();
    const { setOverlayVisible } = useAIOrderingStore();
    // Physics-based smoothing for the scroll to eliminate stutter/jank on mobile devices
    const smoothScrollY = useSpring(scrollY, {
        damping: 30,
        stiffness: 150,
        mass: 0.5
    });
    
    // Parallax logic for depth using the smoothed scroll value
    const yFast = useTransform(smoothScrollY, [0, 800], [0, -180]);
    const yMedium = useTransform(smoothScrollY, [0, 800], [0, -100]);
    const ySlow = useTransform(smoothScrollY, [0, 800], [0, -40]);

    return (
        <section className="relative w-full min-h-[85vh] flex flex-col items-center justify-center pt-32 pb-16 overflow-hidden perspective-1000">
            {/* Ambient Lighting */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
                <div className="w-[80vw] lg:w-[40vw] h-[80vw] lg:h-[40vw] bg-cyan-600/15 lg:bg-cyan-600/10 blur-[100px] lg:blur-[150px] rounded-full mix-blend-screen" />
                <div className="absolute w-[60vw] lg:w-[30vw] h-[60vw] lg:h-[30vw] bg-purple-600/15 lg:bg-purple-600/10 blur-[80px] lg:blur-[120px] rounded-full mix-blend-screen translate-x-1/4 -translate-y-1/4" />
            </div>

            {/* --- FLOATING SPATIAL CARDS (Mobile + Desktop Optimized) --- */}
            {/* Left Side */}
            <FloatingCategoryCard sizeClasses="w-24 h-32 md:w-40 md:h-52 lg:w-56 lg:h-72 top-[8%] lg:top-[10%] left-[2%] lg:left-[8%]" yOffset={yFast} delay={0.1} rotation={-8} category="Neural Tech" title="Galaxy Buds" image="https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-cyan-500/20 text-cyan-400" />
            <FloatingCategoryCard sizeClasses="w-20 h-28 md:w-32 md:h-44 lg:w-48 lg:h-60 top-[40%] lg:top-[45%] -left-[5%] lg:left-[2%]" yOffset={ySlow} delay={0.3} rotation={-4} category="Aesthetic" title="Dyson" image="https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-pink-500/20 text-pink-400" />
            <FloatingCategoryCard sizeClasses="w-24 h-28 md:w-36 md:h-48 lg:w-52 lg:h-64 top-[70%] lg:top-[65%] left-[4%] lg:left-[12%]" yOffset={yMedium} delay={0.5} rotation={6} category="Wearables" title="Apple Watch Ultra" image="https://images.unsplash.com/photo-1590688560938-57c514814ddb?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-amber-500/20 text-amber-400" />
            
            {/* Right Side */}
            <FloatingCategoryCard sizeClasses="w-24 h-32 md:w-40 md:h-52 lg:w-56 lg:h-72 top-[12%] lg:top-[15%] right-[2%] lg:right-[8%]" yOffset={yMedium} delay={0.2} rotation={8} category="Bags" title="Leather Handbag" image="https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-purple-500/20 text-purple-400" />
            <FloatingCategoryCard sizeClasses="w-20 h-28 md:w-32 md:h-44 lg:w-48 lg:h-64 top-[45%] lg:top-[50%] -right-[5%] lg:right-[3%]" yOffset={yFast} delay={0.4} rotation={4} category="Electronics" title="Iphone 17 pro max" image="https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-emerald-500/20 text-emerald-400" />
            <FloatingCategoryCard sizeClasses="w-24 h-24 md:w-36 md:h-40 lg:w-52 lg:h-56 top-[75%] lg:top-[70%] right-[4%] lg:right-[15%]" yOffset={ySlow} delay={0.6} rotation={-6} category="Fashion" title="Zara" image="https://images.unsplash.com/photo-1551028719-00167b16eac5?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-blue-500/20 text-blue-400" />


            {/* --- CORE CONTENT (Static in normal flow - Opacity transform removed) --- */}
            <div className="relative z-20 w-full max-w-3xl mx-auto px-4 sm:px-6 text-center mt-10 lg:mt-0">
                {/* Mobile Readability Shield */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(13,13,12,0.95)_0%,rgba(13,13,12,0.7)_40%,transparent_80%)] lg:hidden pointer-events-none -z-10" />

                <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-[#0D0D0C]/80 border border-white/10 backdrop-blur-xl mb-6 sm:mb-8 shadow-2xl relative z-10">
                    <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
                    <span className="text-[8px] sm:text-[10px] font-mono text-gray-300 uppercase tracking-[0.2em]">AI-SECURED ORDERS</span>
                </div>
                
                <h1 className="text-4xl sm:text-6xl md:text-8xl font-black uppercase tracking-tighter mb-4 sm:mb-6 leading-[1.05] sm:leading-[0.95] drop-shadow-2xl relative z-10" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    The <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-gray-500 drop-shadow-[0_0_40px_rgba(255,255,255,0.15)]">
                        Autonomous
                    </span><br/>
                    Catalog
                </h1>
                
                <p className="max-w-xs sm:max-w-lg mx-auto text-xs sm:text-base md:text-lg text-gray-300 font-light leading-relaxed mb-10 sm:mb-12 drop-shadow-md relative z-10">
                    Don't search. Just ask. airdeliverOS scans thousands of products and secures them for instant air-drop.
                </p>

                {/* AI Interactive Trigger */}
                <div className="w-full max-w-xl mx-auto relative group cursor-pointer z-10" onClick={() => setOverlayVisible(true)}> 
                    <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/30 to-purple-500/30 rounded-[73px] blur-md opacity-70 group-hover:opacity-100 group-hover:blur-xl transition duration-500 -z-10" />
                    
                    <div className="relative flex items-center p-1.5 sm:p-2 rounded-[73px] bg-[#0D0D0C]/90 lg:bg-[#0D0D0C]/80 border border-white/15 backdrop-blur-3xl shadow-[0_0_40px_rgba(0,0,0,0.8)] transition-all duration-500 hover:border-cyan-500/50 hover:bg-[#0D0D0C]">
                        <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-white/5 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0 border border-white/5">
                            <Bot size={18} className="sm:w-[22px] sm:h-[22px]" strokeWidth={1.5} />
                        </div>

                        <div className="flex-1 px-3 sm:px-4 min-w-0 text-left">
                            <p className="text-gray-300 text-xs sm:text-sm md:text-base font-light truncate group-hover:text-white transition-colors">
                                I need a black leather jacket...
                            </p>
                        </div>

                        <button className="flex items-center justify-center gap-2 px-4 sm:px-6 py-3 sm:py-3.5 rounded-full bg-white text-black font-bold text-[10px] sm:text-xs hover:bg-cyan-50 transition-colors shrink-0 shadow-lg shadow-white/10 tracking-widest">
                            <span className="hidden sm:inline">order with air</span>
                            <span className="sm:hidden">order with air</span>
                        </button>
                    </div>
                </div>
            </div>
        </section>
    );
});
AICatalogHero.displayName = 'AICatalogHero';

// ============================================================================
// --- 3. NEURAL MATCH / FEATURED ITEM ---
// ============================================================================
const AlgorithmicPick = React.memo(({ onOpen }: { onOpen: (product: Product) => void }) => {
    const { status } = useSession();
    const { data: recommendationsData, error, isLoading } = useSWR<Product>(
        status === 'authenticated' ? `/products/featured-recommendation` : null, 
        fetcher, 
        { revalidateOnFocus: false }
    );

    if (isLoading || error || !recommendationsData || status !== 'authenticated') return null;

    return (
        <section className="mb-20 relative">
            <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} 
                className="relative flex flex-col lg:flex-row items-stretch bg-[#0A0A0A]/80 backdrop-blur-2xl border border-white/10 rounded-[32px] overflow-hidden group"
            >
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                
                <div className="w-full lg:w-1/2 relative min-h-[350px] flex items-center justify-center p-10 bg-white/[0.02]">
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
                    <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }} className="relative z-10 w-full h-full max-w-sm">
                        <Image src={recommendationsData.image_url || '/images/default.jpeg'} alt={recommendationsData.name} fill className="object-contain drop-shadow-2xl" priority />
                    </motion.div>
                </div>

                <div className="w-full lg:w-1/2 p-10 lg:p-12 flex flex-col justify-center relative z-10 border-l border-white/5">
                    <div className="flex flex-wrap items-center gap-3 mb-6">
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20">
                            <Crosshair className="w-4 h-4 text-purple-400" />
                            <span className="text-[10px] font-mono text-purple-300 uppercase tracking-widest">99.8% Neural Match</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                            <Activity className="w-4 h-4 text-green-400" />
                            <span className="text-[10px] font-mono text-green-300 uppercase tracking-widest">Ready for Air-Drop</span>
                        </div>
                    </div>
                    
                    <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4 leading-tight">{recommendationsData.name}</h2>
                    <p className="text-sm text-gray-400 mb-8 leading-relaxed max-w-md">{recommendationsData.description}</p>
                    
                    <div className="flex flex-wrap items-center gap-6 mt-auto">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-1">Total Cost</span>
                            <span className="text-2xl font-bold text-white font-mono">${formatCurrency(recommendationsData.price)}</span>
                        </div>
                        <button 
                            onClick={() => onOpen(recommendationsData)}
                            className="flex-1 py-4 bg-white text-black font-bold uppercase tracking-widest text-xs rounded-xl hover:bg-cyan-400 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                        >
                            View
                        </button>
                    </div>
                </div>
            </motion.div>
        </section>
    );
});
AlgorithmicPick.displayName = 'AlgorithmicPick';

// ============================================================================
// --- 4. CORE UI COMPONENTS (Stateless & Pure) ---
// ============================================================================
const PageFlyToCartAnimator = React.memo(() => {
  const flyQueue = useAIOrderingStore((state) => state.flyQueue);
  const removeFlyItem = useAIOrderingStore((state) => state.removeFlyItem);

  return (
    <AnimatePresence>
      {flyQueue.map((item) => {
          const el = document.getElementById(item.startElementId);
          const startRect = el ? el.getBoundingClientRect() : { top: 0, left: 0, width: 0, height: 0 };
          if (!startRect.width) return null;

          return (
            <motion.div
              key={item.animationId} 
              className="fixed z-[9999] rounded-xl overflow-hidden border border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.5)] pointer-events-none bg-[#0D0D0C]"
              initial={{ top: startRect.top, left: startRect.left, width: startRect.width, height: startRect.height, opacity: 1, rotate: 0 }}
              animate={{ top: "-20vh", left: startRect.left, width: 10, height: 10, opacity: 0, rotate: 0, scale: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} 
              onAnimationComplete={() => removeFlyItem(item.animationId)}
            >
              <Image 
                src={item.image} 
                alt="" 
                fill 
                sizes="100px"
                className="object-cover opacity-80" 
              />
            </motion.div>
          );
      })}
    </AnimatePresence>
  );
});
PageFlyToCartAnimator.displayName = 'PageFlyToCartAnimator';

const ProductCard = React.memo(({ product, onOpen }: { product: Product, onOpen: (product: Product) => void }) => {
    const addProductById = useAIOrderingStore((state) => state.addProductById);
    const [isAdded, setIsAdded] = useState(false);
    const uniqueBtnId = `add-to-manifest-${product.id}`; 

    const handleAddToCart = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        addProductById(product, uniqueBtnId); 
        setIsAdded(true);
        const timer = setTimeout(() => setIsAdded(false), 2000);
        return () => clearTimeout(timer);
    }, [product, uniqueBtnId, addProductById]);

    return (
        <motion.div
            layoutId={`product-card-${product.id}`}
            variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
            className="group relative w-full h-full rounded-[24px] bg-[#0A0A0A] border border-white/10 overflow-hidden hover:border-cyan-500/40 transition-all duration-500 cursor-pointer flex flex-col shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
            onClick={() => onOpen(product)}
        >
            <div className="absolute top-4 left-4 z-20">
                {product.stock_status ? (
                    <div className="px-2 py-1 bg-green-500/10 border border-green-500/20 rounded text-[9px] text-green-400 font-mono tracking-widest uppercase flex items-center gap-1.5 backdrop-blur-md">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                        In Local Hub
                    </div>
                ) : (
                    <div className="px-2 py-1 bg-gray-500/10 border border-gray-500/20 rounded text-[9px] text-gray-400 font-mono tracking-widest uppercase flex items-center gap-1.5 backdrop-blur-md">
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full" />
                        Sourcing
                    </div>
                )}
            </div>

            <div className="relative w-full aspect-[4/3] p-6 bg-white/[0.02] flex items-center justify-center">
                <motion.div className="relative w-full h-full" whileHover={{ scale: 1.05 }} transition={{ type: "spring", stiffness: 400, damping: 30 }}>
                    <Image id={`product-img-${product.id}`} src={product.image_url || '/images/default.jpeg'} alt={product.name} fill className="object-contain drop-shadow-xl" sizes="(max-width: 768px) 100vw, 33vw" loading="lazy" />
                </motion.div>
            </div>
            
            <div className="relative p-5 flex flex-col flex-grow border-t border-white/5 bg-[#0D0D0C]">
                <h3 className="text-sm font-bold text-gray-100 mb-1 group-hover:text-cyan-400 transition-colors line-clamp-1">{product.name}</h3>
                <p className="text-xs text-gray-500 line-clamp-1 mb-4">{product.description}</p>
                
                <div className="flex items-end justify-between mt-auto pt-2">
                    <span className="text-lg font-bold text-white font-mono">${formatCurrency(product.price)}</span>
                    
                    <AnimatePresence mode="wait">
                        {isAdded ? (
                            <motion.button key="added" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="h-10 px-4 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center gap-2 border border-cyan-500/30">
                                <Zap size={14} className="fill-cyan-400" />
                            </motion.button>
                        ) : (
                            <motion.button id={uniqueBtnId} key="add" onClick={handleAddToCart} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="h-10 px-4 rounded-xl bg-white text-black font-bold text-[10px] tracking-widest flex items-center justify-center gap-2 hover:bg-cyan-400 transition-colors shadow-lg">
                                <Bot size={14} /> order with air
                            </motion.button>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
});
ProductCard.displayName = 'ProductCard';

const ProductList = React.memo(({ products, onOpen }: { products: Product[], onOpen: (product: Product) => void }) => (
    <motion.div variants={{ visible: { transition: { staggerChildren: 0.05 } } }} initial="hidden" animate="visible" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map(product => <ProductCard key={product.id} product={product} onOpen={onOpen} />)}
    </motion.div>
));
ProductList.displayName = 'ProductList';

const Pagination = React.memo(({ page, setPage, hasMore }: { page: number, setPage: (p: number) => void, hasMore: boolean }) => (
    <div className="flex justify-center items-center gap-6 mt-16 pt-8">
        <button disabled={page === 1} onClick={() => { setPage(page - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="p-3 rounded-full bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <ChevronLeft size={20} />
        </button>
        <span className="font-mono text-gray-400 text-xs tracking-[0.2em] uppercase">Inventory Sector <span className="text-white font-bold">{page.toString().padStart(2, '0')}</span></span>
        <button disabled={!hasMore} onClick={() => { setPage(page + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="p-3 rounded-full bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <ChevronRight size={20} />
        </button>
    </div>
));
Pagination.displayName = 'Pagination';

// ============================================================================
// --- 5. PAGE ORCHESTRATOR ---
// ============================================================================
export default function ProductsPage() {
    const [page, setPage] = useState(1);
    const [category, setCategory] = useState("ALL");
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const { isOverlayVisible, setOverlayVisible } = useAIOrderingStore();

    const queryKey = `/products/?page=${page}&limit=${ITEMS_PER_PAGE}&category=${category !== 'ALL' ? category.toLowerCase() : ''}`;
    
    const { data: productsData, error, isLoading } = useSWR<Product[] | { items: Product[], total: number }>(
        queryKey, fetcher, { revalidateOnFocus: false, keepPreviousData: true }
    );

    const products = useMemo(() => {
        if (!productsData) return [];
        return Array.isArray(productsData) ? productsData : productsData.items || [];
    }, [productsData]);

    const hasMore = useMemo(() => products.length >= ITEMS_PER_PAGE, [products]);

    const handleOpen = useCallback((product: Product) => {
        setSelectedProduct(product);
        document.body.style.overflow = 'hidden';
    }, []);

    const handleClose = useCallback(() => {
        setSelectedProduct(null);
        document.body.style.overflow = '';
    }, []);

    const handleCategoryChange = useCallback((cat: string) => {
        setCategory(cat);
        setPage(1);
    }, []);

    return (
        <div className="min-h-screen w-full bg-[#0D0D0C] text-gray-100 overflow-x-hidden selection:bg-cyan-500/30">
            <div className="fixed inset-0 z-0 pointer-events-none">
                 <Canvas camera={{ position: [0, 0, 20], fov: 45 }} dpr={[1, 1.5]} gl={{ powerPreference: "high-performance", antialias: false, alpha: false }}>
                    <Suspense fallback={null}><DynamicBackground /></Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-t from-[#0D0D0C] via-transparent to-[#0D0D0C]/80" />
            </div>

            <PageFlyToCartAnimator />

            <main className="relative z-10">
                <AICatalogHero />

                <div className="max-w-7xl mx-auto px-6 pb-32">
                    <AlgorithmicPick onOpen={handleOpen} />

                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 pb-4 gap-6 sticky top-20 z-30 bg-[#0D0D0C]/90 backdrop-blur-xl rounded-b-2xl border-b border-white/5">
                        <div className="flex items-center gap-3">
                            <Layers className="text-cyan-500" size={20} />
                            <h2 className="text-lg font-bold text-white uppercase tracking-widest" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                Warehouse Manifest
                            </h2>
                        </div>

                        <div className="flex flex-wrap gap-2">
                             {CATEGORIES.map((cat) => (
                                 <button
                                    key={cat} onClick={() => handleCategoryChange(cat)}
                                    className={`px-4 py-2 rounded-full border text-[10px] font-bold uppercase tracking-widest transition-all duration-300 ${
                                        category === cat ? 'bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.2)]' : 'bg-transparent border-white/10 text-gray-500 hover:border-white/30 hover:text-white'
                                    }`}
                                 >
                                     {cat}
                                 </button>
                             ))}
                        </div>
                    </div>

                    {error ? (
                        <div className="text-center py-20 flex flex-col items-center justify-center">
                            <AlertTriangle className="text-red-500 mb-4 w-12 h-12" />
                            <p className="text-red-400 font-mono text-sm uppercase tracking-widest">Network Error: Unable to sync with warehouse</p>
                        </div>
                    ) : isLoading && !productsData ? (
                        <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" /></div>
                    ) : products.length > 0 ? (
                        <>
                            <ProductList products={products} onOpen={handleOpen} />
                            <Pagination page={page} setPage={setPage} hasMore={hasMore} />
                        </>
                    ) : (
                        <div className="text-center py-32 border border-white/5 rounded-3xl bg-white/[0.02] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
                            <p className="text-gray-500 font-mono uppercase tracking-widest text-sm">Inventory Depleted in this Sector.</p>
                        </div>
                    )}
                </div>
            </main>

            <AnimatePresence>
                {selectedProduct && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={handleClose} className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-2xl flex justify-center items-center p-4 overflow-hidden">
                        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-5xl shadow-[0_0_50px_rgba(0,0,0,0.8)] border border-white/10 rounded-[32px]">
                            <ProductDetailsCard product={selectedProduct} onClose={handleClose} />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* AIChatOverlay explicitly injected into DOM root to listen to Global State */}
            <AIChatOverlay isOpen={isOverlayVisible} onClose={() => setOverlayVisible(false)} />
        </div>
    );
}
