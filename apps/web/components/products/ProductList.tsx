'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ProductCard, type Product } from '@/components/products/ProductCard';

export default function ProductList({ products }: { products: Product[] }) {
  const gridVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  return (
    <motion.div
      variants={gridVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-12"
    >
      {products.map((product, index) => (
          <ProductCard 
              key={product.id} 
              product={product} 
              priority={index < 3} // This will prioritize the first 3 images
          />
      ))}
      
    </motion.div>
  );
}


