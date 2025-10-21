// file: apps/web/app/(admin)/dashboard/page.tsx (Corrected Loading Condition)
'use client';

import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AlertCircle, DollarSign, Package, PackageCheck, Truck, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { useState, useMemo } from 'react';

// --- Data Types ---
interface Stats {
  total_revenue: number;
  total_orders: number;
  total_products: number;
  active_drones: number;
}

interface Order {
  id: number;
  user_id: number;
  status: 'Pending' | 'Processing' | 'In Transit' | 'Delivered' | 'Cancelled';
  total_price: number;
  created_at: string;
}

// --- SWR Fetcher ---
const fetcher = (url: string) => api.get(url).then(res => res.data);

// --- Skeleton Components ---
const StatCardSkeleton = () => (
  <div className="animate-pulse overflow-hidden rounded-lg border border-white/10 bg-black/30 backdrop-blur-xl p-5 shadow">
    <div className="h-4 bg-gray-700 rounded w-3/4 mb-4"></div>
    <div className="h-8 bg-gray-600 rounded w-1/2"></div>
  </div>
);

const OrdersTableSkeleton = () => (
  <div className="animate-pulse border border-white/10 rounded-lg overflow-hidden mb-6">
    <div className="h-12 bg-black/50 w-full"></div> {/* Header Placeholder */}
    {[...Array(5)].map((_, i) => (
      <div key={i} className="flex justify-between items-center px-6 py-4 border-t border-white/10 h-[57px]">
        <div className="h-4 bg-gray-700 rounded w-1/6"></div>
        <div className="h-4 bg-gray-700 rounded w-1/4"></div>
        <div className="h-4 bg-gray-700 rounded w-1/6"></div>
        <div className="h-4 bg-gray-700 rounded w-1/6 text-right"></div>
      </div>
    ))}
  </div>
);

