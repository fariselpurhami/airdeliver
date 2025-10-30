// apps/web/components/profile/ViewOrdersModal.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Package, Loader2, AlertCircle } from 'lucide-react';
import useSWR from 'swr';
import { fetcher } from '@/lib/fetcher'; 
import Image from 'next/image'; 

interface Order {
    id: number;
    user_id: number;
    status: string;
    total_price: number;
    created_at: string;
}

interface PaginatedOrdersResponse {
    total: number;
    page: number;
    limit: number;
    orders: Order[];
}

const OrderRow = ({ order }: { order: Order }) => {
    const statusColor = {
        Delivered: 'text-green-400', Shipped: 'text-cyan-400',
        Processing: 'text-yellow-400', Cancelled: 'text-red-400',
    }[order.status] || 'text-gray-400';

    return (
         <motion.tr 
             initial={{ opacity: 0 }} animate={{ opacity: 1 }}
             className="border-b border-white/10 hover:bg-white/5"
         >
            <td className="px-4 py-3 text-sm text-cyan-400">#{order.id}</td>
            <td className="px-4 py-3 text-sm text-gray-300">
                {new Date(order.created_at).toLocaleDateString()}
            </td>
            <td className={`px-4 py-3 text-sm font-semibold ${statusColor}`}>
                {order.status}
            </td>
            <td className="px-4 py-3 text-sm text-white font-mono text-right">
                ${order.total_price.toFixed(2)}
            </td>
        </motion.tr>
    );
};

export default function ViewOrdersModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const [page, setPage] = useState(1);
    const limit = 10; 

    const { data, error, isLoading } = useSWR<PaginatedOrdersResponse>(
        isOpen ? `/api/v1/orders/me?page=${page}&limit=${limit}` : null, 
        fetcher,
        { revalidateOnFocus: false }
    );

    const totalPages = data ? Math.ceil(data.total / limit) : 0;

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="fixed inset-0 z-50 bg-black/30 backdrop-blur-xl flex justify-center items-center p-4"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full max-w-5xl h-[85vh] max-h-[800px] flex flex-col bg-black/20 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden" 
                    >
                        <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
                            <h3 className="font-bold text-lg text-white flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <Package size={18} className="text-cyan-400"/> Your Orders
                            </h3>
                            <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <div className="flex-grow p-1 overflow-y-auto"> 
                            {isLoading && !data && (
                                 <div className="flex items-center justify-center h-full">
                                    <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
                                 </div>
                            )}
                            {error && (
                                 <div className="flex flex-col items-center justify-center h-full text-center px-6">
                                    <AlertCircle className="h-10 w-10 text-red-500 mb-3"/>
                                    <p className="text-red-400">Error loading orders:</p>
                                    <p className="text-sm text-red-400/80">{error.message}</p>
                                 </div>
                            )}
                            {data && data.orders.length === 0 && (
                                 <div className="flex items-center justify-center h-full text-gray-500 italic">
                                    You haven't placed any orders yet.
                                 </div>
                            )}
                            {data && data.orders.length > 0 && (
                                <table className="min-w-full">
                                    <thead className="sticky top-0 bg-black/70 backdrop-blur-sm z-10">
                                        <tr className="border-b border-white/10">
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">ID</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Date</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                         <AnimatePresence>
                                            {data.orders.map(order => <OrderRow key={order.id} order={order} />)}
                                        </AnimatePresence>
                                    </tbody>
                                </table>
                            )}
                        </div>

                        
                        {totalPages > 1 && (
                            <footer className="p-3 border-t border-white/10 flex justify-between items-center flex-shrink-0">
                                <button 
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1 || isLoading}
                                    className="px-3 py-1 text-sm rounded bg-white/10 hover:bg-white/20 disabled:opacity-50"
                                >
                                    Previous
                                </button>
                                <span className="text-xs text-gray-400">
                                    Page {page} of {totalPages} (Total: {data?.total})
                                </span>
                                <button 
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages || isLoading}
                                    className="px-3 py-1 text-sm rounded bg-white/10 hover:bg-white/20 disabled:opacity-50"
                                >
                                    Next
                                </button>
                            </footer>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
