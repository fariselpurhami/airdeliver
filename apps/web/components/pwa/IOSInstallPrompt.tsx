'use client';
import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { Share, PlusSquare, X, Rocket } from 'lucide-react';

export const IOSInstallPrompt = memo(({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  if (!isOpen) return null;

  return (
    <div id="ios-install-prompt" className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center px-4 pb-8 sm:p-0 pointer-events-none" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm pointer-events-auto"
      />
      
      <motion.div
        initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="relative w-full max-w-sm bg-zinc-900 border border-white/10 rounded-3xl p-6 shadow-2xl pointer-events-auto"
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white bg-zinc-800 rounded-full p-1.5 transition-colors">
          <X size={18} />
        </button>

        <div className="flex flex-col items-center text-center mt-2">
          <div className="w-16 h-16 bg-gradient-to-tr from-cyan-500 to-purple-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-cyan-500/20">
            <Rocket size={32} className="text-white" />
          </div>
          
          <h3 className="text-xl font-bold text-white mb-2 font-sans tracking-tight">Install airdeliver app</h3>
          <p className="text-sm text-gray-400 mb-6 font-light">Install our native app for the best ordering experience.</p>

          <div className="w-full bg-black/50 rounded-2xl p-4 border border-white/5 space-y-4 text-left">
            <div className="flex items-center gap-4">
              <div className="bg-zinc-800 p-2 rounded-xl text-blue-400"><Share size={20} /></div>
              <p className="text-sm text-gray-300">1. Tap <span className="font-bold text-white">Share</span> in Safari menu.</p>
            </div>
            <div className="w-px h-4 bg-white/10 ml-6" />
            <div className="flex items-center gap-4">
              <div className="bg-zinc-800 p-2 rounded-xl text-gray-300"><PlusSquare size={20} /></div>
              <p className="text-sm text-gray-300">2. Tap <span className="font-bold text-white">Add to Home Screen</span>.</p>
            </div>
          </div>
          
          <button onClick={onClose} className="mt-6 w-full py-3 rounded-full bg-white/10 text-white font-medium hover:bg-white/20 transition-colors">
            Got it
          </button>
        </div>
      </motion.div>
    </div>
  );
});
IOSInstallPrompt.displayName = 'IOSInstallPrompt';
