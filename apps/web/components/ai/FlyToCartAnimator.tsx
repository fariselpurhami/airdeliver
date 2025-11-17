// apps/web/components/ai/FlyToCartAnimator.tsx

'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

export const FlyToCartAnimator: React.FC = () => {
  const flyToCartItem = useAIOrderingStore((state) => state.flyToCartItem);
  const [item, setItem] = useState(flyToCartItem);

  useEffect(() => {
    if (flyToCartItem) {
      setItem(flyToCartItem);
    }
  }, [flyToCartItem]);

  const getStartPosition = () => {
    if (!item) return { x: 0, y: 0, width: 0, height: 0 };
    const el = document.getElementById(item.startElementId);
    if (el) {
      return el.getBoundingClientRect();
    }
    return { x: window.innerWidth / 2, y: window.innerHeight / 2, width: 100, height: 100 };
  };

  const getEndPosition = () => {
    const el = document.getElementById('order-summary-cart-icon');
    if (el) {
      const rect = el.getBoundingClientRect();
      return {
        top: rect.top + rect.height / 2,
        left: rect.left + rect.width / 2,
      };
    }
    return { top: 100, left: window.innerWidth - 100 };
  };

  const startRect = getStartPosition();
  const endPos = getEndPosition();

  return (
    <AnimatePresence>
      {item && startRect.width > 0 && (
        <motion.div
          key={item.id}
          className="fixed z-[9999] rounded-lg overflow-hidden border border-cyan-500/50"
          initial={{
            top: startRect.top,
            left: startRect.left,
            width: startRect.width,
            height: startRect.height,
            opacity: 1,
            rotate: 0,
          }}
          animate={{
            top: endPos.top,
            left: endPos.left,
            width: 20,
            height: 20,
            opacity: 0.5,
            rotate: 720,
            filter: 'blur(4px)',
            scale: 0.2,
          }}
          exit={{ opacity: 0 }}
          transition={{
            duration: 0.8,
            ease: [0.76, 0, 0.24, 1],
          }}
          onAnimationComplete={() => setItem(null)}
        >
          <img
            src={item.image}
            alt="product"
            className="w-full h-full object-cover"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};
