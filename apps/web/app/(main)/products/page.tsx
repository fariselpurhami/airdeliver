//** apps/web/app/(main)/products/page.tsx **//

'use client';

import React, { useState, useEffect, Suspense, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';
import { type Product } from '@/types';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AlertTriangle, Cpu, Eye, ShoppingBag, Check, Zap, Tag, Layers, ScanLine } from 'lucide-react';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { useCartStore } from '@/hooks/useCartStore';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';

const fetcher = (url: string) => api.get(url).then(res => res.data);

// ============================================================================
// --- 1. ARCHITECTURAL BACKGROUND (The Cosmos) ---
// ============================================================================
const ProductsBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.x = Math.sin(time * 0.5) * 20;
            light1Ref.current.position.y = Math.cos(time * 0.5) * 20;
            light1Ref.current.position.z = Math.cos(time * 0.5) * 15;
        }
        if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(time * 0.3) * -20;
            light2Ref.current.position.y = Math.cos(time * 0.3) * -20;
            light2Ref.current.position.z = Math.sin(time * 0.3) * 10;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 15, 50]} />
            <ambientLight intensity={0.8} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={300} color="#00C6FF" distance={50} />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={200} color="#7F00FF" distance={50} />
            <Stars radius={120} depth={60} count={8000} factor={5} saturation={0.5} fade speed={0.5} />
        </>
    );
};

