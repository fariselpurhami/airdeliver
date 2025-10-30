// apps/web/components/profile/EditProfileDetailsModal.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Loader2, User, Phone, MapPin } from 'lucide-react';

interface UserProfileData {
    full_name?: string | null;
    phone_number?: string | null;
    address?: string | null;
}

interface EditProfileDetailsModalProps {
    isOpen: boolean;
    onClose: () => void;
    userData: UserProfileData | undefined; 
    onSave: (updatedData: Partial<UserProfileData>) => Promise<void>; 
}

export default function EditProfileDetailsModal({
    isOpen,
    onClose,
    userData,
    onSave,
}: EditProfileDetailsModalProps) {
    const [fullName, setFullName] = useState(userData?.full_name || '');
    const [phoneNumber, setPhoneNumber] = useState(userData?.phone_number || '');
    const [address, setAddress] = useState(userData?.address || '');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && userData) {
            setFullName(userData.full_name || '');
            setPhoneNumber(userData.phone_number || '');
            setAddress(userData.address || '');
            setError(null);
        }
    }, [isOpen, userData]);

    const handleSave = async () => {
        setIsLoading(true);
        setError(null);
        const updatedData: Partial<UserProfileData> = {};
        if (fullName !== (userData?.full_name || '')) updatedData.full_name = fullName;
        if (phoneNumber !== (userData?.phone_number || '')) updatedData.phone_number = phoneNumber;
        if (address !== (userData?.address || '')) updatedData.address = address;

        if (Object.keys(updatedData).length === 0) {
             setIsLoading(false);
             onClose();
             return;
        }

        try {
            await onSave(updatedData);
            onClose(); 
        } catch (err: any) {
            setError(err.message || 'Failed to save profile details. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="fixed inset-0 z-[60] bg-black/20 backdrop-blur-md flex justify-center items-center p-4" 
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.95, opacity: 0, y: 30 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        onClick={(e) => e.stopPropagation()}
                        
                        className="w-full max-w-lg bg-black/20 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <header className="p-4 border-b border-white/10 flex justify-between items-center">
                            <h3 className="font-bold text-lg text-white flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <User size={18} className="text-cyan-400"/> Edit Profile Details
                            </h3>
                            <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <div className="p-6 space-y-5 max-h-[60vh] overflow-y-auto">
                            
                            <div>
                                <label htmlFor="fullName" className="block text-sm font-medium text-gray-400 mb-1">Full Name</label>
                                <input type="text" id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none"
                                    disabled={isLoading} />
                            </div>
                           
                            <div>
                                <label htmlFor="phoneNumber" className="block text-sm font-medium text-gray-400 mb-1">Phone Number</label>
                                <input type="tel" id="phoneNumber" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none"
                                    disabled={isLoading} />
                            </div>
                          
                            <div>
                                <label htmlFor="address" className="block text-sm font-medium text-gray-400 mb-1">Primary Address</label>
                                <textarea id="address" value={address} onChange={(e) => setAddress(e.target.value)} rows={3}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none resize-none"
                                    disabled={isLoading} />
                            </div>

                            {error && <p className="text-sm text-red-400 pt-1">{error}</p>}
                        </div>

                        <footer className="p-4 border-t border-white/10 flex justify-end gap-3">
                            <motion.button onClick={onClose} disabled={isLoading} className="px-4 py-2 text-sm rounded-lg text-gray-300 hover:bg-white/10 transition-colors" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                                Cancel
                            </motion.button>
                            <motion.button onClick={handleSave} disabled={isLoading} className="px-4 py-2 text-sm rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-semibold transition-colors flex items-center gap-2 disabled:opacity-50" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                                Save Profile
                            </motion.button>
                        </footer>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
