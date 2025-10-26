// file: apps/web/components/profile/ChangePasswordModal.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, KeyRound, Loader2, Eye, EyeOff } from 'lucide-react';

interface ChangePasswordModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (currentPassword: string, newPassword: string) => Promise<void>; // Async save handler
}

export default function ChangePasswordModal({
    isOpen,
    onClose,
    onSave,
}: ChangePasswordModalProps) {
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    // Reset fields when modal opens
    useEffect(() => {
        if (isOpen) {
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
            setError(null);
            setShowCurrent(false);
            setShowNew(false);
            setShowConfirm(false);
        }
    }, [isOpen]);

    const handleSave = async () => {
        if (newPassword !== confirmPassword) {
            setError("New passwords do not match.");
            return;
        }
        if (newPassword.length < 8) { // Basic validation
            setError("New password must be at least 8 characters long.");
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            await onSave(currentPassword, newPassword);
            onClose(); // Close modal on successful save
        } catch (err: any) {
            setError(err.message || 'Failed to change password. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const PasswordInput = ({ label, id, value, onChange, show, toggleShow }: any) => (
         <div className="relative">
            <label htmlFor={id} className="block text-sm font-medium text-gray-400 mb-1">
                {label}
            </label>
            <input
                type={show ? 'text' : 'password'}
                id={id}
                name={id}
                value={value}
                onChange={onChange}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 pr-10 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none"
                disabled={isLoading}
            />
            <button 
                type="button" 
                onClick={toggleShow} 
                className="absolute right-3 top-[34px] text-gray-500 hover:text-cyan-400"
                aria-label={show ? "Hide password" : "Show password"}
            >
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
        </div>
    );


    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="fixed inset-0 z-50 bg-black/20 backdrop-blur-md flex justify-center items-center p-4"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full max-w-md bg-black/20 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <header className="p-4 border-b border-white/10 flex justify-between items-center">
                            <h3 className="font-bold text-lg text-white flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <KeyRound size={18} className="text-cyan-400"/> Change Password
                            </h3>
                            <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <div className="p-6 space-y-4">
                            <PasswordInput 
                                label="Current Password" 
                                id="currentPassword" 
                                value={currentPassword} 
                                onChange={(e: any) => setCurrentPassword(e.target.value)} 
                                show={showCurrent} 
                                toggleShow={() => setShowCurrent(!showCurrent)} 
                            />
                            <PasswordInput 
                                label="New Password" 
                                id="newPassword" 
                                value={newPassword} 
                                onChange={(e: any) => setNewPassword(e.target.value)} 
                                show={showNew} 
                                toggleShow={() => setShowNew(!showNew)} 
                            />
                             <PasswordInput 
                                label="Confirm New Password" 
                                id="confirmPassword" 
                                value={confirmPassword} 
                                onChange={(e: any) => setConfirmPassword(e.target.value)} 
                                show={showConfirm} 
                                toggleShow={() => setShowConfirm(!showConfirm)} 
                            />
                            {error && <p className="text-sm text-red-400 pt-2">{error}</p>}
                        </div>

                        <footer className="p-4 border-t border-white/10 flex justify-end gap-3">
                            <motion.button onClick={onClose} disabled={isLoading} className="px-4 py-2 text-sm rounded-lg text-gray-300 hover:bg-white/10 transition-colors" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                                Cancel
                            </motion.button>
                            <motion.button onClick={handleSave} disabled={isLoading} className="px-4 py-2 text-sm rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-semibold transition-colors flex items-center gap-2 disabled:opacity-50" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <KeyRound size={16} />}
                                Update Password
                            </motion.button>
                        </footer>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
