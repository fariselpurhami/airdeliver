'use client';

import { Settings, CheckCheck, BellOff, ListFilter } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

const filters = ['All', 'Unread', 'Orders', 'Security'];

export function ControlBar({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="sticky top-20 z-10 flex flex-col sm:flex-row justify-between items-center py-4 px-3 rounded-lg bg-black/50 backdrop-blur-md border-b border-white/10">
      
      <div className="relative w-full sm:w-auto text-center sm:text-left mb-4 sm:mb-0">
        <div className="flex items-center justify-center sm:justify-start gap-3">
          <h1 className="text-3xl font-bold" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            Notifications
          </h1>
          {unreadCount > 0 && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-400 text-black text-sm font-bold"
            >
              {unreadCount}
            </motion.div>
          )}
        </div>
        <div className="glow-line-animation" />
      </div>

      <div 
        className="flex items-center gap-2 pb-2 sm:pb-0 overflow-x-auto sm:overflow-x-visible 
                   whitespace-nowrap sm:whitespace-normal sm:flex-wrap sm:justify-center"
      >
        {filters.map(filter => (
          <button
            key={filter}
            onClick={() => onFilterChange(filter)}
            className={`group relative px-4 py-2 rounded-full text-sm font-medium transition-colors duration-300
                ${activeFilter === filter 
                    ? 'text-black' 
                    : 'text-gray-300 bg-white/5 hover:bg-white/10 hover:text-white'
                }`}
          >
            {activeFilter === filter ? (
          
              <motion.div
                layoutId="active-notification-pill"
                className="absolute inset-0 bg-cyan-400 rounded-full"
                style={{ borderRadius: 9999 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            ) : (
              
              <motion.div
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 blur-[2px] opacity-0 
                           group-hover:opacity-100 transition-opacity"
              />
            )}
            <span className="relative z-10">{filter}</span>
          </button>
        ))}
      </div>

      
      <div className="relative hidden lg:flex items-center gap-2">
        <button 
          onClick={() => setMenuOpen(!menuOpen)} 
          className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <Settings size={18} />
        </button>

        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="absolute top-12 right-0 w-60 bg-gray-900 border border-white/10 rounded-lg shadow-xl z-50 p-2"
              style={{ backgroundColor: '#050505' }} 
            >
              <button className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <BellOff size={16} />
                <span>Pause notifications</span>
              </button>
              <button className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <ListFilter size={16} />
                <span>Notification preferences</span>
              </button>
              <div className="h-px bg-white/10 my-1"></div>
              <button 
                onClick={() => {
                  onMarkAllAsRead();
                  setMenuOpen(false);
                }}
                className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                <CheckCheck size={18} />
                <span>Mark all as read</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
    </div>
  );
}
