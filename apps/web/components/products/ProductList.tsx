//** apps/web/components/products/Productlist.tsx **//

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProductCard } from './ProductCard';
import { ProductDetailsCard } from './ProductDetailsCard';
import { type Product } from '@/types';

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08, 
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
      <motion.div
        variants={listVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 p-4" 
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

      <AnimatePresence>
        {selectedProduct && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex justify-center items-center p-4 md:p-8 overflow-hidden" 
          >
            <div onClick={(e) => e.stopPropagation()} className="w-full max-w-5xl h-full flex items-center justify-center">
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
