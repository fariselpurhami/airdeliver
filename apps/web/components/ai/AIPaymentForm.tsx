import React, { useState } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { motion } from 'framer-motion';
import { Lock } from 'lucide-react';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

interface AIPaymentFormProps {
  orderId: number;
  total: number;
  onPaymentSuccess: () => void;
}

export const AIPaymentForm: React.FC<AIPaymentFormProps> = ({ orderId, total, onPaymentSuccess }) => {
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
    <div className="w-full max-w-lg mx-auto p-6 text-white">
      <div className="text-center mb-6">
        <h2 className="text-3xl font-bold mb-2">Complete Payment</h2>
        <p className="text-gray-400 text-lg">Order ID: #{orderId}</p>
        <p className="text-5xl font-extrabold text-cyan-400 mt-4">${total.toFixed(2)}</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-4 bg-black/30 rounded-lg border border-cyan-400/30">
          <PaymentElement />
        </div>
        
        {errorMessage && (
          <div className="text-red-400 text-sm text-center p-2 rounded-md bg-red-900/30 border border-red-500/50">
            {errorMessage}
          </div>
        )}

        <motion.button
          disabled={isLoading || !stripe || !elements}
          type="submit"
          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-bold py-4 rounded-lg shadow-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          whileHover={{ scale: 1.02 }}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Lock size={18} />
          )}
          <span>{isLoading ? 'Processing...' : 'Pay Securely'}</span>
        </motion.button>
      </form>
    </div>
  );
};
