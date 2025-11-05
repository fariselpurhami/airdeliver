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
import { AlertTriangle, Cpu, Eye, ShoppingBag, Check } from 'lucide-react';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { useCartStore } from '@/hooks/useCartStore';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';

const fetcher = (url: string) => api.get(url).then(res => res.data);

// ============================================================================
// --- 1. Background Component ---
// ============================================================================
const ProductsBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.x = Math.sin(time * 0.5) * 15;
            light1Ref.current.position.y = Math.cos(time * 0.5) * 15;
            light1Ref.current.position.z = Math.cos(time * 0.5) * 10;
        }
        if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(time * 0.3) * -15;
            light2Ref.current.position.y = Math.cos(time * 0.3) * -15;
            light2Ref.current.position.z = Math.sin(time * 0.3) * 5;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 10, 30]} />
            <ambientLight intensity={1.0} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        </>
    );
};

const DynamicProductsBackground = dynamic(() => Promise.resolve(ProductsBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. Skeletons ---
// ============================================================================

const BannerSkeleton = () => (
    <div className="animate-pulse">
        <div className="h-16 md:h-24 bg-cyan-900/50 rounded w-3/4 mx-auto mb-4"></div>
        <div className="h-6 bg-cyan-800/50 rounded w-1/2 mx-auto"></div>
    </div>
);

const ProductCardSkeleton = () => (
    <div className="relative animate-pulse w-full rounded-2xl bg-black/30 backdrop-blur-xl border border-cyan-400/30 p-6 flex flex-col justify-between aspect-[3/4] shadow-lg shadow-cyan-500/10">
        <div className="h-1/2 bg-cyan-900/50 rounded-lg mb-4"></div>
        <div className="space-y-3">
            <div className="h-4 bg-cyan-800/50 rounded w-3/4"></div>
            <div className="h-6 bg-cyan-700/50 rounded w-1/2"></div>
            <div className="h-10 bg-cyan-800/50 rounded w-full"></div>
        </div>
    </div>
);

const ProductListSkeleton = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => <ProductCardSkeleton key={i} />)}
    </div>
);

