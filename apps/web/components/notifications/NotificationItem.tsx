'use client';

import { motion } from 'framer-motion';
import { Package, Shield, Tag, Bell, Check, X, Clock } from 'lucide-react';

// ... (function getIcon remains the same) ...
const getIcon = (type: string) => {
    switch (type) {
        case 'order': return <Package className="text-cyan-400" size={20} />;
        case 'security': return <Shield className="text-amber-500" size={20} />;
        case 'promotion': return <Tag className="text-violet-400" size={20} />;
        default: return <Bell className="text-gray-500" size={20} />;
    }
};

// ... (function getBorderColor remains the same) ...
const getBorderColor = (type: string, read: boolean) => {
    if (read) return 'border-gray-700/50';
    if (type === 'security') return 'border-amber-500';
    return 'border-cyan-400';
};

// +++ 1. Update Props type +++
export function NotificationItem({ notification, isSelected, onSelect, onMarkAsRead, onDismiss }) {
    const { id, type, title, body, timestamp, read, cta } = notification;
    
    const borderColor = getBorderColor(type, read);
    
    // +++ 2. Stop event propagation for clicks +++
    const handleActionClick = (e, action) => {
        e.stopPropagation(); // يمنع فتح الـ FocusPanel عند الضغط على زر
        action(id);
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -50, transition: { duration: 0.2 } }}
            onClick={onSelect}
            className={`group relative flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-all duration-300 border-l-2
                ${read ? 'opacity-70 hover:opacity-100' : 'bg-white/5'}
                ${isSelected ? 'bg-white/10 ring-2 ring-cyan-500' : 'hover:bg-white/10'}
                ${borderColor}
            `}
        >
            {/* ... (Icon and Content divs remain the same) ... */}
            <div className="flex-shrink-0 mt-1">
                {getIcon(type)}
            </div>
            <div className="flex-1">
                 <h3 className={`font-semibold ${read ? 'text-gray-300' : 'text-white'}`}>
                    {title}
                </h3>
                <p className="text-sm text-gray-400 mt-1">{body}</p>
                <div className="flex items-center gap-4 mt-2">
                    <span className="text-xs text-gray-500">{timestamp}</span>
                    {cta && (
                        <button 
                            // +++ 3. Add stopPropagation here too +++
                            onClick={(e) => e.stopPropagation()} 
                            className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
                        >
                            {cta}
                        </button>
                    )}
                </div>
            </div>

            {/* 3. Quick Actions (ربط الدوال) */}
            <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {!read && (
                    // +++ 4. Add onClick handler +++
                    <button 
                        onClick={(e) => handleActionClick(e, onMarkAsRead)}
                        title="Mark as read" 
                        className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"
                    >
                        <Check size={16} />
                    </button>
                )}
                <button title="Snooze" className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white">
                    <Clock size={16} />
                </button>
                {/* +++ 5. Add onClick handler +++ */}
                <button 
                    onClick={(e) => handleActionClick(e, onDismiss)}
                    title="Dismiss" 
                    className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"
                >
                    <X size={16} />
                </button>
            </div>
        </motion.div>
    );
}
