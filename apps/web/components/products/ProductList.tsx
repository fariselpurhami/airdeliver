//** apps/web/components/products/ProductList.tsx **//

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProductCard } from './ProductCard';
import { ProductDetailsCard } from './ProductDetailsCard';
import { type Product } from '@/types';

// 🛡️ L8 FIX: إيقاف الـ stagger في الموبايل لمنع الكراش
const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: typeof window !== 'undefined' && window.innerWidth > 768 ? 0.08 : 0, 
    },
  },
};

export default function ProductList({ products }: { products: Product[] }) {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const handleOpen = (product: Product) => {
    setSelectedProduct(product);
    document.body.style.overflow = 'hidden';
  };

  const handleClose = () => {
    setSelectedProduct(null);
    document.body.style.overflow = '';
  };

  return (
    <>
      {/* سكرول عمودي طبيعي جداً للموبايل */}
      <div className="w-full pb-24">
        
        <motion.div
          variants={listVariants}
          initial="hidden"
          animate="visible"
          // 👇 التعديل السحري: grid-cols-2 بيجبر الشاشة تعرض كارتين متساويين بظبط، و gap-3 بتعمل مسافة شيك بينهم
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4 p-3 md:p-4 w-full mx-auto" 
        >
          {products.map((product, index) => (
            <ProductCard
              key={product.id}
              product={product}
              priority={index < 4} 
              onOpen={handleOpen}
            />
          ))}
        </motion.div>

      </div>

      <AnimatePresence>
        {selectedProduct && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 z-[100] bg-black/90 md:backdrop-blur-xl flex justify-center items-center p-4 md:p-8 overflow-hidden transform-gpu" 
          >
            <div onClick={(e) => e.stopPropagation()} className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh]">
              <ProductDetailsCard
                product={selectedProduct}
                onClose={handleClose}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
