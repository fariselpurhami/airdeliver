//** apps/web/components/products/ProductOverlay.tsx **//

'use client';

import React, { useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, PackageSearch, ScanBarcode, Sparkles, Database, Wifi, Plus, ShoppingBag } from 'lucide-react';
import ProductList from './ProductList'; 
import { type Product } from '@/types'; 
import useSWR from 'swr';
import { api } from '@/lib/api';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore'; 

// --- ARCHITECTURAL UTILS: DATA ADAPTER LAYER ---
const fetcher = (url: string) => api.get(url).then(res => res.data);

// Safe Data Normalizer: Ensures 'price' is ALWAYS a number before it hits the UI
// This prevents the "toFixed is not a function" crash globally for this overlay
const normalizeProductData = (rawProduct: any): Product => ({
    ...rawProduct,
    // Force conversion to Number. If fail, fallback to 0.
    price: Number(rawProduct.price) || 0, 
    // Ensure inventory is a number if needed
    inventory: Number(rawProduct.inventory) || 0,
});

const LoadingSpinner = () => (
    <div className="flex flex-col justify-center items-center h-full gap-6">
        <div className="relative">
            <div className="w-20 h-20 rounded-full border-2 border-purple-500/10 border-t-purple-400 animate-spin" />
            <div className="absolute inset-2 rounded-full border-2 border-cyan-500/10 border-b-cyan-400 animate-spin [animation-duration:1.5s]" />
            <div className="absolute inset-0 flex items-center justify-center">
                <Database className="w-6 h-6 text-white/50 animate-pulse" />
            </div>
        </div>
        <div className="flex flex-col items-center gap-1">
            <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] animate-pulse">ESTABLISHING UPLINK</p>
            <p className="text-purple-400/50 font-mono text-[10px] tracking-widest">RETRIEVING ASSETS...</p>
        </div>
    </div>
);

const AddToManifestButton = ({ products }: { products: Product[] }) => {
    const { addProductById } = useAIOrderingStore();
    const [isFlying, setIsFlying] = useState(false);
    const btnRef = useRef<HTMLButtonElement>(null);

    const handleQuickAdd = (e: React.MouseEvent) => {
        e.stopPropagation();
        
        const productToAdd = products[0];
        
        if (productToAdd) {
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

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose} 
                    className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden"
                >

                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500/50 to-transparent opacity-50" />

                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }}
                        onClick={(e) => e.stopPropagation()} 
                        className="w-full max-w-7xl h-[93vh] flex flex-col bg-black/60 backdrop-blur-3xl border border-white/10 rounded-[55px] shadow-[0_0_60px_rgba(168,85,247,0.15)] overflow-hidden relative"
                    >
                     
                        <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/5 blur-[80px] pointer-events-none" />
                        <div className="absolute bottom-0 left-0 w-64 h-64 bg-cyan-500/5 blur-[80px] pointer-events-none" />

                  
                        <header className="px-8 py-6 border-b border-white/5 flex justify-between items-center flex-shrink-0 relative z-10 bg-black/20">
                            <div className="flex flex-col">
                                <h3 className="font-bold text-xl normal-case tracking-tight flex items-center gap-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                   
                                    <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-white/5 shadow-inner">
                                        <PackageSearch size={22} className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-400 stroke-current" />
                                    </div>
                                    
                                    <motion.span
                                        className="text-transparent bg-clip-text bg-gradient-to-r from-white via-purple-200 to-purple-400"
                                        animate={{
                                            textShadow: [
                                                '0 0 10px rgba(168,85,247,0)',
                                                '0 0 20px rgba(168,85,247,0.2)',
                                                '0 0 10px rgba(168,85,247,0)'
                                            ]
                                        }}
                                        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                                    >
                                        Explore Products
                                    </motion.span>
                                </h3>
                                <div className="flex items-center gap-2 mt-1.5 ml-1">
                                    <span className="relative flex h-2 w-2">
                                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                                    </span>
                                    <span className="text-[10px] text-gray-500 font-mono tracking-[0.2em] uppercase">
                                        Live Catalog Access
                                    </span>
                                </div>
                            </div>

                            <div className="flex items-center gap-4">

                                <button
                                    onClick={onClose}
                                    className="group p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-red-500/10 hover:text-red-300 hover:border-red-500/30 transition-all duration-300 backdrop-blur-sm"
                                >
                                    <X size={22} className="group-hover:rotate-90 transition-transform duration-300" />
                                </button>
                            </div>
                        </header>
                   
                        
                        <div className="flex-grow relative z-10 overflow-hidden">
                          
                            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />
                            
                            <div className="h-full overflow-y-auto p-6 md:p-8 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
                                {isLoading ? (
                                    <LoadingSpinner />
                                ) : error ? (
                                    <div className="flex flex-col items-center justify-center h-full text-red-400 gap-4 p-8 border border-red-500/10 rounded-3xl bg-red-500/5">
                                        <ScanBarcode size={48} className="opacity-50 animate-pulse" />
                                        <div className="text-center">
                                            <p className="font-bold text-lg mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>SIGNAL LOST</p>
                                            <p className="text-sm opacity-70 font-mono">Unable to retrieve manifest. Connection terminated.</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="animate-in fade-in zoom-in-95 duration-500">
                                        {/* Now passing strictly sanitized products */}
                                        <ProductList products={products} /> 
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="px-8 py-3 border-t border-white/5 bg-black/40 backdrop-blur-md flex justify-between items-center text-[10px] text-gray-500 font-mono uppercase tracking-widest relative z-20">
                            <div className="flex items-center gap-4">
                                <span className="flex items-center gap-2">
                                    <Wifi size={10} className="text-green-500" />
                                    System: Online
                                </span>
                                <span className="hidden sm:inline-block text-gray-700">|</span>
                                <span className="hidden sm:inline-block">Latency: 12ms</span>
                            </div>
                            <span className="flex items-center gap-2 text-purple-400/80">
                                <Sparkles size={10} />
                                AI Curation Active
                            </span>
                        </div>

                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
