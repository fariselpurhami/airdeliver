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
import { AirSparkles } from '@/components/ui/AirSparkles';
import { AlertTriangle, ShoppingBag, Zap, Layers, ChevronLeft, ChevronRight, Activity, BadgeCheck } from 'lucide-react';
import Image from 'next/image';
import { MobileHomeFloatingCards } from '@/components/hero/MobileHomeFloatingCards';
import { FloatingHeroCards, HERO_STAGE_CLASSES } from '@/components/hero/FloatingHeroCards';
import { DemoImageAttribution } from '@/components/products/DemoImageAttribution';
import { CatalogImage } from '@/components/products/CatalogImage';
import dynamic from 'next/dynamic';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import AIChatOverlay from '@/components/ai/AIChatOverlay';

import { AISecuredOrdersBadge } from '@/components/hero/AISecuredOrdersBadge';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const formatCurrency = (value: number | string | undefined | null): string => {
    if (value === undefined || value === null) return '0.00';
    const num = Number(value);
    return isNaN(num) ? '0.00' : num.toFixed(2);
};

const CATEGORIES = ["ALL", "ELECTRONICS", "FASHION", "BEAUTY", "ESSENTIALS"];
const ITEMS_PER_PAGE = 24;

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

const AICatalogHero = React.memo(() => {
    const { setOverlayVisible } = useAIOrderingStore();
    
    const messages = useAIOrderingStore((state) => state.messages);
    const cartItemsCount = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        const cartContent = lastCartMessage?.content as { items?: unknown[] } | undefined;
        return cartContent?.items?.length || 0;
    }, [messages]);

    return (
        <section className={`${HERO_STAGE_CLASSES} max-lg:min-h-[100svh] max-lg:pt-28 max-lg:pb-16`} data-hero-stage="products">
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
                <div className="w-[80vw] lg:w-[40vw] h-[80vw] lg:h-[40vw] bg-cyan-600/15 lg:bg-cyan-600/10 blur-[100px] lg:blur-[150px] rounded-full mix-blend-screen" />
                <div className="absolute w-[60vw] lg:w-[30vw] h-[60vw] lg:h-[30vw] bg-purple-600/15 lg:bg-purple-600/10 blur-[80px] lg:blur-[120px] rounded-full mix-blend-screen translate-x-1/4 -translate-y-1/4" />
            </div>

            <div className="hidden lg:contents"><FloatingHeroCards /></div>
            <div className="absolute inset-x-5 top-28 bottom-16 lg:hidden" data-mobile-catalog-distribution><MobileHomeFloatingCards /></div>

            <div className="relative z-30 w-full max-w-3xl lg:max-w-[48%] mx-auto px-4 sm:px-6 text-center">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(13,13,12,0.95)_0%,rgba(13,13,12,0.7)_40%,transparent_80%)] lg:hidden pointer-events-none -z-10" />

                <AISecuredOrdersBadge />
                
                <h1 className="text-4xl sm:text-6xl lg:text-[clamp(36px,4.4vw,76px)] font-black uppercase tracking-tighter mb-4 sm:mb-6 leading-[1.05] sm:leading-[0.95] drop-shadow-2xl relative z-10" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    The <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-gray-500 drop-shadow-[0_0_40px_rgba(255,255,255,0.15)]">
                        Autonomous
                    </span><br/>
                    Catalog
                </h1>
                
                <p className="max-w-xs sm:max-w-lg mx-auto text-xs sm:text-base md:text-lg text-gray-300 font-light leading-relaxed mb-10 sm:mb-12 drop-shadow-md relative z-10">
                    Don't search. Just ask.
                </p>

                <div className="w-full max-w-xl mx-auto relative group cursor-pointer z-10" onClick={() => setOverlayVisible(true)}> 
                    {/* تأثير الخلفية الملونة */}
                    <div className={`absolute -inset-[1px] rounded-[73px] blur-md transition-all duration-1000 -z-10 ${cartItemsCount > 0 ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 opacity-100' : 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 opacity-70 group-hover:opacity-100 group-hover:blur-xl'}`} />
                    
                    <motion.div
                        animate={
                            cartItemsCount > 0 
                                ? { 
                                    y: [0, -6, 0], 
                                    boxShadow: [
                                        "0px 0px 40px rgba(0,0,0,0.8)", 
                                        "0px 10px 40px rgba(6,182,212,0.3)", 
                                        "0px 0px 40px rgba(0,0,0,0.8)"
                                    ] 
                                } 
                                : { y: 0, boxShadow: "0px 0px 40px rgba(0,0,0,0.8)" }
                        }
                        transition={
                            cartItemsCount > 0 
                                ? { duration: 3, repeat: Infinity, ease: "easeInOut" } 
                                : {}
                        }
                        className="relative flex items-center p-1.5 sm:p-2 rounded-[73px] bg-[#0D0D0C]/90 lg:bg-[#0D0D0C]/80 border border-white/15 backdrop-blur-3xl transition-all duration-500 hover:border-cyan-500/50 hover:bg-[#0D0D0C]"
                    >
                        <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-white/5 text-cyan-400 group-hover:scale-105 transition-transform duration-500 shrink-0 border border-white/5 relative">
                            <AirSparkles className="h-6 w-6 text-purple-400 sm:h-7 sm:w-7" />
                            
                            {/* نقطة الإشعار برقم المنتجات (Badge) */}
                            {cartItemsCount > 0 && (
                                <motion.span 
                                    initial={{ scale: 0 }} 
                                    animate={{ scale: 1 }}
                                    className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-black text-[#050505] shadow-[0_0_10px_rgba(6,182,212,0.8)]"
                                >
                                    {cartItemsCount}
                                </motion.span>
                            )}
                        </div>

                        <div className="flex-1 px-3 sm:px-4 min-w-0 text-left">
                            <p className={`text-[11px] sm:text-sm md:text-base transition-colors ${cartItemsCount > 0 ? 'text-cyan-200 font-medium' : 'text-gray-300 font-light truncate group-hover:text-white'}`}>
                                {cartItemsCount > 0 
                                    ? "Your order is ready. Tap to review..." 
                                    : "I need a black leather jacket..."}
                            </p>
                        </div>

                        <button className="flex items-center justify-center gap-2 px-4 sm:px-6 py-3 sm:py-3.5 rounded-full bg-white text-black font-bold text-[10px] sm:text-xs hover:bg-cyan-50 transition-colors shrink-0 shadow-lg shadow-white/10 tracking-widest whitespace-nowrap">
                            <span className="hidden sm:inline">{cartItemsCount > 0 ? "Confirm Order!" : "order with air"}</span>
                            <span className="sm:hidden">{cartItemsCount > 0 ? "Confirm Order!" : "order with air"}</span>
                        </button>
                    </motion.div>
                </div>
            </div>
        </section>
    );
});
AICatalogHero.displayName = 'AICatalogHero';

