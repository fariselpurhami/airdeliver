'use client';

import { motion } from 'framer-motion';

export function UndoToast({ message, onUndo }) {
    return (
        <motion.div
            layout
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            // يثبته أسفل الشاشة
            className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between gap-4 p-4 rounded-lg shadow-lg bg-gray-900 border border-cyan-400/30"
            style={{ backgroundColor: '#111' }} // لون أغمق قليلاً
        >
            <span className="text-gray-300 text-sm">{message}</span>
            <button
                onClick={onUndo}
                className="px-3 py-1 rounded-full text-sm font-semibold bg-cyan-400 text-black hover:bg-cyan-300 transition-colors"
            >
                Undo
            </button>
        </motion.div>
    );
}
