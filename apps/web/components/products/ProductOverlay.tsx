// apps/web/components/products/ProductOverlay.tsx

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2 } from 'lucide-react';
import ProductList from './Productlist'; 
import { type Product } from '@/types'; 
import useSWR from 'swr';
import { api } from '@/lib/api';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-full">
        <Loader2 className="w-12 h-12 text-cyan-400 animate-spin" />
    </div>
);

export default function ProductOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    
    const { data: productsData, error, isLoading } = useSWR(
        isOpen ? '/products/' : null,
        fetcher,
        { revalidateOnFocus: false }
    );
    
    const products = productsData || [];

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose} 
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-lg flex justify-center items-center p-4"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} 
                        onClick={(e) => e.stopPropagation()} 
                        className="w-full max-w-7xl h-[95vh] max-h-[1000px] flex flex-col bg-black/50 backdrop-blur-2xl border border-cyan-400/30 rounded-2xl shadow-2xl shadow-cyan-500/20 overflow-hidden"
                    >
               
                        <header className="p-4 border-b border-cyan-400/30 flex justify-between items-center flex-shrink-0">
                            <h3 className="font-bold text-lg text-white normal-case" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <motion.span
                                    className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                                    animate={{
                                    filter: [
                                        'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))',
                                        'drop-shadow(0 0 8px rgba(0, 198, 255, 0.8))',
                                        'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))'
                                    ]
                                    }}
                                    transition={{
                                    duration: 3,
                                    repeat: Infinity,
                                    ease: "easeInOut"
                                    }}
                                >
                                    Explore Products
                                </motion.span>
                            </h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </header>
                   
                        <div className="flex-grow p-6 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
                            {isLoading ? (
                                <LoadingSpinner />
                            ) : error ? (
                                <div className="text-red-400 text-center">Failed to load products.</div>
                            ) : (
                                <ProductList products={products} /> 
                            )}
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
