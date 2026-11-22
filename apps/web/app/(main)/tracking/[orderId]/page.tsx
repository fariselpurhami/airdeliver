// apps/web/app/(main)/tracking/[orderId]/page.tsx

'use client';

import { useMemo } from 'react';
import { FiLoader, FiPackage, FiAlertTriangle, FiCheckCircle, FiClock } from 'react-icons/fi';
import useSWR from 'swr';
import { api } from '@/lib/api';

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
    total_price: number;
    created_at: string;
    items?: OrderItem[];
}

interface PaginatedOrders {
    orders: OrderDetails[];
}

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
    pending: { label: 'Order received', className: 'text-yellow-400' },
    processing: { label: 'Being prepared', className: 'text-cyan-400' },
    in_transit: { label: 'On the way', className: 'text-cyan-400' },
    delivered: { label: 'Delivered', className: 'text-green-400' },
    cancelled: { label: 'Cancelled', className: 'text-red-400' },
    failed: { label: 'Failed', className: 'text-red-400' },
};

export default function TrackingPage({ params }: { params: { orderId: string } }) {
  const { orderId } = params;
  const swrFetcher = (url: string) => api.get(url).then(res => res.data);
  // The backend exposes order history at GET /orders/me; there is no
  // per-order detail endpoint, so we look the order up in the user's list.
  const { data, error, isLoading } = useSWR<PaginatedOrders>('/orders/me?limit=100', swrFetcher);

  const order = useMemo(
    () => data?.orders?.find(o => String(o.id) === String(orderId)) || null,
    [data, orderId]
  );

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center bg-black text-white p-4">
        <FiLoader className="animate-spin text-cyan-400 text-4xl mb-4" />
        <h1 className="text-2xl font-bold mb-2 text-gray-300">Loading Order #{orderId}...</h1>
      </div>
    );
  }

  if (error) {
      return (
          <div className="min-h-screen flex flex-col items-center justify-center text-center bg-black text-white p-4">
              <FiAlertTriangle className="text-red-500 text-4xl mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-red-400">Error Loading Order #{orderId}</h1>
              <p className="text-red-300 bg-red-900/50 p-3 rounded border border-red-800 max-w-md">
                   {(error as any)?.message || 'Could not fetch order details.'}
              </p>
          </div>
      );
  }

  if (!order) {
      return (
          <div className="min-h-screen flex flex-col items-center justify-center text-center bg-black text-white p-4">
              <FiPackage className="text-gray-500 text-4xl mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-gray-300">Order #{orderId} not found</h1>
              <p className="text-gray-500 max-w-md">This order does not exist in your history.</p>
          </div>
      );
  }

  const status = STATUS_STYLES[order.status?.toLowerCase()] || { label: order.status, className: 'text-gray-300' };

  return (
    <div className="min-h-screen bg-black text-white pt-24 pb-12">
        <div className="max-w-2xl mx-auto px-4">
            <h1 className="text-4xl font-bold mb-2 text-center" style={{ fontFamily: "'Orbitron', sans-serif" }}>Order #{order.id}</h1>
            <p className="text-center text-gray-500 mb-8">
                Placed {new Date(order.created_at).toLocaleString()}
            </p>

            <div className="p-6 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm mb-4">
                <h3 className="font-semibold text-cyan-400 flex items-center gap-2 mb-2">
                    {order.status?.toLowerCase() === 'delivered' ? <FiCheckCircle size={16} /> : <FiClock size={16} />}
                    Status
                </h3>
                <p className={`text-lg font-semibold ${status.className}`}>{status.label}</p>
            </div>

            {order.items && order.items.length > 0 && (
                <div className="p-6 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm mb-4">
                    <h3 className="font-semibold text-cyan-400 mb-3">Items</h3>
                    <ul className="space-y-2">
                        {order.items.map(item => (
                            <li key={item.id} className="flex justify-between text-sm text-gray-300">
                                <span>{item.product?.name || `Product #${item.product_id}`} × {item.quantity}</span>
                                <span className="font-mono">${(item.price_per_unit * item.quantity).toFixed(2)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="p-6 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm flex justify-between items-center">
                <span className="font-semibold text-gray-300">Total</span>
                <span className="text-xl font-bold text-white font-mono">${order.total_price.toFixed(2)}</span>
            </div>
        </div>
    </div>
  );
}
