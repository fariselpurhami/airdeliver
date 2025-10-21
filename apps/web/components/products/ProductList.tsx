// file: components/products/Productlist.tsx (النسخة المعدلة لدعم فتح التفاصيل)
'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProductCard, type Product } from './ProductCard'; // استيراد الكارت الأساسي
import { ProductDetailsCard } from './ProductDetailsCard'; // <-- سننشئ هذا المكون الجديد

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1, // حركة ظهور متتالية للكروت
    },
  },
};

export default function ProductList({ products }: { products: Product[] }) {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const handleOpen = (product: Product) => {
    setSelectedProduct(product);
    // منع الـ scroll في الخلفية
    document.body.style.overflow = 'hidden';
  };

  const handleClose = () => {
    setSelectedProduct(null);
    // إعادة تفعيل الـ scroll
    document.body.style.overflow = '';
  };

  return (
    <>
      <motion.div
        variants={listVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
      >
        {products.map((product, index) => (
          <ProductCard
            key={product.id}
            product={product}
            priority={index < 4} // تحميل أول 4 صور بـ priority
            onOpen={handleOpen}
          />
        ))}
      </motion.div>

      {/* --- الـ Overlay والكارت المفصل --- */}
      <AnimatePresence>
        {selectedProduct && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            // الضغط على الخلفية يغلق الكارت
            onClick={handleClose}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex justify-center items-center p-4"
          >
            {/* نمنع إغلاق الكارت عند الضغط عليه مباشرة */}
            <div onClick={(e) => e.stopPropagation()}>
               {/* استخدام مكون جديد لعرض التفاصيل */}
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
