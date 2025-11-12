import React, { useState } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { motion } from 'framer-motion';
import { Lock } from 'lucide-react';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

interface AIPaymentFormProps {
  orderId: number;
  total: number;
  items: any[]; 
  onPaymentSuccess: () => void;
}

export const AIPaymentForm: React.FC<AIPaymentFormProps> = ({ orderId, total, items, onPaymentSuccess }) => {
  const stripe = useStripe();
  const elements = useElements();
  const resetChat = useAIOrderingStore((state) => state.resetChat);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    
    const return_url = `${window.location.origin}/profile?payment_success=true&order_id=${orderId}`;

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: return_url,
      },
    });

    if (error.type === "card_error" || error.type === "validation_error") {
      setErrorMessage(error.message || "An error occurred.");
    } else if (error) {
      setErrorMessage("An unexpected error occurred. Please try again.");
    }
    
    setIsLoading(false);
  };

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
        {items && items.length > 0 ? (
          items.map((item: any) => (
            <div key={item.product_id} className="flex justify-between items-center text-sm">
              <span className="text-gray-300">{item.name} (x{item.quantity})</span>
              <span className="text-white font-medium">${(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))
        ) : (
          <p className="text-gray-400 text-sm italic text-center">No items in order.</p>
        )}
        
        <div className="!mt-4 pt-4 border-t border-cyan-400/20 flex justify-between items-center">
            <span className="text-white font-bold text-lg">Total</span>
            <motion.p 
              className="text-3xl font-extrabold text-cyan-300"
              style={{ fontFamily: "'Orbitron', sans-serif", filter: 'drop-shadow(0 0 10px rgba(6, 182, 212, 0.5))' }}
              animate={{ filter: ['drop-shadow(0 0 10px rgba(6, 182, 212, 0.5))', 'drop-shadow(0 0 15px rgba(6, 182, 212, 0.8))', 'drop-shadow(0 0 10px rgba(6, 182, 212, 0.5))'] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            >
              ${total.toFixed(2)}
            </motion.p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-4 bg-black/40 rounded-xl border border-cyan-400/30 backdrop-blur-sm">
          <PaymentElement />
        </div>
        
        {errorMessage && (
          <div className="text-red-400 text-sm text-center p-3 rounded-lg bg-red-900/40 border border-red-500/50">
            {errorMessage}
          </div>
        )}

        <motion.button
          disabled={isLoading || !stripe || !elements}
          type="submit"
          className="w-full flex items-center justify-center gap-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold py-4 rounded-xl shadow-lg hover:shadow-cyan-500/40 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ fontFamily: "'Orbitron', sans-serif", letterSpacing: '0.05em' }}
          whileHover={{ scale: 1.03, shadow: '0 0 20px rgba(6, 182, 212, 0.6)' }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Lock size={16} />
          )}
          <span>{isLoading ? 'Authorizing...' : 'Authorize & Pay Securely'}</span>
        </motion.button>
      </form>
    </motion.div>
  );
};
