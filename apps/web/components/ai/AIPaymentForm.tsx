//** apps/web/components/ai/AIPaymentForm.tsx **//

'use client';

import React, { useState, useEffect } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, AlertTriangle, ShieldCheck, CreditCard, ScanLine, Wallet, CheckCircle2, ArrowRight, Activity } from 'lucide-react';

interface AIPaymentFormProps {
  orderId: number;
  total: number;
  items: any[]; 
  onPaymentSuccess: () => void;
}

const SecurityBadge = () => (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
        <div className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </div>
        <span className="text-[10px] font-mono text-green-400 uppercase tracking-wider">Uplink Secure</span>
    </div>
);

export const AIPaymentForm: React.FC<AIPaymentFormProps> = ({ orderId, total, items, onPaymentSuccess }) => {
  const stripe = useStripe();
  const elements = useElements();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
      if (stripe && elements) {
          setIsReady(true);
      }
  }, [stripe, elements]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    
    const return_url = `${window.location.origin}/profile?payment_success=true&order_id=${orderId}`;

    try {
        const { error, paymentIntent } = await stripe.confirmPayment({
          elements,
          confirmParams: {
            return_url: return_url,
          },
          redirect: 'if_required' 
        });

        if (error) {
          setErrorMessage(error.message || "Transaction declined by gateway.");
        } else if (paymentIntent && paymentIntent.status === 'succeeded') {
            onPaymentSuccess();
        }
    } catch (e) {
        setErrorMessage("Network anomaly detected. Protocol terminated.");
    }
    
    setIsLoading(false);
  };

  if (!isReady) {
    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-12 gap-6 text-center">
             <div className="relative">
                <div className="w-16 h-16 border-2 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                    <Lock size={20} className="text-cyan-500/50" />
                </div>
             </div>
             <div className="space-y-1">
                <p className="text-cyan-300 font-mono text-sm tracking-widest animate-pulse">ESTABLISHING SECURE TUNNEL</p>
                <p className="text-xs text-cyan-500/50">Handshaking with Payment Gateway...</p>
             </div>
        </div>
    );
  }

  return (
    <motion.div 
      className="w-full max-w-lg mx-auto relative group"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
        <div className="absolute -inset-1 bg-gradient-to-b from-cyan-500/20 to-purple-500/20 rounded-[40px] blur-xl opacity-50 group-hover:opacity-75 transition-opacity duration-700" />
        
        <div className="relative bg-[#050505] backdrop-blur-3xl border border-white/10 rounded-[32px] overflow-hidden shadow-2xl">
            <div className="bg-gradient-to-b from-white/5 to-transparent p-8 pb-6 border-b border-white/5">
                <div className="flex justify-between items-start mb-4">
                    <div className="p-3 rounded-2xl bg-cyan-950/30 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
                        <CreditCard size={24} />
                    </div>
                    <SecurityBadge />
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Payment Terminal
                </h2>
                <div className="flex items-center gap-2 text-xs text-gray-500 font-mono">
                    <span>REF: {`ORD-${orderId.toString().padStart(6, '0')}`}</span>
                    <span>•</span>
                    <span className="text-cyan-500">AES-256 ENCRYPTED</span>
                </div>
            </div>

            <div className="p-8 pt-6">
                <div className="mb-8 rounded-2xl bg-white/[0.03] border border-white/5 p-4 relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500/50" />
                    <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                        <ScanLine size={12} /> Transaction Manifest
                    </div>
                    
                    <div className="space-y-2 max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 pr-2">
                        {items.length > 0 ? items.map((item: any, idx: number) => (
                            <div key={idx} className="flex justify-between text-sm group/item">
                                <span className="text-gray-300 truncate pr-4 group-hover/item:text-white transition-colors">
                                    {item.name} <span className="text-cyan-500/70 text-[10px]">x{item.quantity}</span>
                                </span>
                                <span className="text-white font-mono opacity-80">${(item.price * item.quantity).toFixed(2)}</span>
                            </div>
                        )) : (
                            <p className="text-gray-600 text-xs italic">Encrypted details hidden.</p>
                        )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/10 flex justify-between items-end">
                        <span className="text-xs text-gray-500 uppercase tracking-wider">Total Authorization</span>
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-black text-white tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                ${total.toFixed(2)}
                            </span>
                            <span className="text-xs text-gray-500 font-bold">USD</span>
                        </div>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-black/40 border border-white/10 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all duration-300">
                            <PaymentElement 
                                options={{ 
                                    layout: 'tabs',
                                    readOnly: isLoading,
                                }} 
                            />
                        </div>
                    </div>
                    
                    <AnimatePresence>
                        {errorMessage && (
                            <motion.div 
                                initial={{ opacity: 0, height: 0, y: -10 }}
                                animate={{ opacity: 1, height: 'auto', y: 0 }}
                                exit={{ opacity: 0, height: 0, y: -10 }}
                                className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs leading-relaxed"
                            >
                                <AlertTriangle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
                                <span>{errorMessage}</span>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <motion.button
                        disabled={isLoading || !stripe}
                        type="submit"
                        className="group w-full relative overflow-hidden rounded-xl bg-cyan-500 p-[1px] disabled:opacity-50 disabled:cursor-not-allowed"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <div className="relative h-full w-full rounded-[11px] bg-black px-6 py-4 transition-all duration-300 group-hover:bg-cyan-950/30">
                            <div className="absolute inset-0 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                            
                            <div className="relative flex items-center justify-center gap-3">
                                {isLoading ? (
                                    <>
                                        <Activity className="animate-pulse text-cyan-400" size={20} />
                                        <span className="font-bold text-cyan-100 tracking-widest uppercase text-sm">Processing...</span>
                                    </>
                                ) : (
                                    <>
                                        <span className="font-black text-white tracking-widest uppercase text-sm group-hover:text-cyan-200 transition-colors">
                                            Initiate Transfer
                                        </span>
                                        <div className="p-1 rounded-full bg-cyan-500/20 text-cyan-400 group-hover:translate-x-1 transition-transform">
                                            <ArrowRight size={16} />
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </motion.button>
                    
                    <div className="flex justify-center items-center gap-2 text-[10px] text-gray-600 font-mono uppercase tracking-widest">
                        <ShieldCheck size={12} className="text-gray-500" />
                        <span>Powered by Stripe • End-to-End Encryption</span>
                    </div>
                </form>
            </div>
        </div>
    </motion.div>
  );
};
