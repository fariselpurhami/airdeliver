//** apps/web/components/products/ProductOverlay.tsx **//

'use client';

import React, { useState, useRef, useMemo, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, PackageSearch, Plus, ShoppingBag } from 'lucide-react';
import ProductList from './ProductList'; 
import { type Product } from '@/types'; 
import useSWR from 'swr';
import { api } from '@/lib/api';
import { listedCatalogPrice } from '../ai/CatalogPrice';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore'; 
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock';
// --- ARCHITECTURAL UTILS: DATA ADAPTER LAYER ---
const fetcher = (url: string) => api.get(url).then(res => res.data);

// Keep the existing numeric Product contract while carrying unknown explicitly.
// A numeric compatibility value is never displayed or addable without its status.
export const normalizeProductData = (rawProduct: any): Product => {
    const price = listedCatalogPrice(rawProduct);
    return { ...rawProduct, price: price ?? 0,
        price_status: price === null ? 'unknown' : 'listed',
        inventory: Number(rawProduct.inventory) || 0 };
};

const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-full">
        <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-white/60 animate-spin" />
    </div>
);
const AddToManifestButton = ({ products }: { products: Product[] }) => {
    const { addProductById } = useAIOrderingStore();
    const [isFlying, setIsFlying] = useState(false);
    const btnRef = useRef<HTMLButtonElement>(null);

    const handleQuickAdd = (e: React.MouseEvent) => {
        e.stopPropagation();
        
        const productToAdd = products[0];
        
        if (productToAdd && listedCatalogPrice(productToAdd) !== null) {
            addProductById(productToAdd, 'quick-manifest-btn');
            setIsFlying(true);
            setTimeout(() => setIsFlying(false), 1000);
        }
    };

    return (
        <div className="relative group">
            <motion.button
                id="quick-manifest-btn"
                ref={btnRef}
                onClick={handleQuickAdd}
                disabled={!products[0] || listedCatalogPrice(products[0]) === null}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="relative overflow-hidden flex items-center gap-3 px-6 py-3 rounded-2xl bg-gradient-to-r from-cyan-600 to-blue-600 border border-cyan-400/30 text-white font-bold tracking-wider text-xs shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_40px_rgba(6,182,212,0.6)] transition-all duration-300"
            >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                <Plus size={16} className="text-cyan-100" />
                <span className="relative z-10">order with air</span>
                
                <span className="absolute -inset-1 rounded-2xl border border-cyan-400/0 group-hover:border-cyan-400/50 group-hover:animate-ping opacity-20 pointer-events-none" />
            </motion.button>

            <AnimatePresence>
                {isFlying && (
                    <motion.div
                        initial={{ opacity: 1, x: 0, y: 0, scale: 1 }}
                        animate={{ 
                            x: -300, 
                            y: 300,  
                            opacity: 0, 
                            scale: 0.5,
                            rotate: -45 
                        }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} 
                        className="absolute top-1/2 left-1/2 z-50 pointer-events-none"
                    >
                        <div className="relative p-2 bg-cyan-400 rounded-full shadow-[0_0_30px_rgba(6,182,212,1)]">
                            <ShoppingBag size={20} className="text-black fill-black" />
                            <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: 100 }}
                                className="absolute right-0 top-1/2 h-1 bg-gradient-to-l from-cyan-400 to-transparent -translate-y-1/2 origin-right"
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default function ProductOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    
    const { data: productsData, error, isLoading } = useSWR(
        isOpen ? '/products/' : null,
        fetcher,
        { revalidateOnFocus: false }
    );
    
    // --- ARCHITECTURAL FIX: MEMOIZED SANITIZATION ---
    // We process the data ONCE when it arrives, guaranteeing downstream safety.
    const products = useMemo(() => {
        if (!productsData) return [];
        
        const rawList = Array.isArray(productsData) ? productsData : (productsData as any).items || [];
        
        // This .map runs the 'normalizeProductData' on every item
        return rawList.map(normalizeProductData);
    }, [productsData]);
    
    useBodyScrollLock({ locked: isOpen });
    useEffect(() => {
        if (!isOpen) {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    if (typeof document === 'undefined') return null;
    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose} 
                    className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden"
                    style={{ paddingTop: "max(1rem, env(safe-area-inset-top))", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
                >


                    <motion.div
                        role="dialog" aria-modal="true" aria-label="Trending products"
                        initial={{ scale: 0.95, opacity: 0, y: 30 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                        onClick={(e) => e.stopPropagation()} 
			style={{ willChange: "opacity, transform" }}
                        className="w-full h-full max-w-[460px] max-h-[1050px] md:max-w-7xl md:h-[93vh] md:max-h-none flex flex-col bg-black/60 backdrop-blur-3xl border border-white/10 rounded-[28px] md:rounded-[40px] ring-1 ring-inset ring-white/5 shadow-[0_40px_120px_rgba(0,0,0,0.65)] overflow-hidden relative"
                    >
                  
                        <header className="relative z-10 flex-shrink-0 border-b border-white/5 px-6 py-5 md:px-10 md:py-6">
                            <div className="flex items-center justify-between gap-4">
                                <div className="flex min-w-0 items-baseline gap-3">
                                    <h2 className="truncate text-lg md:text-xl font-semibold tracking-tight text-white/95">
                                        Trending products
                                    </h2>
                                    {!isLoading && !error && products.length > 0 && (
                                        <span className="flex-shrink-0 text-xs md:text-sm text-gray-500">
                                            {products.length} {products.length === 1 ? 'product' : 'products'}
                                        </span>
                                    )}
                                </div>

                                <button
                                    onClick={onClose}
                                    aria-label="Close products"
                                    className="group flex-shrink-0 p-2.5 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300"
                                >
                                    <X size={20} className="group-hover:rotate-90 transition-transform duration-300" />
                                </button>
                            </div>
                        </header>
                   
                        
                        <div className="flex-grow relative z-10 overflow-hidden">
                          
                            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />
                            
                            <div className="h-full overflow-y-auto p-6 md:p-8 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                                {isLoading ? (
                                    <LoadingSpinner />
                                ) : error ? (
                                    <div className="flex flex-col items-center justify-center h-full gap-3 p-8 text-center">
                                        <PackageSearch size={32} className="text-gray-600" />
                                        <p className="text-sm font-medium text-gray-300">Couldn't load products</p>
                                        <p className="text-xs text-gray-500">Check your connection and try again.</p>
                                    </div>
                                ) : (
                                    <div className="animate-in fade-in zoom-in-95 duration-500">
                                        {/* Now passing strictly sanitized products */}
                                        <ProductList products={products} /> 
                                    </div>
                                )}
                            </div>
                        </div>

                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body
    );
}
