'use client';

import { motion } from 'framer-motion';
import { Search, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button'; // Assuming shadcn Button
import { Input } from '@/components/ui/input'; // Assuming shadcn Input

const categories = ["All", "Drones", "Pods", "Power Cells", "Accessories"];

export const ProductFilters = () => {
  return (
    <motion.div 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="sticky top-24 z-30 w-full max-w-5xl mx-auto"
    >
      <div className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col md:flex-row items-center gap-4">
        {/* AI Search */}
        <div className="relative w-full md:flex-grow">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
          <Input 
            type="text"
            placeholder="Ask AI to find your perfect item..."
            className="w-full pl-10 pr-4 py-2 bg-white/5 border-none rounded-lg text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
          />
        </div>
        
        {/* Category Chips */}
        <div className="flex gap-2 overflow-x-auto">
          {categories.map(cat => (
            <Button 
              key={cat}
              variant="ghost"
              className="rounded-full text-gray-300 hover:bg-white/10 hover:text-white transition-all duration-300"
            >
              {cat}
            </Button>
          ))}
        </div>
        
        {/* Sorting (simplified) */}
        <Button variant="ghost" className="rounded-full text-gray-300 hover:bg-white/10 hover:text-white">
          <SlidersHorizontal size={16} className="mr-2" /> Sort
        </Button>
      </div>
    </motion.div>
  );
};
