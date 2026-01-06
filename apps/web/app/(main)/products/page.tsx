//** apps/web/app/(main)/products/page.tsx **//

'use client';

import React, { useState, Suspense, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';
import { type Product } from '@/types';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AlertTriangle, Cpu, Eye, ShoppingBag, Zap, Tag, Layers, ScanLine, ChevronLeft, ChevronRight } from 'lucide-react';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

// --- ARCHITECTURAL UTILS: RESILIENCE LAYER ---
const fetcher = (url: string) => api.get(url).then(res => res.data);

// Safe Currency Formatter (Prevents the .toFixed crash)
const formatCurrency = (value: number | string | undefined | null): string => {
    if (value === undefined || value === null) return '0.00';
    const num = Number(value);
    // If NaN (Not a Number), return 0.00 safely
    return isNaN(num) ? '0.00' : num.toFixed(2);
};

const CATEGORIES = ["ALL", "FASHION", "BEAUTY", "ELECTRONICS", "ACCESSORIES"];
const ITEMS_PER_PAGE = 30;

// ============================================================================
// --- 1. PERFORMANCE CORE (Background Isolation) ---
// ============================================================================
const ProductsBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.set(
                Math.sin(time * 0.5) * 20,
                Math.cos(time * 0.5) * 20,
                Math.cos(time * 0.5) * 15
            );
        }
        if (light2Ref.current) {
            light2Ref.current.position.set(
                Math.sin(time * 0.3) * -20,
                Math.cos(time * 0.3) * -20,
                Math.sin(time * 0.3) * 10
            );
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 15, 50]} />
            <ambientLight intensity={0.8} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={300} color="#00C6FF" distance={50} />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={200} color="#7F00FF" distance={50} />
            <Stars radius={120} depth={60} count={5000} factor={4} saturation={0.5} fade speed={0.5} />
        </>
    );
};

// Lazy Load Heavy 3D Assets
const DynamicProductsBackground = dynamic(() => Promise.resolve(ProductsBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. ANIMATION LOGIC (Optimized) ---
// ============================================================================

const PageFlyToCartAnimator = () => {
  const flyQueue = useAIOrderingStore((state) => state.flyQueue);
  const removeFlyItem = useAIOrderingStore((state) => state.removeFlyItem);

  return (
    <AnimatePresence>
      {flyQueue.map((item) => {
          // Use a safe fallback if element not found to prevent calculation errors
          const el = document.getElementById(item.startElementId);
          const startRect = el ? el.getBoundingClientRect() : { top: 0, left: 0, width: 0, height: 0 };
          
          if (!startRect.width) return null;

          return (
            <motion.div
              key={item.animationId} 
              className="fixed z-[9999] rounded-xl overflow-hidden border border-cyan-500/80 shadow-[0_0_30px_rgba(6,182,212,0.8)] pointer-events-none"
              initial={{ 
                  top: startRect.top, 
                  left: startRect.left, 
                  width: startRect.width, 
                  height: startRect.height, 
                  opacity: 1, 
                  rotate: 0 
              }}
              animate={{ 
                  top: "50vh", // Center vertically roughly
                  left: -100, 
                  width: 20, 
                  height: 20, 
                  opacity: 0, 
                  rotate: -45, 
                  scale: 0.5 
              }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.8, ease: "easeInOut" }} 
              onAnimationComplete={() => removeFlyItem(item.animationId)}
            >
              {/* Using standard img for animation performance over Next/Image here */}
              <img src={item.image} alt="" className="w-full h-full object-cover" />
            </motion.div>
          );
      })}
    </AnimatePresence>
  );
};

// ============================================================================
// --- 3. LOADING SKELETONS ---
// ============================================================================

const BannerSkeleton = () => (
    <div className="animate-pulse flex flex-col items-center gap-4">
        <div className="h-16 w-3/4 max-w-lg bg-white/5 rounded-full border border-white/5"></div>
        <div className="h-4 w-1/2 max-w-sm bg-white/5 rounded-full"></div>
    </div>
);

const ProductCardSkeleton = () => (
    <div className="relative animate-pulse w-full rounded-[32px] bg-black/20 border border-white/5 p-4 flex flex-col aspect-[3/4.2]">
        <div className="flex-1 bg-white/5 rounded-2xl mb-4 relative overflow-hidden" />
        <div className="space-y-3 px-2">
            <div className="h-6 bg-white/5 rounded w-3/4"></div>
            <div className="h-4 bg-white/5 rounded w-1/2"></div>
        </div>
    </div>
);

const ProductListSkeleton = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        {[...Array(8)].map((_, i) => <ProductCardSkeleton key={i} />)}
    </div>
);

