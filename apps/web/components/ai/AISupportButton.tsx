"use client";

import { Bot, X } from 'lucide-react';
import { useAISupportStore } from '@/hooks/useAISupportStore';
import { motion } from 'framer-motion';

export const AISupportButton = () => {
  
  const { isOpen, setIsOpen } = useAISupportStore();

  return (
    <motion.button
      onClick={() => setIsOpen(!isOpen)}
      className="fixed bottom-6 right-6 z-50 p-4 rounded-full 
                 bg-gradient-to-br from-cyan-500 to-purple-600 
                 text-white shadow-lg shadow-cyan-500/40 
                 flex items-center justify-center 
                 focus:outline-none focus:ring-4 focus:ring-cyan-400/50 
                 hover:scale-110 transition-all duration-300 ease-in-out group"
      whileHover={{ scale: 1.1, rotate: 5 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
      aria-label="Toggle AI Support Chat"
    >
      <motion.div
        key={isOpen ? "close-icon" : "bot-icon"}
        initial={{ scale: 0, rotate: -90 }}
        animate={{ scale: 1, rotate: 0 }}
        exit={{ scale: 0, rotate: 90 }}
        transition={{ type: "spring", stiffness: 200, damping: 20 }}
      >
        {isOpen ? (
          <X size={28} className="text-white group-hover:rotate-180 transition-transform duration-300" />
        ) : (
          <Bot size={28} className="text-white group-hover:scale-110 transition-transform duration-300" />
        )}
      </motion.div>
    </motion.button>
  );
};
