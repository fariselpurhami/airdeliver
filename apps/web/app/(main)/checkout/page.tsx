'use client';

import { CalendarDays } from 'lucide-react';
import React from 'react';
import { motion } from 'framer-motion';
import { Lock, CreditCard, User, MapPin } from 'lucide-react';
import { Button } from '@/components/ui/Button'; 
import { Input } from '@/components/ui/input'; 

const FuturisticInput = ({ icon, ...props }: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) => (
    <div className="relative">
        <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500">{icon}</div>
        <Input {...props} className="w-full bg-white/5 border-white/10 rounded-lg py-6 pl-12 pr-4 text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-0 focus-visible:ring-offset-transparent" />
    </div>
);

export default function CheckoutPage() {
    return (
        <main className="min-h-screen w-full bg-black text-gray-100 flex items-center justify-center p-4">
            <div className="absolute inset-0 -z-10 bg-grid-white/[0.05]" />

            <motion.div
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                className="w-full max-w-lg"
            >
                <div className="relative p-8 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50">
                    <div className="text-center mb-8">
                        <h1 className="text-4xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Launch Sequence</h1>
                        <p className="text-gray-400 mt-2">Authorize payment to deploy your autonomous fleet.</p>
                    </div>

                    <form className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-300 border-b border-white/10 pb-2">Contact Information</h2>
                        <FuturisticInput icon={<User size={18} />} type="text" placeholder="Full Name" />
                        <FuturisticInput icon={<MapPin size={18} />} type="text" placeholder="Delivery Address" />
                        
                        <h2 className="text-lg font-semibold text-gray-300 border-b border-white/10 pb-2 pt-4">Payment Details</h2>
                        <FuturisticInput icon={<CreditCard size={18} />} type="text" placeholder="Card Number" />
                        <div className="grid grid-cols-2 gap-4">
                            <FuturisticInput icon={<CalendarDays size={18} />} type="text" placeholder="MM / YY" />
                            <FuturisticInput icon={<Lock size={18} />} type="text" placeholder="CVC" />
                        </div>

                        <div className="pt-6">
                            <motion.button
                                type="submit"
                                whileHover={{ scale: 1.02, boxShadow: "0 0 25px 5px rgba(0, 198, 255, 0.4)" }}
                                whileTap={{ scale: 0.98 }}
                                className="w-full glowing-button rounded-full py-3 text-lg font-bold"
                            >
                                Authorize & Launch Fleet
                            </motion.button>
                        </div>
                    </form>
                </div>
            </motion.div>
        </main>
    );
}
