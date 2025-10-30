'use client';

import { motion } from 'framer-motion';
import { 
    Package, // Order
    Shield, // Security
    Banknote, // Payment
    BrainCircuit, // AI/System
    Check, 
    X, 
    Clock 
} from 'lucide-react';

const typeConfig = {
    order: { icon: Package, color: 'text-cyan-400' },
    security: { icon: Shield, color: 'text-amber-500' },
    payment: { icon: Banknote, color: 'text-green-400' },
    system: { icon: BrainCircuit, color: 'text-violet-400' },
    default: { icon: BrainCircuit, color: 'text-gray-500' }
};

const getIcon = (type: string) => {
    const config = typeConfig[type] || typeConfig.default;
    const IconComponent = config.icon;
    return <IconComponent className={config.color} size={20} />;
};

export function NotificationItem({ notification, isSelected, onSelect, onMarkAsRead, onDismiss, index }) {
    const { id, type, title, body, timestamp, read, cta } = notification;
    
    const borderColor = read 
        ? 'border-gray-800' 
        : (type === 'security' ? 'border-amber-500' : 'border-cyan-400');
    
    const glowClass = !read 
        ? (type === 'security' ? 'shadow-[0_0_15px_-3px_rgba(245,158,11,0.3)]' : 'shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)]')
        : '';

    const handleActionClick = (e, action) => {
        e.stopPropagation(); 
        action(id);
    };

    return (
       
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -50, transition: { duration: 0.2 } }}
            transition={{ delay: index * 0.07, duration: 0.3, ease: "easeOut" }} 
            onClick={onSelect}
            className={`group relative flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-all duration-300 border-l-2
                ${read ? 'opacity-70 hover:opacity-100 bg-black/20' : 'bg-white/5'}
                ${isSelected ? 'bg-white/10 ring-2 ring-cyan-500' : 'hover:bg-white/10'}
                ${borderColor} ${glowClass}
            `}
        >
            
            <div className="flex-shrink-0 mt-1">
                {getIcon(type)}
            </div>

            
            <div className="flex-1">
                <h3 className={`font-semibold ${read ? 'text-gray-300' : 'text-white'}`}>
                    {title}
                </h3>
                <p className="text-sm text-gray-400 mt-1 line-clamp-2">{body}</p>
                <span className="text-xs text-gray-500 mt-2 block">{timestamp}</span>
            </div>

            <div className="flex flex-col items-end gap-2 ml-4">
                {cta && (
                    <button 
                        onClick={(e) => e.stopPropagation()} 
                        className="px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap
                                   bg-cyan-400 text-black hover:bg-cyan-300 transition-colors"
                    >
                        {cta}
                    </button>
                )}
                
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 h-8">
                    {!read && (
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
                    <button 
                        onClick={(e) => handleActionClick(e, onDismiss)}
                        title="Dismiss" 
                        className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"
                    >
                        <X size={16} />
                    </button>
                </div>
            </div>
        </motion.div>
    );
}
