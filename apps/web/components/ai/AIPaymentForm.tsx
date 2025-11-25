// apps/web/components/ai/AIPaymentForm.tsx

import React, { useState } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { motion } from 'framer-motion';
import { Lock, AlertTriangle, ShieldCheck, CreditCard } from 'lucide-react';

interface AIPaymentFormProps {
  orderId: number;
  total: number;
  items: any[]; 
  onPaymentSuccess: () => void;
}

export const AIPaymentForm: React.FC<AIPaymentFormProps> = ({ orderId, total, items, onPaymentSuccess }) => {
  const stripe = useStripe();
  const elements = useElements();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isStripeReady = stripe && elements; 

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!isStripeReady) {
      setErrorMessage("Payment processor is initializing. Please wait.");
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
          if (error.type === "card_error" || error.type === "validation_error") {
            setErrorMessage(error.message || "Payment details invalid.");
          } else {
            setErrorMessage("Payment processing failed. Please try again.");
          }
        } else if (paymentIntent && paymentIntent.status === 'succeeded') {
            onPaymentSuccess();
        }
    } catch (e) {
        setErrorMessage("An unexpected network error occurred.");
    }
    
    setIsLoading(false);
  };

  if (!isStripeReady) {
    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-10 gap-4">
             <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(6,182,212,0.5)]" />
             <p className="text-cyan-300 font-mono animate-pulse">Securing Connection...</p>
        </div>
    );
  }

  return (
    <motion.div 
      className="w-full max-w-lg mx-auto p-8 bg-slate-900/95 backdrop-blur-xl rounded-3xl border border-cyan-500/30 shadow-2xl shadow-cyan-500/20 text-white"
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <div className="flex flex-col items-center mb-8">
        <div className="w-12 h-12 bg-cyan-500/10 rounded-full flex items-center justify-center mb-3 border border-cyan-500/30">
            <ShieldCheck size={24} className="text-cyan-400" />
        </div>
        <h2 
          className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500" 
          style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
          Secure Checkout
        </h2>
        <p className="text-gray-400 text-sm mt-1">Encryption Level: AES-256 • Order #{orderId}</p>
      </div>

      <div className="mb-8 space-y-3 p-5 bg-black/40 border border-white/10 rounded-2xl">
        <div className="flex items-center gap-2 text-gray-300 mb-2 pb-2 border-b border-white/10">
            <CreditCard size={16} />
            <span className="text-xs font-semibold uppercase tracking-wider">Transaction Summary</span>
        </div>
        <div className="max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-900 pr-2">
            {items && items.length > 0 ? (
            items.map((item: any, idx: number) => (
                <div key={item.product_id || idx} className="flex justify-between items-center text-sm mb-2 last:mb-0">
                    <span className="text-gray-300 truncate pr-4">{item.name} <span className="text-cyan-500 text-xs">x{item.quantity}</span></span>
                    <span className="text-white font-mono">${(item.price * item.quantity).toFixed(2)}</span>
                </div>
            ))
            ) : (
            <p className="text-gray-500 text-xs italic text-center">Order details hidden for security.</p>
            )}
        </div>
        
        <div className="pt-3 border-t border-white/10 flex justify-between items-end">
            <span className="text-gray-400 text-sm">Total Amount</span>
            <motion.p 
              className="text-3xl font-bold text-white"
              style={{ fontFamily: "'Orbitron', sans-serif", textShadow: '0 0 20px rgba(6, 182, 212, 0.3)' }}
            >
              ${total.toFixed(2)}
            </motion.p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
       
        <div className="p-1 rounded-xl transition-all focus-within:ring-2 focus-within:ring-cyan-500/50 focus-within:shadow-[0_0_20px_rgba(6,182,212,0.2)]">
          <PaymentElement 
            options={{ 
                layout: 'tabs',
            }} 
          />
        </div>
        
        {errorMessage && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="flex items-start gap-3 text-red-200 text-sm p-4 rounded-xl bg-red-900/20 border border-red-500/30"
          >
            <AlertTriangle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </motion.div>
        )}

        <motion.button
          disabled={isLoading || !isStripeReady}
          type="submit"
          className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-cyan-900/20 hover:shadow-cyan-500/40 hover:from-cyan-500 hover:to-blue-500 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none group"
          style={{ fontFamily: "'Orbitron', sans-serif", letterSpacing: '0.05em' }}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/80 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Lock size={18} className="text-cyan-100 group-hover:text-white transition-colors" />
          )}
          <span>{isLoading ? 'Processing Payment...' : `Pay $${total.toFixed(2)}`}</span>
        </motion.button>
        
        <div className="flex justify-center items-center gap-2 text-xs text-gray-500 mt-4">
            <Lock size={10} />
            <span>Payments processed securely by Stripe. No card data stored.</span>
        </div>
      </form>
    </motion.div>
  );
};
