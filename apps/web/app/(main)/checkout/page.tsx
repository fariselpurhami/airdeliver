# file: apps/web/app/(main)/checkout/page.tsx
# version: 1.0.0
# date: 2025-09-27
# author: Gemini

'use client';

import { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { useCartStore } from '@/hooks/useCartStore';
import { api } from '@/lib/api';
import CheckoutForm from '@/components/checkout/CheckoutForm';

// Load your Stripe public key from environment variables
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export default function CheckoutPage() {
  const { items } = useCartStore();
  const [clientSecret, setClientSecret] = useState('');

  useEffect(() => {
    // Create PaymentIntent as soon as the page loads
    const createPaymentIntent = async () => {
      try {
        const orderPayload = items.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
        }));

        const res = await api.post('/orders/create-payment-intent', orderPayload);
        setClientSecret(res.data.client_secret);
      } catch (error) {
        console.error("Failed to create payment intent:", error);
        // Handle error, e.g., show a message to the user
      }
    };
    
    if (items.length > 0) {
      createPaymentIntent();
    }
  }, [items]);

  const appearance = {
    theme: 'stripe', // Can also be 'night' or 'flat'
  };
  const options = {
    clientSecret,
    appearance,
  };

  return (
    <div className="py-12 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-center mb-8">Checkout</h1>
      {clientSecret && (
        <Elements options={options} stripe={stripePromise}>
          <CheckoutForm />
        </Elements>
      )}
      {!clientSecret && (
        <p className="text-center">Loading payment options...</p>
      )}
    </div>
  );
}
