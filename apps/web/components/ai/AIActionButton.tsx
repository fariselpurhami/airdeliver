// apps/web/components/ai/AIActionButton.tsx

'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface AIActionButtonProps {
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  className?: string;
}

export const AIActionButton: React.FC<AIActionButtonProps> = ({
  onClick,
  variant = 'primary',
  children,
  className = '',
}) => {
  const baseStyle =
    'px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 ease-out-quad focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black/20';
  
  const primaryStyle =
    'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg hover:shadow-cyan-500/40';
  
  const secondaryStyle =
    'bg-gray-700/50 text-gray-300 hover:bg-gray-600/70 border border-gray-600/80';

  const style = variant === 'primary' ? primaryStyle : secondaryStyle;

  return (
    <motion.button
      onClick={onClick}
      className={`${baseStyle} ${style} ${className}`}
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 15 }}
    >
      {children}
    </motion.button>
  );
};
