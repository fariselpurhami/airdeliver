'use client';

import { Bell } from 'lucide-react';
import { motion } from 'framer-motion';

export function CinematicEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center text-center p-16 rounded-lg 
                 border border-white/10 relative overflow-hidden
                 bg-gradient-to-t from-cyan-500/5 via-black/0 to-black/0"
    >
      
      <motion.div
        animate={{ scale: [1, 1.05, 1], opacity: [1, 0.8, 1] }}
        transition={{ 
          repeat: Infinity, 
          duration: 6, 
          ease: "easeInOut" 
        }}
        className="relative mb-6"
      >
        
        <div className="absolute inset-0 bg-cyan-400 rounded-full blur-xl opacity-50"></div>
       
        <Bell size={48} className="text-cyan-300 relative z-10" />
      </motion.div>
      
      <h3 
        className="text-xl font-bold text-white mb-2 leading-tight"
        style={{ fontFamily: "'Orbitron', sans-serif" }}
      >
        You’re all caught up
      </h3>
      <p className="text-gray-400 max-w-xs opacity-60"> 
        No notifications at the moment.
        <br />
        Stay tuned, updates appear here in real time.
      </p>
    </motion.div>
  );
}
