'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
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

  return <main className="min-h-screen bg-black text-white pt-28 pb-16 px-4">
    <div className="max-w-2xl mx-auto space-y-5">
      <Link href="/profile" className="text-cyan-300 underline inline-block py-2">Back to profile and order history</Link>
      <h1 className="text-3xl sm:text-4xl font-bold break-words">Order tracking</h1>
      {!validId ? <p role="alert">This order link is invalid. Open your order history to find the right order.</p>
      : isLoading ? <p role="status">Loading your order...</p>
      : !order && error ? <section className="rounded-2xl border border-white/15 bg-white/5 p-6 space-y-4" role="alert">
        <h2 className="text-xl font-semibold">{missing ? 'Order not found in your account' : signIn ? 'Sign in to view your order' : 'Order details are temporarily unavailable'}</h2>
        <p className="text-slate-300">{missing ? 'Check the order number or open your order history. No information about other accounts is shown.' : signIn ? 'Your session may have expired. Sign in again to continue.' : 'We could not check the current order status. No order change or payment was made here.'}</p>
        {signIn ? <Link href={`/login?callbackUrl=${encodeURIComponent(`/tracking/${orderId}`)}`} className="text-cyan-300 underline">Sign in</Link>
          : !missing && <button type="button" onClick={() => void mutate()} className="rounded-lg border border-cyan-400 px-4 py-2">Try again</button>}
      </section>
      : order ? <>
        <p className="text-slate-300">Order #{order.id} · Placed {orderDate(order.created_at)}</p>
        {error && <p role="alert" className="rounded-xl border border-amber-400 p-4 text-amber-200">We could not refresh this order. The details below are the last saved view, not a confirmed current status.</p>}
        <section aria-labelledby="order-status" className="rounded-2xl border border-white/15 bg-white/5 p-6 space-y-3">
          <h2 id="order-status" className="text-lg font-semibold">Recorded order status</h2>
          <p className={`text-xl font-semibold ${status.className}`}>{status.label}</p>
          <p className="text-sm text-slate-300">Order record last updated: {orderDate(order.updated_at)}</p>
          <p className="text-sm text-slate-400">This is the order record, not live carrier tracking. A carrier location and delivery estimate are not available here.</p>
          <p className="text-xs text-slate-400">Checks every minute while this page is visible and online.</p>
          <button type="button" disabled={isValidating} onClick={() => void mutate()} className="rounded-lg border border-cyan-400 px-4 py-2 disabled:opacity-50">{isValidating ? 'Checking...' : 'Refresh status'}</button>
        </section>
        <section aria-labelledby="order-items" className="rounded-2xl border border-white/15 bg-white/5 p-6">
          <h2 id="order-items" className="text-lg font-semibold mb-4">Items</h2>
          {order.items?.length ? <ul className="space-y-4">{order.items.map(item => <li key={item.id} className="flex flex-wrap gap-2 justify-between text-sm">
            <span className="break-words min-w-0">{item.product?.name || `Product #${item.product_id}`} × {item.quantity}</span>
            <span className="font-mono">{orderMoney(item.price_per_unit * item.quantity, order.currency)}</span>
          </li>)}</ul> : <p className="text-slate-400">Item details are unavailable.</p>}
        </section>
        <section aria-label="Order total" className="rounded-2xl border border-white/15 bg-white/5 p-6 flex flex-wrap gap-3 justify-between">
          <span className="font-semibold">Recorded total</span><span className="font-mono text-xl">{orderMoney(order.total_price, order.currency)}</span>
        </section>
      </> : <p role="status">Order details have not loaded. Open your order history or refresh this page.</p>}
    </div>
  </main>;
}
