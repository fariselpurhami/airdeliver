// file: apps/web/app/(admin)/dashboard/page.tsx
// version: 2.0.0 (Functional Dashboard)
// date: 2025-09-30
// author: Gemini

'use client';

import { useSession } from 'next-auth/react';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

// Define types for our data for type safety
interface Stats {
  total_revenue: number;
  total_orders: number;
  total_products: number;
  active_drones: number;
}

interface Order {
  id: number;
  user_id: number;
  status: string;
  total_price: number;
  created_at: string;
}

export default function AdminDashboardPage() {
  const { data: session } = useSession({ required: true });
  const [stats, setStats] = useState<Stats | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      // Ensure the user is an admin before fetching data
      if (session?.user?.role !== 'admin') {
        setError("Access Denied. You do not have permission to view this page.");
        setIsLoading(false);
        return;
      }
      
      try {
        // Fetch all admin data concurrently
        const [statsRes, ordersRes] = await Promise.all([
          api.get('/admin/stats'),
          api.get('/admin/orders')
        ]);
        
        setStats(statsRes.data);
        setOrders(ordersRes.data);
      } catch (err) {
        setError("Failed to load dashboard data. Please ensure the backend is running and you are logged in as an admin.");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    // Only fetch data if a session exists
    if (session) {
      fetchData();
    }
  }, [session]);

  if (isLoading) {
    return <div className="text-center py-20">Loading Dashboard...</div>;
  }
  
  if (error) {
    return <div className="text-center py-20 text-red-500">{error}</div>;
  }

  return (
    <div className="py-12">
      <h1 className="text-4xl font-bold mb-8">Admin Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-10">
        <div className="overflow-hidden rounded-lg border bg-background p-5 shadow">
          <p className="truncate text-sm font-medium text-foreground/80">Total Revenue</p>
          <p className="mt-1 text-3xl font-semibold">${stats?.total_revenue.toFixed(2) || '0.00'}</p>
        </div>
        <div className="overflow-hidden rounded-lg border bg-background p-5 shadow">
          <p className="truncate text-sm font-medium text-foreground/80">Total Orders</p>
          <p className="mt-1 text-3xl font-semibold">{stats?.total_orders || '0'}</p>
        </div>
        <div className="overflow-hidden rounded-lg border bg-background p-5 shadow">
          <p className="truncate text-sm font-medium text-foreground/80">Total Products</p>
          <p className="mt-1 text-3xl font-semibold">{stats?.total_products || '0'}</p>
        </div>
        <div className="overflow-hidden rounded-lg border bg-background p-5 shadow">
          <p className="truncate text-sm font-medium text-foreground/80">Active Drones</p>
          <p className="mt-1 text-3xl font-semibold">{stats?.active_drones || '0'}</p>
        </div>
      </div>

      {/* Recent Orders Table */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Recent Orders</h2>
        <div className="overflow-x-auto border rounded-lg">
          <table className="min-w-full divide-y">
            <thead className="bg-foreground/5">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Order ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">#{order.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground/80">{new Date(order.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                      {order.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">${order.total_price.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
