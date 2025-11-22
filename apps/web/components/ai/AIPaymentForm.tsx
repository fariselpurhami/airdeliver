// apps/web/components/ai/AIPaymentForm.tsx

import React, { useState } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { motion } from 'framer-motion';
import { Lock, AlertTriangle } from 'lucide-react';

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
        <div className="w-full h-full flex items-center justify-center p-10">
             <div className="w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
    );
  }
  // 👆👆👆 End Fix 👆👆👆

  return (
    <motion.div 
      className="w-full max-w-lg mx-auto p-6 text-white"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="text-center mb-6">
        <h2 
          className="text-3xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500" 
          style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
          Authorize Payment
        </h2>
        <p className="text-gray-400 text-base">Order ID: #{orderId}</p>
      </div>

      <div className="mb-6 space-y-2 p-4 bg-black/20 border border-cyan-400/20 rounded-lg">
        <div className="max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-900">
            {items && items.length > 0 ? (
            items.map((item: any, idx: number) => (
                <div key={item.product_id || idx} className="flex justify-between items-center text-sm mb-1">
                <span className="text-gray-300">{item.name} <span className="text-gray-500">x{item.quantity}</span></span>
                <span className="text-white font-medium">${(item.price * item.quantity).toFixed(2)}</span>
                </div>
            ))
            ) : (
            <p className="text-gray-400 text-sm italic text-center">Order details encrypted.</p>
            )}
        </div>
        
        <div className="!mt-4 pt-4 border-t border-cyan-400/20 flex justify-between items-center">
            <span className="text-white font-bold text-lg">Total Amount</span>
            <motion.p 
              className="text-3xl font-extrabold text-cyan-300"
              style={{ fontFamily: "'Orbitron', sans-serif", filter: 'drop-shadow(0 0 10px rgba(6, 182, 212, 0.5))' }}
            >
              ${total.toFixed(2)}
            </motion.p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-4 bg-black/40 rounded-xl border border-cyan-400/30 backdrop-blur-sm transition-all focus-within:border-cyan-400/80 focus-within:shadow-[0_0_15px_rgba(6,182,212,0.3)]">
          <PaymentElement options={{ layout: 'tabs' }} />
        </div>
        
        {errorMessage && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-red-300 text-sm p-3 rounded-lg bg-red-900/20 border border-red-500/30"
          >
            <AlertTriangle size={16} />
            <span>{errorMessage}</span>
          </motion.div>
        )}

        <motion.button
          disabled={isLoading || !isStripeReady}
          type="submit"
          className="w-full flex items-center justify-center gap-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold py-4 rounded-xl shadow-lg hover:shadow-cyan-500/40 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
          style={{ fontFamily: "'Orbitron', sans-serif", letterSpacing: '0.05em' }}
          whileHover={{ scale: 1.02, shadow: '0 0 20px rgba(6, 182, 212, 0.6)' }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Lock size={16} />
          )}
          <span>{isLoading ? 'Processing Securely...' : 'Authorize Transaction'}</span>
        </motion.button>
      </form>
    </motion.div>
  );
};
