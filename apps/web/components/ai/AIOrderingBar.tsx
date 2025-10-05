// file: apps/web/components/ai/AIOrderingBar.tsx
// version: 1.0.0
// date: 2025-09-27
// author: Gemini

'use client';

import { FiZap } from 'react-icons/fi';
import { motion } from 'framer-motion';

interface AIOrderingBarProps {
  onClick: () => void;
}

export const AIOrderingBar = ({ onClick }: AIOrderingBarProps) => {
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40">
      <motion.button
        onClick={onClick}
        className="flex items-center gap-2 px-6 py-3 bg-foreground text-background rounded-full shadow-lg hover:bg-foreground/80 transition-colors"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Order with AI"
      >
        <FiZap />
        <span>Order with AI</span>
      </motion.button>
    </div>
  );
};