// ============================================================================
// --- 3. (Refactored) Product Card Component ---
// ============================================================================
const ProductCard = ({ product, onOpen }: { product: Product, onOpen: (product: Product) => void }) => {
    const { addToCart } = useCartStore();
    const [isAdded, setIsAdded] = useState(false);

    const handleAddToCart = (e: React.MouseEvent) => {
        e.stopPropagation();
        addToCart(product);
        setIsAdded(true);
        setTimeout(() => setIsAdded(false), 1200);
    };

    const handleViewDetails = (e: React.MouseEvent) => {
        e.stopPropagation();
        onOpen(product);
    };

    return (
        <motion.div
            layoutId={`product-card-${product.id}`}
            variants={{ hidden: { opacity: 0, y: 30, scale: 0.95 }, visible: { opacity: 1, y: 0, scale: 1 } }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="relative w-full rounded-2xl overflow-hidden bg-black/30 backdrop-blur-xl border border-cyan-400/30 flex flex-col aspect-[3/4] group cursor-pointer"
            whileHover={{ y: -8, scale: 1.03, boxShadow: '0 0 30px rgba(0, 198, 255, 0.3)' }}
            onClick={() => onOpen(product)}
        >
            <div className="absolute w-full h-full inset-0 z-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" 
                 style={{ background: 'radial-gradient(circle at 50% 50%, rgba(0, 198, 255, 0.15) 0%, rgba(0, 198, 255, 0) 70%)' }} />

            <div className="relative w-full h-1/2 p-6">
                <Image
                    src={product.image_url || '/images/default.jpeg'}
                    alt={product.name}
                    fill
                    className="object-contain"
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                />
            </div>
            
            <div className="relative z-10 p-6 flex flex-col justify-end h-1/2 bg-gradient-to-t from-black/50 to-transparent">
                <h3 className="text-xl font-bold text-white mb-2 truncate" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {product.name}
                </h3>
                <p className="text-2xl font-black text-cyan-400 mb-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    ${product.price.toFixed(2)}
                </p>
                <p className="text-sm text-gray-400 mb-4 line-clamp-2">{product.description}</p>
                
                <AnimatePresence mode="wait">
                    {isAdded ? (
                        <motion.div
                            key="added"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex-1 p-3 rounded-lg bg-green-500/10 border border-green-500/50 text-white font-bold text-sm flex items-center justify-center gap-2"
                        >
                            <Check size={16} /> Added
                        </motion.div>
                    ) : (
                        <motion.div
                            key="add"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex gap-2 opacity-0 group-hover:opacity-100 transform translate-y-3 group-hover:translate-y-0 transition-all duration-300"
                        >
                            <button 
                                onClick={handleAddToCart}
                                className="flex-1 p-3 rounded-lg bg-cyan-500 text-black font-bold text-sm flex items-center justify-center gap-2"
                            >
                                <ShoppingBag size={16} /> Add to Cart
                            </button>
                            <button 
                                onClick={handleViewDetails}
                                className="p-3 rounded-lg bg-white/10 text-white hover:bg-white/20"
                            >
                                <Eye size={16} />
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

const ProductList = ({ products, onOpen }: { products: Product[], onOpen: (product: Product) => void }) => (
    <motion.div 
        variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
    >
        {products.map(product => (
            <ProductCard key={product.id} product={product} onOpen={onOpen} />
        ))}
    </motion.div>
);


// ============================================================================
// --- 4. (Refactored) AI Replicator Component ---
// ============================================================================
const PersonalizedRecommendations = ({ onOpen }: { onOpen: (product: Product) => void }) => {
    const { data: session, status } = useSession();
    const userId = (session?.user as any)?.id;

    const apiUrl = status === 'authenticated' && userId
        ? `/products/suggestions?product_id=1&user_id=${userId}`
        : null;

    const { data: recommendationsData, error, isLoading } = useSWR<Product[]>(apiUrl, fetcher, {
        revalidateOnFocus: false,
        shouldRetryOnError: false
    });

    const topPick = useMemo(() => {
        if (!recommendationsData) return null;
        const items = Array.isArray(recommendationsData) ? recommendationsData : (recommendationsData as any).items || [];
        const product = items.map((p: any) => ({ ...p, isAIRec: true }))[0];
        return product || null;
    }, [recommendationsData]);

    if (isLoading || error || !topPick || status !== 'authenticated') {
        return null;
    }

    return (
        <section className="mb-24">
            <motion.div 
                initial={{ opacity: 0 }} 
                animate={{ opacity: 1 }} 
                transition={{ delay: 0.5 }}
                className="flex flex-col lg:flex-row items-center gap-8 p-8 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-3xl shadow-2xl shadow-cyan-500/10"
            >
                <div className="w-full lg:w-2/5 h-96 lg:h-auto lg:aspect-square">
                    <ProductCard product={topPick} onOpen={onOpen} />
                </div>

                <div className="w-full lg:w-3/5 text-center lg:text-left">
                    <div className="flex items-center justify-center lg:justify-start gap-3 mb-4">
                        <Cpu className="w-8 h-8 text-cyan-400" />
                        <h2 className="text-3xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            A.I. Recommendation
                        </h2>
                    </div>
                    <p className="text-lg text-gray-400 mb-6">
                        Based on your activity and recent autonomous deliveries, our AI core has selected this product for you.
                    </p>
                    <h3 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600 mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {topPick.name}
                    </h3>
                    <p className="text-gray-300 mb-8 line-clamp-3">
                        {topPick.description}
                    </p>
                    <button 
                        onClick={() => onOpen(topPick)}
                        className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-black bg-white rounded-full shadow-lg transition-transform duration-300 hover:scale-105 overflow-hidden"
                    >
                        <span className="absolute inset-0 bg-gradient-to-r from-[#00C6FF] to-[#7F00FF] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        <span className="relative flex items-center">View Product Details</span>
                    </button>
                </div>
            </motion.div>
        </section>
    );
};

// ============================================================================
// --- 5. Error Component ---
// ============================================================================

const ErrorDisplay = ({ error }: { error: any }) => (
    <div className="flex flex-col items-center justify-center text-center text-red-400 my-16 p-6 border border-red-500/30 bg-red-900/50 rounded-2xl backdrop-blur-lg">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h3 className="text-xl font-bold mb-2">Failed to Load Products</h3>
        <p className="text-sm">{error?.message || 'An unknown error occurred.'}</p>
        <p className="text-xs mt-2">Please try refreshing the page or check back later.</p>
    </div>
);

// ============================================================================
// --- 6. (Refactored) Main Page Component ---
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
        <div className="min-h-screen w-full bg-black text-gray-100">
            <div className="fixed inset-0 z-0 opacity-70">
                 <Canvas>
                    <Suspense fallback={null}>
                        <DynamicProductsBackground />
                    </Suspense>
                </Canvas>
            </div>

            <main className="container mx-auto px-4 pb-24 relative z-10">
                <section className="relative text-center py-32 md:py-48">
                    {isLoading && !productsData && !error ? <BannerSkeleton /> : (
                        <motion.h1
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                            className="text-5xl md:text-7xl font-black uppercase" 
                            style={{ fontFamily: "'Orbitron', sans-serif" }}
                        >
                             <motion.span
                                className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                                animate={{
                                filter: [
                                    'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))',
                                    'drop-shadow(0 0 16px rgba(0, 198, 255, 0.8)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.8))',
                                    'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))'
                                ]
                                }}
                                transition={{
                                duration: 3,
                                repeat: Infinity,
                                ease: "easeInOut"
                                }}
                            >
                                THE CATALOG
                            </motion.span>
                        </motion.h1>
                    )}
                    <motion.p
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                        className="mt-4 text-lg text-gray-400"
                    >
                        Find Products You Love. Get Them in Minutes.
                    </motion.p>
                </section>

                <PersonalizedRecommendations onOpen={handleOpen} />

                <h2 className="text-3xl font-bold mb-12 text-center" style={{ fontFamily: "'Orbitron', sans-serif" }}>All Products</h2>

                {error ? (
                    <ErrorDisplay error={error} />
                ) : isLoading && !productsData ? (
                    <ProductListSkeleton />
                ) : products.length > 0 ? (
                    <ProductList products={products} onOpen={handleOpen} />
                ) : (
                    <p className="text-center text-gray-500">No products available at the moment.</p>
                )}
            </main>

            <AnimatePresence>
                {selectedProduct && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={handleClose}
                        className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-lg flex justify-center items-center p-4" 
                    >
                        <div onClick={(e) => e.stopPropagation()}>
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
