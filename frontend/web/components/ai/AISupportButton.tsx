"use client";

import { Bot, X } from "lucide-react";
import { useAISupportStore } from "@/hooks/useAISupportStore";
import { motion } from "framer-motion";

export const AISupportButton = () => {
  const { isOpen, setIsOpen } = useAISupportStore();

  return (
    <motion.button
      onClick={() => setIsOpen(!isOpen)}
      className="fixed bottom-6 right-6 z-50 size-9 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 text-white shadow-md shadow-cyan-500/20 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-cyan-400/30 transition-all duration-200 ease-out group"
      whileHover={{ scale: 1.04, rotate: 3 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
      aria-label="Toggle AI Support Chat"
    >
      {isOpen ? <X className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
    </motion.button>
  );
};