const DynamicProductsBackground = dynamic(() => Promise.resolve(ProductsBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. SKELETONS (Loading States) ---
// ============================================================================

const BannerSkeleton = () => (
    <div className="animate-pulse flex flex-col items-center gap-4">
        <div className="h-16 w-3/4 max-w-lg bg-white/5 rounded-full border border-white/5"></div>
        <div className="h-4 w-1/2 max-w-sm bg-white/5 rounded-full"></div>
    </div>
);

const ProductCardSkeleton = () => (
    <div className="relative animate-pulse w-full rounded-[32px] bg-black/20 border border-white/5 p-4 flex flex-col aspect-[3/4.2]">
        <div className="flex-1 bg-white/5 rounded-2xl mb-4 relative overflow-hidden">
             <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
        </div>
        <div className="space-y-3 px-2">
            <div className="h-6 bg-white/5 rounded w-3/4"></div>
            <div className="h-4 bg-white/5 rounded w-1/2"></div>
            <div className="h-12 bg-white/5 rounded-2xl w-full mt-2"></div>
        </div>
    </div>
);

const ProductListSkeleton = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        {[...Array(8)].map((_, i) => <ProductCardSkeleton key={i} />)}
    </div>
);

// ============================================================================
// --- 3. ARCHITECTURAL PRODUCT CARD (The "Pod") ---
// ============================================================================
const ProductCard = ({ product, onOpen }: { product: Product, onOpen: (product: Product) => void }) => {
    const { addToCart } = useCartStore();
    const [isAdded, setIsAdded] = useState(false);

    const handleAddToCart = (e: React.MouseEvent) => {
        e.stopPropagation();
        addToCart(product);
        setIsAdded(true);
        setTimeout(() => setIsAdded(false), 1500);
    };

    return (
        <motion.div
            layoutId={`product-card-${product.id}`}
            variants={{ 
                hidden: { opacity: 0, y: 30, scale: 0.9 }, 
                visible: { opacity: 1, y: 0, scale: 1 } 
            }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="group relative w-full h-full rounded-[32px] bg-black/40 backdrop-blur-md border border-white/10 overflow-hidden hover:border-cyan-500/40 hover:shadow-[0_0_40px_rgba(0,198,255,0.1)] transition-all duration-500 cursor-pointer flex flex-col"
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
                        src={product.image_url || '/images/default.jpeg'}
                        alt={product.name}
                        fill
                        className="object-contain drop-shadow-2xl"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
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
                    <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 font-mono tracking-tight">
                        ${product.price.toFixed(2)}
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
                                className="w-full py-3 rounded-2xl bg-green-500/20 border border-green-500/50 text-green-300 font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2"
                            >
                                <Check size={16} /> Acquired
                            </motion.button>
                        ) : (
                            <div className="flex gap-2">
                                <motion.button 
                                    key="add"
                                    onClick={handleAddToCart}
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="flex-1 py-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500 hover:text-black font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2 transition-all duration-300 group/btn"
                                >
                                    <ShoppingBag size={16} className="group-hover/btn:text-black transition-colors" /> 
                                    <span className="group-hover/btn:text-black">Add to Cart</span>
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
};

const ProductList = ({ products, onOpen }: { products: Product[], onOpen: (product: Product) => void }) => (
    <motion.div 
        variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8"
    >
        {products.map(product => (
            <ProductCard key={product.id} product={product} onOpen={onOpen} />
        ))}
    </motion.div>
);


// ============================================================================
// --- 4. AI FEATURED MODULE (The Core) ---
// ============================================================================
const PersonalizedRecommendations = ({ onOpen }: { onOpen: (product: Product) => void }) => {
    const { data: session, status } = useSession();

    const apiUrl = status === 'authenticated'
        ? `/products/featured-recommendation` 
        : null;

    const { data: recommendationsData, error, isLoading } = useSWR<Product>(apiUrl, fetcher, {
        revalidateOnFocus: false,
        shouldRetryOnError: false
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
                        />
                    </motion.div>
                    
                    <div className="absolute top-6 left-6 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 backdrop-blur-md flex items-center gap-2">
                        <Cpu size={14} className="text-cyan-400 animate-pulse" />
                        <span className="text-[10px] font-bold text-cyan-300 uppercase tracking-widest">AI Selected</span>
                    </div>
                </div>

                <div className="w-full lg:w-3/5 p-10 lg:p-12 flex flex-col justify-center bg-black/20">
                    <div className="flex items-center gap-3 mb-6">
                        <ScanLine className="w-6 h-6 text-gray-500" />
                        <span className="text-xs font-mono text-gray-500 uppercase tracking-[0.2em]">Recommendation Engine v9.0</span>
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
                                Initiate View <ArrowRightIcon className="w-4 h-4" />
                            </span>
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                        </button>
                        
                        <div className="px-6 py-4 rounded-full border border-white/10 flex items-center gap-3 bg-white/5">
                            <Tag size={16} className="text-purple-400" />
                            <span className="text-sm text-gray-300 font-mono">${topPick.price.toFixed(2)}</span>
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
// --- 5. ERROR COMPONENT ---
// ============================================================================

const ErrorDisplay = ({ error }: { error: any }) => (
    <div className="flex flex-col items-center justify-center text-center py-20 px-6">
        <div className="p-6 bg-red-500/10 rounded-full border border-red-500/30 mb-6">
            <AlertTriangle className="w-12 h-12 text-red-400" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>System Error</h3>
        <p className="text-gray-400 max-w-md mb-6">{error?.message || 'Unable to retrieve product manifest. Connection interrupted.'}</p>
        <button 
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-white/10 hover:bg-white/20 border border-white/10 rounded-lg text-sm text-white transition-colors"
        >
            Retry Connection
        </button>
    </div>
);

// ============================================================================
// --- 6. MAIN PAGE COMPONENT (The Terminal) ---
// ============================================================================

export default function ProductsPage() {
    const { data: productsData, error, isLoading } = useSWR<Product[] | { items: Product[] }>(
        '/products/',
        fetcher,
        { revalidateOnFocus: false }
    );

    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

    const products = useMemo(() => {
        if (!productsData) return [];
        return Array.isArray(productsData) ? productsData : productsData.items || [];
    }, [productsData]);

    const handleOpen = (product: Product) => {
        setSelectedProduct(product);
        document.body.style.overflow = 'hidden';
    };

    const handleClose = () => {
        setSelectedProduct(null);
        document.body.style.overflow = '';
    };

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 overflow-x-hidden">
            <div className="fixed inset-0 z-0">
                 <Canvas camera={{ position: [0, 0, 20], fov: 45 }}>
                    <Suspense fallback={null}>
                        <DynamicProductsBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/80 pointer-events-none" />
            </div>

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
                                Selected by AI. Delivered by Air.
                            </motion.p>
                        </motion.div>
                    )}
                </section>

                <PersonalizedRecommendations onOpen={handleOpen} />

                <div className="flex items-center justify-between mb-12 border-b border-white/10 pb-6">
                    <div className="flex items-center gap-4">
                        <Layers className="text-cyan-500" size={24} />
                        <h2 className="text-2xl font-bold text-white uppercase tracking-widest" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            Global Inventory
                        </h2>
                    </div>
                    <div className="hidden md:flex items-center gap-2 text-sm text-gray-500 font-mono">
                        <span>{products.length} UNITS</span>
                        <span>//</span>
                        <span>READY FOR DISPATCH</span>
                    </div>
                </div>

                {error ? (
                    <ErrorDisplay error={error} />
                ) : isLoading && !productsData ? (
                    <ProductListSkeleton />
                ) : products.length > 0 ? (
                    <ProductList products={products} onOpen={handleOpen} />
                ) : (
                    <div className="text-center py-20 border border-dashed border-white/10 rounded-[32px]">
                        <ShoppingBag size={48} className="mx-auto text-gray-600 mb-4" />
                        <p className="text-gray-500 text-lg">Inventory Depleted. Awaiting Resupply.</p>
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
