'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/Button'; 
import { Input } from '@/components/ui/input'; 

const categories = ["All", "Drones", "Pods", "Power Cells", "Accessories"];

export const ProductFilters = () => {
  const [activeCategory, setActiveCategory] = useState("All");

  return (
    <motion.div 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="sticky top-24 z-30 w-full max-w-5xl mx-auto"
    >
      <div className="bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl p-4 flex flex-col md:flex-row items-center gap-4 shadow-2xl shadow-cyan-500/10">
        
        <div className="relative w-full md:flex-grow">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
          <Input 
            type="text"
            placeholder="Ask AI to find your perfect item..."
            className="w-full pl-11 pr-4 py-3 bg-black/20 border border-cyan-400/30 rounded-lg text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-0 focus-visible:ring-offset-black/10"
          />
        </div>
        
        <div className="flex gap-2 overflow-x-auto">
          {categories.map(cat => (
            <Button 
              key={cat}
              onClick={() => setActiveCategory(cat)}
              variant="ghost"
              className={`rounded-full px-5 transition-all duration-300 ${
                activeCategory === cat 
                ? 'bg-cyan-500/30 text-cyan-200 border border-cyan-500/50' 
                : 'text-gray-400 hover:bg-white/10 hover:text-white'
              }`}
            >
              {cat}
            </Button>
          ))}
        </div>
        
        <Button variant="ghost" className="rounded-full text-gray-400 hover:bg-white/10 hover:text-white">
          <SlidersHorizontal size={16} className="mr-2" /> Sort
        </Button>
      </div>
    </motion.div>
  );
};
