'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Lock,
    AlertTriangle,
    ShieldCheck,
    CreditCard,
    ScanLine,
    ArrowRight,
    Activity,
    CheckCircle2
} from 'lucide-react';

import { useStripe, useElements, PaymentElement } from '@stripe/react-stripe-js';

// ============================================================================
// LOADING & SUCCESS COMPONENTS
// ============================================================================

const PaymentLoadingState = React.memo(() => (
    <div className="w-full h-full flex items-center justify-center bg-transparent">
         <div className="w-8 h-8 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
    </div>
));
PaymentLoadingState.displayName = 'PaymentLoadingState';


const PaymentSuccessState = React.memo(() => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
        className="w-full h-full flex flex-col items-center justify-center p-12 gap-6 text-center bg-transparent"
     >
        <div className="w-24 h-24 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center text-green-400 mb-4 shadow-[0_0_30px_rgba(34,197,94,0.2)]">
            <CheckCircle2 size={40} />
        </div>
        <div>
            <h3 className="text-xl font-bold text-white mb-2 tracking-wide font-mono uppercase">Payment Authorized</h3>
            <p className="text-sm text-green-400 font-mono">Initializing Uplink Protocol...</p>
        </div>
     </motion.div>
));
PaymentSuccessState.displayName = 'PaymentSuccessState';

// ============================================================================
// MAIN AIPAYMENTFORM COMPONENT
// ============================================================================

interface Item {
    id: number | string;
    name: string;
    quantity: number;
    price: number;
}

interface AIPaymentFormProps {
    orderId: string | number;
    total: number;
    items: Item[];
    onPaymentSuccess: () => void;
    clientSecret?: string; // أضفنا ده عشان يمنع إيرور الفرونت
}

const AIPaymentForm = React.memo(({ orderId, total, items, onPaymentSuccess, clientSecret }: AIPaymentFormProps) => {
    const stripe = useStripe();
    const elements = useElements();

    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isReady, setIsReady] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            requestAnimationFrame(() => setIsReady(true));
        }, 1500); // قللنا الوقت لثانية ونص عشان مياخدش وقت طويل في التحميل الحقيقي
        return () => clearTimeout(timer);
    }, []);

    const handleSubmit = useCallback(async (event: React.FormEvent) => {
        event.preventDefault();

        if (!stripe || !elements || isLoading) {
            return;
        }

        setIsLoading(true);
        setErrorMessage(null);

        try {
            const { error, paymentIntent } = await stripe.confirmPayment({
                elements,
                redirect: 'if_required',
            });

            if (error) {
                setErrorMessage(error.message || "Transaction declined by gateway.");
            } else if (paymentIntent && paymentIntent.status === 'succeeded') {
                setIsSuccess(true);
                setTimeout(() => onPaymentSuccess(), 2000);
            }
        } catch (e) {
            setErrorMessage("Network anomaly detected. Protocol terminated.");
        } finally {
            setIsLoading(false);
        }
    }, [stripe, elements, isLoading, onPaymentSuccess]);

    // حماية إضافية لو الكلاينت سيكريت مش موجود
    if (!clientSecret) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center text-white p-4 text-center bg-transparent">
                <AlertTriangle size={48} className="text-yellow-500 mb-4" />
                <h2 className="text-xl font-bold font-mono">Missing Client Secret</h2>
            </div>
        );
    }

    if (!isReady) return <PaymentLoadingState />;
    if (isSuccess) return <PaymentSuccessState />;

    return (
        <motion.div
            className="w-full h-full flex flex-col relative transform-gpu bg-transparent"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
            {/* --- Header --- */}
            <div className="bg-gradient-to-b from-white/5 to-transparent p-6 border-b border-white/5 flex-shrink-0">
                <div className="flex justify-between items-start mb-4">
                    <div className="p-3 rounded-2xl bg-cyan-950/30 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
                        <CreditCard size={18} />
                    </div>
                </div>

                <h2 className="text-2xl font-medium uppercase text-white mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Secured Checkout
                </h2>
                <div className="flex items-center gap-2 text-xs text-gray-500 font-mono">
                    <span>REF: {`ORD-${orderId.toString().padStart(6, '0')}`}</span>
                </div>
            </div>

            {/* --- Body --- */}
            <div className="p-6 flex-grow overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 flex flex-col">

                {/* Manifest Block */}
                <div className="mb-6 rounded-2xl bg-white/[0.03] border border-white/5 p-4 relative overflow-hidden flex-shrink-0">
                    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500/50" />
                    <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                        <ScanLine size={12} /> Manifest
                    </div>

                    <div className="space-y-2 max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 pr-2">
                        {items.length > 0 ? items.map((item, idx) => (
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
                        <span className="text-xs text-gray-500 uppercase tracking-wider">Total</span>
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-black text-white tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                ${total.toFixed(2)}
                            </span>
                            <span className="text-xs text-gray-500 font-bold">USD</span>
                        </div>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col flex-grow">
                    <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-black/40 border border-white/10 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all duration-300">
                            <PaymentElement options={{ layout: 'tabs', readOnly: isLoading }} />
                        </div>
                    </div>

                    <AnimatePresence>
                        {errorMessage && (
                            <motion.div
                                initial={{ opacity: 0, height: 0, y: -10 }}
                                animate={{ opacity: 1, height: 'auto', y: 0 }}
                                exit={{ opacity: 0, height: 0, y: -10 }}
                                className="flex items-start gap-3 p-4 mt-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs leading-relaxed"
                            >
                                <AlertTriangle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
                                <span>{errorMessage}</span>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Airpay Button - Pushed to bottom */}
                    <div className="mt-auto pt-6">
                        <motion.button
                            disabled={isLoading || !isReady || !stripe || !elements}
                            type="submit"
                            className="group w-full relative overflow-hidden rounded-xl bg-cyan-500 p-[1px] disabled:opacity-50 disabled:cursor-not-allowed"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <div className="relative h-full w-full rounded-[11px] bg-black px-6 py-4 transition-all duration-300 group-hover:bg-cyan-950/30">
                                <div className="absolute inset-0 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                                <div className="relative flex items-center justify-center gap-3">
                                    {isLoading ? (
                                        <div className="flex items-center justify-center">
                                            <svg className="animate-spin h-5 w-5 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                               <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                               <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                           </svg>
                                       </div>
                                   ) : (
                                        <>
                                            <span className="font-black text-white tracking-widest text-sm group-hover:text-cyan-200 transition-colors">
                                                PAY ${(total).toFixed(2)}
                                            </span>
                                            <div className="p-1 rounded-full bg-cyan-500/20 text-cyan-400 group-hover:translate-x-1 transition-transform">
                                                <ArrowRight size={16} />
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </motion.button>

                        <div className="flex justify-center items-center gap-2 mt-4 text-[10px] text-gray-600 font-mono uppercase tracking-widest pb-2">
                            <ShieldCheck size={12} className="text-gray-500" />
                            <span>Powered by Stripe • End-to-End Encryption</span>
                        </div>
                    </div>
                </form>
            </div>
        </motion.div>
    );
});

AIPaymentForm.displayName = 'AIPaymentForm';
export default AIPaymentForm;
