// file: apps/web/components/profile/EditProfileModal.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Loader2 } from 'lucide-react';

interface EditProfileModalProps {
    isOpen: boolean;
    onClose: () => void;
    fieldName: string; // e.g., 'full_name', 'phone_number'
    label: string; // e.g., 'Full Name', 'Phone Number'
    currentValue: string | null | undefined;
    onSave: (fieldName: string, newValue: string) => Promise<void>; // Async save handler
}

export default function EditProfileModal({
    isOpen,
    onClose,
    fieldName,
    label,
    currentValue,
    onSave,
}: EditProfileModalProps) {
    const [value, setValue] = useState(currentValue || '');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Reset value when modal opens with a new field
    useEffect(() => {
        if (isOpen) {
            setValue(currentValue || '');
            setError(null); // Clear previous errors
        }
    }, [isOpen, currentValue]);

    const handleSave = async () => {
        setIsLoading(true);
        setError(null);
        try {
            await onSave(fieldName, value);
            onClose(); // Close modal on successful save
        } catch (err: any) {
            setError("Your changes could not be saved. Check the current details before trying again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-center items-center p-4"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full max-w-md bg-black/50 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <header className="p-4 border-b border-white/10 flex justify-between items-center">
                            <h3 className="font-bold text-lg text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                Edit {label}
                            </h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </header>

                        <div className="p-6 space-y-4">
                            <label htmlFor={fieldName} className="block text-sm font-medium text-gray-400">
                                {label}
                            </label>
                            <input
                                type={fieldName === 'email' ? 'email' : 'text'} // Basic type handling
                                id={fieldName}
                                name={fieldName}
                                value={value}
                                onChange={(e) => setValue(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none"
                                placeholder={`Enter your ${label.toLowerCase()}`}
                                disabled={isLoading}
                            />
                            {error && <p className="text-sm text-red-400 mt-1">{error}</p>}
                        </div>

                        <footer className="p-4 border-t border-white/10 flex justify-end gap-3">
                            <motion.button
                                onClick={onClose}
                                disabled={isLoading}
                                className="px-4 py-2 text-sm rounded-lg text-gray-300 hover:bg-white/10 transition-colors"
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                            >
                                Cancel
                            </motion.button>
                            <motion.button
                                onClick={handleSave}
                                disabled={isLoading}
                                className="px-4 py-2 text-sm rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-semibold transition-colors flex items-center gap-2 disabled:opacity-50"
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                            >
                                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                                Save Changes
                            </motion.button>
                        </footer>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
