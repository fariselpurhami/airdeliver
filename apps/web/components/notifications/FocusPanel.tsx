'use client';

import { motion } from 'framer-motion';
import { X, Shield, Package } from 'lucide-react';

// دي مجرد نسخة مبدئية جداً عشان نملى المكان
export function FocusPanel({ notification, onClose }) {
    
    return (
        <motion.div
            layout
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            // الـ sticky ده عشان يفضل ثابت مكانه لو القائمة الشمال أطول
            className="sticky top-40 p-5 rounded-lg bg-white/5 border border-white/10 backdrop-blur-lg"
        >
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                    {notification.type === 'order' && <Package size={18} className="text-cyan-400" />}
                    {notification.type === 'security' && <Shield size={18} className="text-amber-500" />}
                    <h2 className="text-lg font-semibold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Details
                    </h2>
                </div>
                <button onClick={onClose} className="p-1 rounded-full hover:bg-white/10">
                    <X size={20} />
                </button>
            </div>

            <div className="space-y-4">
                <h3 className="text-xl font-medium text-white">{notification.title}</h3>
                <p className="text-gray-300">{notification.body}</p>
                <span className="text-sm text-gray-500">{notification.timestamp}</span>
                
                {/* الأزرار الأساسية */}
                {notification.cta && (
                     <button className="w-full px-4 py-3 rounded-lg text-sm font-semibold transition-colors bg-cyan-400 text-black hover:bg-cyan-300">
                        {notification.cta}
                    </button>
                )}
                <button className="w-full px-4 py-3 rounded-lg text-sm font-semibold transition-colors bg-white/10 text-white hover:bg-white/20">
                    Manage 'Security' Alerts
                </button>
            </div>
        </motion.div>
    );
}