// ============================================================================
// --- 4. ARCHITECTURAL PRODUCT CARD (Memoized for Speed) ---
// ============================================================================

// Defined outside to prevent recreation on render
const cardVariants = {
    hidden: { opacity: 0, y: 30, scale: 0.9 }, 
    visible: { opacity: 1, y: 0, scale: 1 } 
};

// Using React.memo ensures this card ONLY re-renders if its specific props change.
// Crucial for lists with 100+ items.
const ProductCard = React.memo(({ product, onOpen }: { product: Product, onOpen: (product: Product) => void }) => {
    const addProductById = useAIOrderingStore((state) => state.addProductById);
    const [isAdded, setIsAdded] = useState(false);
    const uniqueBtnId = `add-to-manifest-${product.id}`; 

    const handleAddToCart = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        addProductById(product, uniqueBtnId); 
        setIsAdded(true);
        // Clean up timeout to prevent memory leaks if component unmounts
        const timer = setTimeout(() => setIsAdded(false), 2000);
        return () => clearTimeout(timer);
    }, [product, uniqueBtnId, addProductById]);

    return (
        <motion.div
            layoutId={`product-card-${product.id}`}
            variants={cardVariants}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="group relative w-full h-full rounded-[32px] bg-black/40 backdrop-blur-md border border-white/10 overflow-hidden hover:border-cyan-500/40 hover:shadow-[0_0_40px_rgba(0,198,255,0.1)] transition-all duration-500 cursor-pointer flex flex-col will-change-transform"
            onClick={() => onOpen(product)}
        >
            <div className="absolute top-4 left-4 z-20 flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                <div className="px-2 py-1 rounded bg-black/50 border border-white/10 text-[10px] text-cyan-400 font-mono backdrop-blur-sm">
                    ID-{product.id.toString().padStart(3, '0')}
                </div>
            </div>

            <div className="relative w-full aspect-square p-8 overflow-hidden bg-gradient-to-b from-white/5 to-transparent">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <motion.div 
                    className="w-full h-full relative z-10"
                    whileHover={{ scale: 1.1, y: -5, rotate: 2 }}
                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                >
                    <Image
                        id={`product-img-${product.id}`} 
                        src={product.image_url || '/images/default.jpeg'}
                        alt={product.name}
                        fill
                        className="object-contain drop-shadow-2xl"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        loading="lazy"
                    />
                </motion.div>
            </div>
            
            <div className="relative z-10 p-5 flex flex-col flex-grow bg-black/20 border-t border-white/5 group-hover:bg-black/40 transition-colors">
                <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-bold text-white leading-tight line-clamp-1 group-hover:text-cyan-300 transition-colors" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {product.name}
                    </h3>
                </div>
                
                <div className="flex items-center gap-2 mb-4">
                    {/* CRASH FIX APPLIED HERE: formatCurrency */}
                    <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 font-mono tracking-tight">
                        ${formatCurrency(product.price)}
                    </span>
                    {product.stock_status && (
                        <span className="px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-[10px] text-green-400 uppercase tracking-wider">
                            In Stock
                        </span>
                    )}
                </div>

                <p className="text-xs text-gray-400 mb-4 line-clamp-2 leading-relaxed opacity-70 group-hover:opacity-100 transition-opacity">
                    {product.description}
                </p>
                
                <div className="mt-auto pt-2">
                    <AnimatePresence mode="wait">
                        {isAdded ? (
                            <motion.button
                                key="added"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="w-full py-3 rounded-2xl bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                            >
                                <Zap size={16} className="fill-cyan-300" /> Uplinked
                            </motion.button>
                        ) : (
                            <div className="flex gap-2">
                                <motion.button 
                                    id={uniqueBtnId}
                                    key="add"
                                    onClick={handleAddToCart}
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="flex-1 py-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500 hover:text-black font-bold text-xs tracking-widest flex items-center justify-center gap-2 transition-all duration-300 group/btn"
                                >
                                    <ShoppingBag size={16} className="group-hover/btn:text-black transition-colors" /> 
                                    <span className="group-hover/btn:text-black">order with air</span>
                                </motion.button>
                                <motion.button
                                    key="view"
                                    onClick={(e) => { e.stopPropagation(); onOpen(product); }}
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="p-3 rounded-2xl bg-white/5 border border-white/10 text-white hover:bg-white/20 hover:border-white/30 transition-all"
                                >
                                    <Eye size={18} />
                                </motion.button>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
});
ProductCard.displayName = 'ProductCard';

const ProductList = React.memo(({ products, onOpen }: { products: Product[], onOpen: (product: Product) => void }) => (
    <motion.div 
        variants={{ visible: { transition: { staggerChildren: 0.05 } } }} // Faster stagger
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8"
    >
        {products.map(product => (
            <ProductCard key={product.id} product={product} onOpen={onOpen} />
        ))}
    </motion.div>
));
ProductList.displayName = 'ProductList';

// ============================================================================
// --- 5. AI FEATURED MODULE ---
// ============================================================================
const PersonalizedRecommendations = ({ onOpen }: { onOpen: (product: Product) => void }) => {
    const { data: session, status } = useSession();

    const apiUrl = status === 'authenticated'
        ? `/products/featured-recommendation` 
        : null;

    const { data: recommendationsData, error, isLoading } = useSWR<Product>(apiUrl, fetcher, {
        revalidateOnFocus: false,
        shouldRetryOnError: false,
        dedupingInterval: 60000 // Cache for 1 minute
    });

    const topPick = useMemo(() => {
        if (!recommendationsData) return null;
        return { ...recommendationsData, isAIRec: true };
    }, [recommendationsData]);

    if (isLoading || error || !topPick || status !== 'authenticated') {
        return null;
    }

    return (
        <section className="mb-24 relative group">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-600/10 via-purple-600/10 to-transparent blur-3xl opacity-30 group-hover:opacity-50 transition-opacity duration-1000" />
            
            <motion.div 
                initial={{ opacity: 0, y: 20 }} 
                animate={{ opacity: 1, y: 0 }} 
                transition={{ delay: 0.3 }}
                className="relative flex flex-col lg:flex-row items-stretch gap-0 bg-black/40 backdrop-blur-xl border border-white/10 rounded-[40px] overflow-hidden shadow-2xl shadow-cyan-900/20"
            >
                <div className="w-full lg:w-2/5 relative min-h-[400px] bg-gradient-to-br from-white/5 to-transparent flex items-center justify-center p-10 overflow-hidden">
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
                    <motion.div 
                        className="relative z-10 w-full h-full"
                        animate={{ y: [0, -10, 0] }}
                        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <Image
                            src={topPick.image_url || '/images/default.jpeg'}
                            alt={topPick.name}
                            fill
                            className="object-contain drop-shadow-[0_0_50px_rgba(0,198,255,0.3)]"
                            priority // Load this fast (Above Fold)
                        />
                    </motion.div>
                    
                    
                </div>

                <div className="w-full lg:w-3/5 p-10 lg:p-12 flex flex-col justify-center bg-black/20">
                    <div className="flex items-center gap-3 mb-6">
                        <ScanLine className="w-6 h-6 text-gray-500" />
                        <span className="text-xs font-mono text-gray-500 uppercase tracking-[0.2em]">Selected for you</span>
                    </div>
                    
                    <h2 className="text-4xl lg:text-5xl font-black text-white mb-6 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-cyan-400">
                            {topPick.name}
                        </span>
                    </h2>
                    
                    <p className="text-lg text-gray-300 mb-8 leading-relaxed max-w-xl border-l-2 border-cyan-500/30 pl-6">
                        {topPick.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-4 mt-auto">
                        <button 
                            onClick={() => onOpen(topPick)}
                            className="group relative px-8 py-4 bg-cyan-500 text-black font-bold uppercase tracking-widest text-sm rounded-full overflow-hidden transition-all hover:scale-105 hover:shadow-[0_0_30px_rgba(6,182,212,0.4)]"
                        >
                            <span className="relative z-10 flex items-center gap-2">
                                View <ArrowRightIcon className="w-4 h-4" />
                            </span>
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                        </button>
                        
                        <div className="px-6 py-4 rounded-full border border-white/10 flex items-center gap-3 bg-white/5">
                            <Tag size={16} className="text-purple-400" />
                            <span className="text-sm text-gray-300 font-mono">${formatCurrency(topPick.price)}</span>
                        </div>
                    </div>
                </div>
            </motion.div>
        </section>
    );
};

const ArrowRightIcon = ({ className }: { className?: string }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
    </svg>
);

// ============================================================================
// --- 6. PAGINATION & ERROR ---
// ============================================================================

const Pagination = ({ page, setPage, hasMore }: { page: number, setPage: (p: number) => void, hasMore: boolean }) => (
    <div className="flex justify-center items-center gap-4 mt-16">
        <button
            disabled={page === 1}
            onClick={() => {
                setPage(page - 1);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="p-3 rounded-xl bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-all"
        >
            <ChevronLeft size={20} />
        </button>
        <span className="font-mono text-cyan-400 text-sm tracking-widest px-4 py-2 border border-cyan-500/30 rounded-lg bg-cyan-950/20">
            PAGE {page.toString().padStart(2, '0')}
        </span>
        <button
            disabled={!hasMore}
            onClick={() => {
                setPage(page + 1);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="p-3 rounded-xl bg-white/5 border border-white/10 text-white disabled:opacity-30 hover:bg-white/10 transition-all"
        >
            <ChevronRight size={20} />
        </button>
    </div>
);

const ErrorDisplay = ({ error, retry }: { error: any, retry: () => void }) => (
    <div className="flex flex-col items-center justify-center text-center py-20 px-6">
        <div className="p-6 bg-red-500/10 rounded-full border border-red-500/30 mb-6">
            <AlertTriangle className="w-12 h-12 text-red-400" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>System Error</h3>
        <p className="text-gray-400 max-w-md mb-6">{error?.message || 'Unable to retrieve product manifest. Connection interrupted.'}</p>
        <button 
            onClick={retry}
            className="px-6 py-2 bg-white/10 hover:bg-white/20 border border-white/10 rounded-lg text-sm text-white transition-colors"
        >
            Retry Connection
        </button>
    </div>
);

// ============================================================================
// --- 7. MAIN PAGE COMPONENT (The Terminal) ---
// ============================================================================

export default function ProductsPage() {
    const [page, setPage] = useState(1);
    const [category, setCategory] = useState("ALL");
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

    // Optimized Query Key for SWR
    const queryKey = `/products/?page=${page}&limit=${ITEMS_PER_PAGE}&category=${category !== 'ALL' ? category.toLowerCase() : ''}`;
    
    const { data: productsData, error, isLoading, mutate } = useSWR<Product[] | { items: Product[], total: number }>(
        queryKey,
        fetcher,
        { 
            revalidateOnFocus: false,
            keepPreviousData: true // Creates the "Instant" feel
        }
    );

    const products = useMemo(() => {
        if (!productsData) return [];
        return Array.isArray(productsData) ? productsData : productsData.items || [];
    }, [productsData]);

    const hasMore = useMemo(() => {
        if (products.length < ITEMS_PER_PAGE) return false;
        // In a real scenario, use productsData.total from backend
        return true; 
    }, [products]);

    // Optimize Handlers to prevent unnecessary re-renders of children
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
        <div className="min-h-screen w-full bg-black text-gray-100 overflow-x-hidden selection:bg-cyan-500/30">
            
            <div className="fixed inset-0 z-0">
                 {/* Canvas logic is heavy, ensuring it doesn't block main thread via suspense */}
                 <Canvas camera={{ position: [0, 0, 20], fov: 45 }} dpr={[1, 2]}>
                    <Suspense fallback={null}>
                        <DynamicProductsBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/80 pointer-events-none" />
            </div>

            <PageFlyToCartAnimator />

            <main className="container mx-auto px-4 lg:px-8 pb-32 relative z-10">
                
                <section className="relative text-center pt-32 pb-16 md:pt-40 md:pb-24">
                    {isLoading && !productsData && !error ? <BannerSkeleton /> : (
                        <motion.div
                            initial={{ opacity: 0, y: -30 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                        >
                            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md mb-6">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                <span className="text-[10px] font-mono text-gray-300 uppercase tracking-widest">Global Network Live</span>
                            </div>
                            
                            <h1 className="text-5xl md:text-8xl font-black uppercase tracking-tight mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                 <motion.span
                                    className="text-transparent bg-clip-text bg-gradient-to-b from-white via-cyan-100 to-cyan-900"
                                    animate={{
                                        textShadow: [
                                            '0 0 20px rgba(0, 198, 255, 0)',
                                            '0 0 40px rgba(0, 198, 255, 0.3)',
                                            '0 0 20px rgba(0, 198, 255, 0)'
                                        ]
                                    }}
                                    transition={{ duration: 4, repeat: Infinity }}
                                >
                                    The Catalog
                                </motion.span>
                            </h1>
                            
                            <motion.p
                                initial={{ opacity: 0 }} 
                                animate={{ opacity: 1 }} 
                                transition={{ delay: 0.3 }}
                                className="max-w-2xl mx-auto text-lg text-gray-400 font-light leading-relaxed"
                            >
                                Access the world's most advanced autonomous delivery inventory. <br className="hidden md:block" />
                                Selected by order with air. Delivered by airaero X.
                            </motion.p>
                        </motion.div>
                    )}
                </section>

                <PersonalizedRecommendations onOpen={handleOpen} />

                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-12 border-b border-white/10 pb-6 gap-6">
                    <div className="flex items-center gap-4">
                        <Layers className="text-cyan-500" size={24} />
                        <h2 className="text-2xl font-bold text-white uppercase tracking-widest" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            Global Inventory
                        </h2>
                    </div>

                    <div className="flex flex-wrap gap-2">
                         {CATEGORIES.map((cat) => (
                             <button
                                key={cat}
                                onClick={() => handleCategoryChange(cat)}
                                className={`px-4 py-2 rounded-full border text-xs font-bold uppercase tracking-wider transition-all duration-300 ${
                                    category === cat 
                                        ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)]' 
                                        : 'bg-white/5 border-white/10 text-gray-500 hover:border-white/30 hover:text-white'
                                }`}
                             >
                                 {cat}
                             </button>
                         ))}
                    </div>

                    <div className="hidden md:flex items-center gap-2 text-sm text-gray-500 font-mono">
                        <ScanLine size={14} />
                        <span>PAGE {page}</span>
                        <span className="text-cyan-500/50">///</span>
                        <span>{ITEMS_PER_PAGE}/PG</span>
                    </div>
                </div>

                {error ? (
                    <ErrorDisplay error={error} retry={() => mutate()} />
                ) : isLoading && !productsData ? (
                    <ProductListSkeleton />
                ) : products.length > 0 ? (
                    <>
                        {/* Using Memoized ProductList to prevent re-renders when parent state changes */}
                        <ProductList products={products} onOpen={handleOpen} />
                        <Pagination page={page} setPage={setPage} hasMore={hasMore} />
                    </>
                ) : (
                    <div className="text-center py-20 border border-dashed border-white/10 rounded-[32px]">
                        <ShoppingBag size={48} className="mx-auto text-gray-600 mb-4" />
                        <p className="text-gray-500 text-lg">Inventory Depleted in this Sector. Awaiting Resupply.</p>
                        <button onClick={() => setCategory("ALL")} className="mt-4 text-cyan-400 hover:underline">Return to All Sectors</button>
                    </div>
                )}
            </main>

            <AnimatePresence>
                {selectedProduct && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={handleClose}
                        className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-2xl flex justify-center items-center p-4 overflow-hidden" 
                    >
                        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-5xl">
                            <ProductDetailsCard
                                product={selectedProduct}
                                onClose={handleClose}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
