'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Package, Radar, ShieldCheck, RefreshCw, ReceiptText } from 'lucide-react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { orderDate, orderMoney, orderStatus } from '@/lib/order-display';

interface OrderItem {
  id: number;
  product_id: number;
  quantity: number;
  price_per_unit: number;
  product?: { name?: string } | null;
}
interface OrderDetails {
  id: number;
  status: string;
  currency: string;
  total_price: number;
  created_at: string;
  updated_at: string;
  items?: OrderItem[];
}
const fetchOrder = (url: string) => api.get<OrderDetails>(url).then(response => response.data);

export default function TrackingPage() {
  const { orderId } = useParams<{ orderId: string }>();
  // Validate before constructing a request. IDs stay strings to avoid rounding
  // an out-of-range path to a different customer's order.
  const validId = typeof orderId === 'string' && /^[1-9]\d{0,18}$/.test(orderId) && BigInt(orderId) <= BigInt('2147483647');
  const { data: order, error, isLoading, isValidating, mutate } = useSWR<OrderDetails>(
    validId ? `/orders/me/${orderId}` : null, fetchOrder,
    { refreshInterval: 60000, refreshWhenHidden: false, refreshWhenOffline: false, shouldRetryOnError: false, keepPreviousData: false }
  );
  const errorStatus = error?.response?.status;
  const missing = errorStatus === 404;
  const signIn = errorStatus === 401 || errorStatus === 403;
  const status = orderStatus(order?.status || '');

  return <main className="relative isolate min-h-screen bg-black text-white pt-24 sm:pt-28 pb-16 px-4 overflow-hidden">
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
      <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[850px] h-[650px] rounded-full bg-cyan-500/[0.08] blur-[100px]" />
      <div className="absolute top-96 -right-56 w-[600px] h-[600px] rounded-full bg-violet-500/[0.08] blur-[100px]" />
      <div className="absolute inset-0 opacity-[0.12]" style={{backgroundImage:'linear-gradient(rgba(0,198,255,.2) 1px,transparent 1px),linear-gradient(90deg,rgba(0,198,255,.2) 1px,transparent 1px)',backgroundSize:'72px 72px',maskImage:'linear-gradient(black,transparent 75%)'}} />
    </div>
    <div className="max-w-3xl mx-auto space-y-5 sm:space-y-6">
      <Link href="/profile" className="group inline-flex min-h-11 items-center gap-2 rounded-xl px-3 -ml-3 text-xs font-medium tracking-wide text-slate-400 transition hover:bg-white/5 hover:text-cyan-300 focus-visible:outline-2 focus-visible:outline-cyan-400"><ArrowLeft size={15} aria-hidden="true"/>Back to profile and order history</Link>
      <header className="text-center py-5 sm:py-8 space-y-5">
        <div className="inline-flex items-center gap-2.5 rounded-full border border-white/10 bg-white/[0.04] px-5 py-2.5 shadow-[0_0_30px_rgba(6,182,212,.08)] backdrop-blur-xl"><Radar size={14} className="text-cyan-400" aria-hidden="true"/><span className="text-[10px] uppercase tracking-[0.24em] text-cyan-200">Your order record</span></div>
        <h1 className="text-3xl sm:text-5xl font-black tracking-tight break-words" style={{fontFamily:"'Orbitron', sans-serif"}}>ORDER <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-400">TRACKING</span></h1>
        <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">Your purchase details and latest recorded status, together in one place.</p>
      </header>
      {!validId ? <p role="alert">This order link is invalid. Open your order history to find the right order.</p>
      : isLoading ? <p role="status">Loading your order...</p>
      : !order && error ? <section className="rounded-2xl border border-white/15 bg-white/5 p-6 space-y-4" role="alert">
        <h2 className="text-xl font-semibold">{missing ? 'Order not found in your account' : signIn ? 'Sign in to view your order' : 'Order details are temporarily unavailable'}</h2>
        <p className="text-slate-300">{missing ? 'Check the order number or open your order history. No information about other accounts is shown.' : signIn ? 'Your session may have expired. Sign in again to continue.' : 'We could not check the current order status. No order change or payment was made here.'}</p>
        {signIn ? <Link href={`/login?callbackUrl=${encodeURIComponent(`/tracking/${orderId}`)}`} className="text-cyan-300 underline">Sign in</Link>
          : !missing && <button type="button" onClick={() => void mutate()} className="rounded-lg border border-cyan-400 px-4 py-2">Try again</button>}
      </section>
      : order ? <>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-5"><span className="inline-flex items-center gap-2 font-mono text-sm text-cyan-300"><Package size={16} aria-hidden="true"/>Order #{order.id}</span><span className="text-xs text-slate-400">Placed {orderDate(order.created_at)}</span></div>
        {error && <p role="alert" className="rounded-xl border border-amber-400 p-4 text-amber-200">We could not refresh this order. The details below are the last saved view, not a confirmed current status.</p>}
        <section aria-labelledby="order-status" className="relative overflow-hidden rounded-[28px] sm:rounded-[32px] border border-white/10 bg-white/[0.035] p-6 sm:p-8 space-y-4 backdrop-blur-2xl shadow-[0_16px_60px_rgba(0,0,0,.3)]">
          <div aria-hidden="true" className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent"/><h2 id="order-status" className="text-xs uppercase tracking-[0.18em] text-slate-400 flex items-center gap-2"><Radar size={15} className="text-cyan-400" aria-hidden="true"/>Recorded order status</h2>
          <p className={`text-xl sm:text-2xl font-semibold ${status.className}`}>{status.label}</p>
          <p className="text-sm text-slate-300">Order record last updated: {orderDate(order.updated_at)}</p>
          <p className="text-sm text-slate-400">This is the order record, not live carrier tracking. A carrier location and delivery estimate are not available here.</p>
          <p className="text-xs text-slate-400">Checks every minute while this page is visible and online.</p>
          <button type="button" disabled={isValidating} onClick={() => void mutate()} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-cyan-400/25 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-200 transition hover:bg-cyan-400/20 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-cyan-400"><RefreshCw size={14} aria-hidden="true" className={isValidating ? 'animate-spin' : ''}/>{isValidating ? 'Checking...' : 'Refresh status'}</button>
        </section>
        <section aria-labelledby="order-items" className="rounded-[28px] sm:rounded-[32px] border border-white/10 bg-white/[0.035] p-6 sm:p-8 backdrop-blur-2xl">
          <h2 id="order-items" className="text-xs uppercase tracking-[0.18em] text-slate-400 flex items-center gap-2 mb-6"><Package size={15} className="text-cyan-400" aria-hidden="true"/>Items</h2>
          {order.items?.length ? <ul className="space-y-4">{order.items.map(item => <li key={item.id} className="flex flex-wrap gap-2 justify-between text-sm">
            <span className="break-words min-w-0">{item.product?.name || `Product #${item.product_id}`} × {item.quantity}</span>
            <span className="font-mono">{orderMoney(item.price_per_unit * item.quantity, order.currency)}</span>
          </li>)}</ul> : <p className="text-slate-400">Item details are unavailable.</p>}
        </section>
        <section aria-label="Order total" className="rounded-[28px] sm:rounded-[32px] border border-cyan-400/15 bg-gradient-to-br from-cyan-500/[0.07] to-violet-500/[0.05] p-6 sm:p-8 flex flex-wrap items-center gap-3 justify-between backdrop-blur-2xl">
          <span className="font-medium text-sm inline-flex items-center gap-2"><ReceiptText size={16} className="text-cyan-400" aria-hidden="true"/>Recorded total</span><span className="font-mono text-xl">{orderMoney(order.total_price, order.currency)}</span>
        </section>
      </> : <p role="status">Order details have not loaded. Open your order history or refresh this page.</p>}
      <p className="flex justify-center items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-slate-500 pt-3"><ShieldCheck size={13} aria-hidden="true"/>Private to your account</p>
    </div>
  </main>;
}
