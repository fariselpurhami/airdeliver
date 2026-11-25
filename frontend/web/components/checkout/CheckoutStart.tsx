'use client';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

export default function CheckoutStart() {
  const { status } = useSession();
  const beginCheckout = useAIOrderingStore(state => state.confirmCurrentOrder);
  return <section className="mx-auto max-w-xl px-6 py-16 text-white">
    <h1 className="text-3xl font-semibold mb-4">Secure checkout</h1>
    <p className="mb-6 text-slate-300">Use the same checkout as your shopping assistant. Review your delivery address, see the current order total, then choose an available payment method.</p>
    {status === 'authenticated' ? <button type="button" onClick={beginCheckout} className="rounded-lg bg-cyan-400 px-6 py-3 font-semibold text-slate-950">Review delivery and payment</button>
      : <Link href="/login?callbackUrl=%2Fcheckout" className="inline-block rounded-lg bg-cyan-400 px-6 py-3 font-semibold text-slate-950">Sign in to continue</Link>}
    <p className="mt-5 text-sm text-slate-400">No payment details are collected on this page. Card details are entered only in the payment provider's secure form.</p>
    <Link href="/cart" className="mt-6 inline-block text-cyan-300 underline">Back to cart</Link>
  </section>;
}