// --- Status Badge Component ---
const StatusBadge = ({ status }: { status: Order['status'] }) => {
  let colorClasses = '';
  switch (status) {
    case 'Delivered': colorClasses = 'bg-green-500/10 text-green-400 border-green-500/30'; break;
    case 'Processing': case 'In Transit': colorClasses = 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'; break;
    case 'Cancelled': colorClasses = 'bg-red-500/10 text-red-400 border-red-500/30'; break;
    case 'Pending': default: colorClasses = 'bg-gray-500/10 text-gray-400 border-gray-500/30'; break;
  }
  return <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full border ${colorClasses}`}>{status}</span>;
};

// --- Main Dashboard Component ---
export default function AdminDashboardPage() {
  const { data: session, status } = useSession({ required: true }); // required:true handles redirect if not logged in
  const [currentPage, setCurrentPage] = useState(1);
  const ordersPerPage = 10;

  // Derive API URLs based on admin role
  const statsApiUrl = session?.user?.role === 'admin' ? '/admin/stats' : null;
  const ordersApiUrl = session?.user?.role === 'admin' ? `/admin/orders?page=${currentPage}&limit=${ordersPerPage}` : null;

  // Fetch data using SWR
  const { data: stats, error: statsError, isLoading: isLoadingStats } = useSWR<Stats>(statsApiUrl, fetcher, { revalidateOnFocus: false });
  const { data: ordersData, error: ordersError, isLoading: isLoadingOrders } = useSWR<{ orders: Order[], total_orders: number }>(ordersApiUrl, fetcher, { revalidateOnFocus: false });

  const orders = ordersData?.orders ?? [];
  const totalOrders = ordersData?.total_orders ?? 0;
  const totalPages = Math.ceil(totalOrders / ordersPerPage);

  // Determine overall loading and error states
  const isLoading = status === 'loading' || (session?.user?.role === 'admin' && ((!stats && isLoadingStats) || (!ordersData && isLoadingOrders)));
  const error = status !== 'authenticated' && status !== 'loading' // Handle auth edge cases if required:true fails somehow
    ? "Authentication error."
    : session?.user?.role !== 'admin' // Check role *after* session loads
    ? "Access Denied. You do not have permission to view this page."
    : statsError || ordersError // Check SWR errors
    ? `Failed to load dashboard data: ${statsError?.message || ordersError?.message || 'Unknown error'}`
    : null;

  // Pagination handlers
  const handleNextPage = () => { if (currentPage < totalPages) setCurrentPage(currentPage + 1); };
  const handlePrevPage = () => { if (currentPage > 1) setCurrentPage(currentPage - 1); };

  // --- Render Loading State ---
  // The condition has been simplified by removing the redundant check
  if (isLoading && !error && session?.user?.role === 'admin') {
    return (
      <div className="container mx-auto py-12 px-4 text-white">
        <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-bold mb-8 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600" style={{ fontFamily: "'Orbitron', sans-serif" }}>Admin Dashboard</motion.h1>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-10">
          {[...Array(4)].map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
        <div>
          <div className="h-8 bg-gray-700 rounded w-1/4 mb-4 animate-pulse"></div>
          <OrdersTableSkeleton />
          <div className="flex justify-between items-center mt-6 animate-pulse">
            <div className="h-9 bg-gray-700 rounded w-28"></div>
            <div className="h-4 bg-gray-700 rounded w-20"></div>
            <div className="h-9 bg-gray-700 rounded w-24"></div>
          </div>
        </div>
      </div>
    );
  }

  // --- Render Error State ---
  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center text-white">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Error Loading Dashboard</h2>
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  // --- Render Dashboard ---
  // No changes needed in the final render part
  return (
    <div className="container mx-auto py-12 px-4 text-white">
        <motion.h1 /* ... */ >Admin Dashboard</motion.h1>
        <motion.div /* ... Stats Cards ... */ >
             {/* ... StatCard components ... */}
             <motion.div variants={{hidden: {opacity: 0, y: 20}, visible: {opacity: 1, y: 0}}} className="overflow-hidden rounded-lg border border-white/10 bg-black/30 backdrop-blur-xl p-5 shadow shadow-black/30">
                <p className="truncate text-sm font-medium text-gray-400 flex items-center gap-2"><DollarSign size={16}/>Total Revenue</p>
                <p className="mt-1 text-3xl font-semibold text-white">${stats?.total_revenue?.toFixed(2) ?? '0.00'}</p>
            </motion.div>
            <motion.div variants={{hidden: {opacity: 0, y: 20}, visible: {opacity: 1, y: 0}}} className="overflow-hidden rounded-lg border border-white/10 bg-black/30 backdrop-blur-xl p-5 shadow shadow-black/30">
                <p className="truncate text-sm font-medium text-gray-400 flex items-center gap-2"><Package size={16}/>Total Orders</p>
                <p className="mt-1 text-3xl font-semibold text-white">{stats?.total_orders ?? totalOrders ?? '0'}</p> {/* Show total from ordersData if stats is slow */}
            </motion.div>
            <motion.div variants={{hidden: {opacity: 0, y: 20}, visible: {opacity: 1, y: 0}}} className="overflow-hidden rounded-lg border border-white/10 bg-black/30 backdrop-blur-xl p-5 shadow shadow-black/30">
                <p className="truncate text-sm font-medium text-gray-400 flex items-center gap-2"><PackageCheck size={16}/>Total Products</p>
                <p className="mt-1 text-3xl font-semibold text-white">{stats?.total_products ?? '0'}</p>
            </motion.div>
            <motion.div variants={{hidden: {opacity: 0, y: 20}, visible: {opacity: 1, y: 0}}} className="overflow-hidden rounded-lg border border-white/10 bg-black/30 backdrop-blur-xl p-5 shadow shadow-black/30">
                <p className="truncate text-sm font-medium text-gray-400 flex items-center gap-2"><Truck size={16}/>Active Drones</p>
                <p className="mt-1 text-3xl font-semibold text-white">{stats?.active_drones ?? '0'}</p>
            </motion.div>
        </motion.div>
        <motion.div /* ... Orders Table ... */ >
            <h2 /* ... */ >Recent Orders</h2>
            <div /* ... table container ... */ >
                <table /* ... */ >
                    <thead /* ... */ >{/* ... */}</thead>
                    <tbody /* ... */ >
                        {orders && orders.length > 0 ? orders.map((order) => (
                            <tr key={order.id} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-cyan-400">#{order.id}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{new Date(order.created_at).toLocaleDateString()}</td>
                                <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={order.status} /></td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-white">${order.total_price.toFixed(2)}</td>
                            </tr>
                        )) : (
                            <tr><td colSpan={4} className="text-center py-10 text-gray-500">No recent orders found.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
             {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex justify-between items-center mt-6">
                <motion.button onClick={handlePrevPage} disabled={currentPage === 1} whileHover={{ scale: 1.05, x: -2 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 bg-white/5 border border-white/10 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/10 transition-colors">
                  <ChevronLeft size={16} /> Previous
                </motion.button>
                <span className="text-sm text-gray-400">Page {currentPage} of {totalPages}</span>
                <motion.button onClick={handleNextPage} disabled={currentPage === totalPages} whileHover={{ scale: 1.05, x: 2 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 bg-white/5 border border-white/10 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/10 transition-colors">
                  Next <ChevronRight size={16} />
                </motion.button>
              </div>
            )}
        </motion.div>
    </div>
  );
}
