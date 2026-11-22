'use client';
import { useRef, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

export default function PayPalReturn() {
  const [status, setStatus] = useState<'ready' | 'pending' | 'done' | 'error'>('ready');
  const busy = useRef(false);
  async function finish() {
    if (busy.current) return;
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get('order_id') || '';
    const token = params.get('token') || '';
    if (!/^[1-9][0-9]*$/.test(orderId) || !/^[A-Z0-9]{1,36}$/.test(token)) { setStatus('error'); return; }
    busy.current = true; setStatus('pending');
    try {
      const response = await api.post('/ai-ordering/checkout/paypal/capture', { order_id: orderId, paypal_order_id: token });
      if (response.data?.status !== 'captured') throw new Error('Capture unconfirmed');
      setStatus('done');
    } catch { setStatus('error'); }
    finally { busy.current = false; }
  }
  return <section className="mx-auto max-w-xl px-6 py-16 text-white" aria-busy={status === 'pending'}>
    <h1 className="text-3xl mb-5">{status === 'done' ? 'Payment confirmed' : 'Finish your PayPal checkout'}</h1>
    {status === 'done' ? <p>Your payment was verified and your order is confirmed.</p> : <>
      <p className="text-slate-300 mb-5">Sign in to the same account, then finish payment. We verify the PayPal approval, order owner, amount and currency before confirming your order.</p>
      <button disabled={status === 'pending'} onClick={finish} className="rounded-lg bg-cyan-400 px-5 py-3 text-slate-950 font-semibold disabled:opacity-40">{status === 'pending' ? 'Verifying payment...' : 'Complete payment'}</button>
    </>}
    {status === 'error' && <p role="alert" className="mt-5 text-amber-300">Payment confirmation could not be verified. Your payment may have completed. Check your orders before starting a new checkout; you can retry confirmation for this same order.</p>}
    <nav className="mt-6 flex gap-5"><Link href="/profile" className="underline text-cyan-300">Order history in profile</Link><Link href="/login" className="underline">Sign in</Link></nav>
  </section>;
}