const AlgorithmicPick = React.memo(({ onOpen }: { onOpen: (product: Product) => void }) => {
    const { status } = useSession();
    const { data: recommendationsData, error, isLoading } = useSWR<Product>(
        status === 'authenticated' ? `/products/featured-recommendation` : null, 
        fetcher, 
        { revalidateOnFocus: false }
    );

    if (isLoading || error || !recommendationsData || status !== 'authenticated') return null;

    return (
        <section className="mb-10 md:mb-20 relative">
            <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} 
                className="relative flex flex-row items-stretch bg-[#0A0A0A]/80 backdrop-blur-2xl border border-white/10 rounded-2xl md:rounded-[32px] overflow-hidden group min-h-[160px] md:min-h-[350px]"
            >
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                
                <div className="w-[45%] md:w-1/2 relative flex items-center justify-center p-4 md:p-10 bg-white/[0.02]">
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
                    <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }} className="relative z-10 w-full h-full max-w-sm">
                        <CatalogImage product={recommendationsData} src={recommendationsData.image_url || '/images/default.jpeg'} alt={recommendationsData.name} fill className="object-contain drop-shadow-2xl" priority />
                    </motion.div>
                </div>

                <div className="w-[55%] md:w-1/2 p-4 md:p-12 flex flex-col justify-center relative z-10 border-l border-white/5">
                    <div className="flex flex-wrap items-center gap-1.5 md:gap-3 mb-2 md:mb-6">
                        <div className="flex items-center gap-1 md:gap-2 px-2 md:px-3 py-0.5 md:py-1 rounded-full bg-purple-500/10 border border-purple-500/20">
                            <BadgeCheck className="w-2.5 h-2.5 md:w-4 md:h-4 text-purple-400" />
                            <span className="text-[7px] md:text-[10px] font-mono text-purple-300 uppercase tracking-widest whitespace-nowrap">SELECTED FOR YOU</span>
                        </div>
                    </div>
                    
                    <DemoImageAttribution product={recommendationsData} />
                    <h2 className="text-sm md:text-4xl font-bold text-white mb-1.5 md:mb-4 leading-tight line-clamp-2">{recommendationsData.name}</h2>
                    <p className="text-[9px] md:text-sm text-gray-400 mb-3 md:mb-8 leading-relaxed max-w-md line-clamp-2 md:line-clamp-none">{recommendationsData.description}</p>
                    
                    <div className="flex flex-row items-center justify-between gap-2 md:gap-6 mt-auto">
                        <div className="flex flex-col">
                            <span className="text-[7px] md:text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-0.5 md:mb-1">Cost</span>
                            <span className="text-sm md:text-2xl font-bold text-white font-mono">${formatCurrency(recommendationsData.price)}</span>
                        </div>
                        <button 
                            onClick={() => onOpen(recommendationsData)}
                            className="flex-1 max-w-[80px] md:max-w-none py-2 md:py-4 bg-white text-black font-bold uppercase tracking-widest text-[8px] md:text-xs rounded-lg md:rounded-xl hover:bg-cyan-400 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.1)] text-center"
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
    const setOverlayVisible = useAIOrderingStore((state) => state.setOverlayVisible);
    const [isAdded, setIsAdded] = useState(false);
    const uniqueBtnId = `add-to-manifest-${product.id}`; 

    const handleAddToCart = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        addProductById(product, uniqueBtnId); 
        setOverlayVisible(true);
        setIsAdded(true);
        const timer = setTimeout(() => setIsAdded(false), 2000);
        return () => clearTimeout(timer);
    }, [product, uniqueBtnId, addProductById]);

    return (
        <motion.div
            layoutId={`product-card-${product.id}`}
            variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
            className="group relative w-full h-full rounded-2xl md:rounded-[24px] bg-[#0A0A0A] border border-white/10 overflow-hidden hover:border-cyan-500/40 transition-all duration-500 cursor-pointer flex flex-col shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
            onClick={() => onOpen(product)}
        >
            <div className="absolute top-2 left-2 md:top-4 md:left-4 z-20">
                {product.stock_status && (
                    <div className="px-1.5 md:px-2 py-0.5 md:py-1 bg-green-500/10 border border-green-500/20 rounded text-[7px] md:text-[9px] text-green-400 font-mono tracking-widest uppercase flex items-center gap-1 backdrop-blur-md">
                        <span className="w-1 md:w-1.5 h-1 md:h-1.5 bg-green-500 rounded-full" />
                        In Hub
                    </div>
                )}
            </div>

            <div className="relative w-full aspect-[4/3] p-3 md:p-6 bg-white/[0.02] flex items-center justify-center">
                <motion.div className="relative w-full h-full" whileHover={{ scale: 1.05 }} transition={{ type: "spring", stiffness: 400, damping: 30 }}>
                    <CatalogImage product={product} id={`product-img-${product.id}`} src={product.image_url || '/images/default.jpeg'} alt={product.name} fill className="object-contain drop-shadow-xl" sizes="(max-width: 768px) 50vw, 25vw" loading="lazy" />
                </motion.div>
            </div>
            
            <div className="relative p-3 md:p-5 flex flex-col flex-grow border-t border-white/5 bg-[#0D0D0C]">
                <DemoImageAttribution product={product} />
                <h3 className="text-[11px] md:text-sm font-bold text-gray-100 mb-0.5 md:mb-1 group-hover:text-cyan-400 transition-colors line-clamp-2">{product.name}</h3>
                <p className="text-[9px] md:text-xs text-gray-500 line-clamp-3 mb-2 md:mb-4">{product.description}</p>
                
                <div className="flex items-center justify-between mt-auto pt-1.5 md:pt-2">
                    <span className="text-sm md:text-lg font-bold text-white font-mono">${formatCurrency(product.price)}</span>
                    
                    <AnimatePresence mode="wait">
                        {isAdded ? (
                            <motion.button key="added" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="h-7 w-7 md:h-10 md:px-4 rounded-lg md:rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center gap-2 border border-cyan-500/30">
                                <Zap size={12} className="md:w-3.5 md:h-3.5 fill-cyan-400" />
                            </motion.button>
                        ) : (
                            <motion.button id={uniqueBtnId} key="add" onClick={handleAddToCart} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="h-7 w-7 md:w-auto md:h-10 md:px-4 rounded-lg md:rounded-xl bg-white text-black font-bold text-[9px] md:text-[10px] tracking-widest flex items-center justify-center gap-1.5 md:gap-2 hover:bg-cyan-400 transition-colors shadow-lg">
                                <AirSparkles className="h-3 w-3 text-purple-500 md:h-3.5 md:w-3.5" />  <span className="hidden md:inline">order with air</span>
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
    <motion.div variants={{ visible: { transition: { staggerChildren: 0.05 } } }} initial="hidden" animate="visible" className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-6">
        {products.map(product => <ProductCard key={product.id} product={product} onOpen={onOpen} />)}
    </motion.div>
));
ProductList.displayName = 'ProductList';

const Pagination = React.memo(({ page, setPage, hasMore }: { page: number, setPage: (p: number) => void, hasMore: boolean }) => (
    <div className="flex justify-center items-center gap-4 md:gap-6 mt-10 md:mt-16 pt-6 md:pt-8">
        <button disabled={page === 1} onClick={() => { setPage(page - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="p-2.5 md:p-3 rounded-full bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <ChevronLeft size={16} className="md:w-5 md:h-5" />
        </button>
        <span className="font-mono text-gray-400 text-[10px] md:text-xs tracking-[0.2em] uppercase">Page <span className="text-white font-bold">{page.toString().padStart(2, '0')}</span></span>
        <button disabled={!hasMore} onClick={() => { setPage(page + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="p-2.5 md:p-3 rounded-full bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <ChevronRight size={16} className="md:w-5 md:h-5" />
        </button>
    </div>
));
Pagination.displayName = 'Pagination';

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

                <div className="max-w-7xl mx-auto px-4 sm:px-6 pb-24 md:pb-32">
                    <AlgorithmicPick onOpen={handleOpen} />

                    <div className="flex flex-row items-center justify-between mb-6 md:mb-8 px-4 md:px-5 py-3 md:py-4 gap-4 sticky top-16 md:top-20 z-30 bg-[#0D0D0C]/90 backdrop-blur-xl rounded-[73px] border border-white/8">
                        <div className="flex items-center gap-2 md:gap-3 shrink-0">
                            <Layers className="text-cyan-500 w-4 h-4 md:w-5 md:h-5" />
                            <h2 className="text-xs md:text-lg font-extralight text-white uppercase tracking-widest" style={{ fontFamily: "'Exo 2', sans-serif" }}
                            >
                                 Categories
                            </h2>
                        </div>

                        <div className="flex flex-row gap-2 overflow-x-auto no-scrollbar scroll-smooth whitespace-nowrap pl-2 mask-linear-fade">
                             {CATEGORIES.map((cat) => (
                                 <button
                                    key={cat} onClick={() => handleCategoryChange(cat)}
                                    className={`shrink-0 px-3 md:px-4 py-1.5 md:py-2 rounded-full border text-[8px] md:text-[10px] font-bold uppercase tracking-widest transition-all duration-300 ${
                                        category === cat ? 'bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.2)]' : 'bg-transparent border-white/10 text-gray-500 hover:border-white/30 hover:text-white'
                                    }`}
                                 >
                                     {cat}
                                 </button>
                             ))}
                        </div>
                    </div>

                    {error ? (
                        <div className="text-center py-12 md:py-20 flex flex-col items-center justify-center">
                            <AlertTriangle className="text-red-500 mb-3 md:mb-4 w-8 h-8 md:w-12 md:h-12" />
                            <p className="text-red-400 font-mono text-xs md:text-sm uppercase tracking-widest">Products could not be loaded. Please check your connection and try again.</p>
                        </div>
                    ) : isLoading && !productsData ? (
                        <div className="flex justify-center py-12 md:py-20"><div className="w-6 h-6 md:w-8 md:h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" /></div>
                    ) : products.length > 0 ? (
                        <>
                            <ProductList products={products} onOpen={handleOpen} />
                            <Pagination page={page} setPage={setPage} hasMore={hasMore} />
                        </>
                    ) : (
                        <div className="text-center py-20 md:py-32 border border-white/5 rounded-2xl md:rounded-3xl bg-white/[0.02] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
                            <p className="text-gray-500 font-mono uppercase tracking-widest text-xs md:text-sm">No products matched this view. Try a different search or filter.</p>
                        </div>
                    )}
                </div>
            </main>

            <AnimatePresence>
                {selectedProduct && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={handleClose} className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-2xl flex justify-center items-center p-4 overflow-hidden">
                        <div onClick={(e) => e.stopPropagation()} className="w-full flex items-center justify-center">
                            <ProductDetailsCard product={selectedProduct} onClose={handleClose} />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            <AIChatOverlay isOpen={isOverlayVisible} onClose={() => setOverlayVisible(false)} />
        </div>
    );
}
