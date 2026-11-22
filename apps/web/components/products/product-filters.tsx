//** apps/web/components/products/Product-filters.tsx **//

'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, SlidersHorizontal, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/Button'; 
import { Input } from '@/components/ui/input'; 

const categories = ["All Systems", "Drones", "Pods", "Power Cells", "Upgrades"];

export const ProductFilters = () => {
  const [activeCategory, setActiveCategory] = useState("All Systems");

  return (
    <motion.div 
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut", delay: 0.5 }}
      className="sticky top-24 z-30 w-full max-w-4xl mx-auto px-4"
    >
      <div className="bg-black/60 backdrop-blur-2xl border border-white/10 rounded-full p-2 flex flex-col md:flex-row items-center gap-2 shadow-2xl shadow-cyan-900/10">
        
        <div className="relative w-full md:flex-grow group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-cyan-400 transition-colors" size={18} />
          <input 
            type="text"
            placeholder="Query Inventory..."
            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-transparent rounded-full text-white placeholder-gray-500 focus:bg-black/40 focus:border-cyan-500/30 focus:outline-none transition-all text-sm font-medium"
          />
        </div>
        
        <div className="flex gap-1 overflow-x-auto no-scrollbar py-1 px-1 max-w-full">
          {categories.map(cat => (
            <button 
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`whitespace-nowrap px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all duration-300 ${
                activeCategory === cat 
                ? 'bg-cyan-500 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)]' 
                : 'text-gray-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        
        <button className="p-3 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-colors border border-transparent hover:border-white/10">
          <SlidersHorizontal size={18} />
        </button>
      </div>
    </motion.div>
  );
};
