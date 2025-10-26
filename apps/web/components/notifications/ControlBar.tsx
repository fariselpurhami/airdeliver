'use client';

import { Settings, CheckCheck } from 'lucide-react';
import { motion } from 'framer-motion';

const filters = ['All', 'Unread', 'Orders', 'Security'];

// +++ 1. Update Props type +++
export function ControlBar({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead }) {
    return (
        <div className="sticky top-20 z-10 flex flex-col sm:flex-row justify-between items-center py-4 px-3 rounded-lg bg-black/50 backdrop-blur-md border-b border-white/10">
            
            {/* ... (Left: Title + Unread Count remains the same) ... */}
            <div className="flex items-center gap-3 mb-4 sm:mb-0">
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

            {/* ... (Center: Filter Pills remains the same) ... */}
            <div className="flex items-center gap-2 flex-wrap justify-center">
                {filters.map(filter => (
                    <button
                        key={filter}
                        onClick={() => onFilterChange(filter)}
                        className={`relative px-4 py-2 rounded-full text-sm font-medium transition-colors duration-300
                            ${activeFilter === filter 
                                ? 'text-black' 
                                : 'text-gray-300 bg-white/5 hover:bg-white/10 hover:text-white'
                            }`}
                    >
                        {activeFilter === filter && (
                            <motion.div
                                layoutId="active-notification-pill"
                                className="absolute inset-0 bg-cyan-400 rounded-full"
                                style={{ borderRadius: 9999 }}
                                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            />
                        )}
                        <span className="relative z-10">{filter}</span>
                    </button>
                ))}
            </div>

            {/* Right: Global Actions */}
            <div className="hidden lg:flex items-center gap-2">
                {/* +++ 2. Add onClick handler +++ */}
                <button 
                    onClick={onMarkAllAsRead}
                    className="flex items-center gap-2 p-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                >
                    <CheckCheck size={18} />
                    Mark all as read
                </button>
                <button className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors">
                    <Settings size={18} />
                </button>
            </div>
        </div>
    );
}
