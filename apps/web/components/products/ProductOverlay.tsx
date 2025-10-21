// file: components/products/ProductOverlay.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import ProductList from '@/components/products/Productlist'; 
import { type Product } from '@/types'; 


const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-full">
        <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
);

export default function ProductOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    
    useEffect(() => {
        if (isOpen) {
            const fetchProducts = async () => {
                setIsLoading(true);
                try {
                    
                    const response = await fetch('http://127.0.0.1:8000/api/v1/products/');
                    if (!response.ok) throw new Error(`Network response was not ok`);
                    const data = await response.json();
                    setProducts(data);
                } catch (error) {
                    console.error("Failed to fetch products for overlay:", error);
                } finally {
                    setIsLoading(false);
                }
            };
            fetchProducts();
        }
    }, [isOpen]); 

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose} 
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-center items-center p-4"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} 
                        onClick={(e) => e.stopPropagation()} 
                        className="w-full max-w-7xl h-[95vh] max-h-[1000px] flex flex-col bg-black/50 border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden"
                    >
                        {/* Header */}
                        <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
                            <h3 className="font-bold text-lg text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                Explore Products
                            </h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </header>

                        {/* Product List */}
                        <div className="flex-grow p-6 overflow-y-auto">
                            {isLoading ? (
                                <LoadingSpinner />
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
