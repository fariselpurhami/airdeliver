// file: apps/web/app/(admin)/dashboard/page.tsx
'use client';

import React, { useEffect, useRef, Suspense } from 'react';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { motion, useMotionValue, useSpring, useInView } from 'framer-motion';
import { 
    AlertCircle, Lock, Loader2, DollarSign, Package, 
    HardDrive, Wifi, Clock, BarChart2, Zap,
    Users, // <-- NEW ICON
    Truck  // <-- NEW ICON
} from 'lucide-react';
import { 
    ResponsiveContainer, 
    AreaChart, 
    Area, 
    XAxis, 
    YAxis, 
    Tooltip, 
    CartesianGrid 
} from 'recharts';

// --- (1) Data Interfaces (UPDATED) ---
interface Stats {
    total_revenue: number;
    total_orders: number;
    total_products: number;
    active_drones: number;
    pending_deliveries: number; // <-- NEW
    active_users_today: number; // <-- NEW
}
interface Order {
    id: number;
    user_id: number;
    status: string;
    total_price: number;
    created_at: string;
}
interface PaginatedOrdersResponse {
    orders: Order[];
    total_orders: number;
}
interface RevenueData { name: string; revenue: number; }
interface ActivityEvent { id: string; icon: React.ReactNode; description: string; time: string; }

// (Mock data for new components - replace with API calls when ready)
const mockRevenueData: RevenueData[] = [
    { name: 'Mon', revenue: 400 }, { name: 'Tue', revenue: 300 }, { name: 'Wed', revenue: 600 }, 
    { name: 'Thu', revenue: 800 }, { name: 'Fri', revenue: 700 }, { name: 'Sat', revenue: 1100 }, 
    { name: 'Sun', revenue: 1000 },
];
const mockActivityData: ActivityEvent[] = [
    { id: '1', icon: <Package size={16} />, description: 'New Order #1045 received', time: '5m ago' },
    { id: '2', icon: <Wifi size={16} />, description: 'Drone #A-42 went online', time: '12m ago' },
    { id: '3', icon: <Zap size={16} />, description: 'AI Order completed by user #7', time: '28m ago' },
    { id: '4', icon: <HardDrive size={16} />, description: 'New Product "iPhone 18" added', time: '45m ago' },
];


// --- (2) API Fetcher (No changes) ---
const fetcher = async (url: string) => {
    const { getSession } = await import('next-auth/react');
    const session = await getSession();
    // @ts-ignore
    const token = session?.accessToken;
    if (!token) throw new Error('Not authenticated');
    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to fetch data');
    }
    return res.json();
};

// --- (3) Re-usable Animated Counter (No changes) ---
const AnimatedCounter = ({ value }: { value: number }) => {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 100, stiffness: 100 });
    const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });

    useEffect(() => { if (isInView) motionValue.set(value); }, [motionValue, isInView, value]);

    useEffect(() => {
        const unsubscribe = springValue.on("change", (latest) => {
            if (ref.current) {
                if (value > 100 || value === 0 || Number.isInteger(value)) { 
                    ref.current.textContent = Intl.NumberFormat('en-US').format(Math.round(latest));
                } else { 
                    ref.current.textContent = Intl.NumberFormat('en-US', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                    }).format(latest);
                }
            }
        });
        return unsubscribe;
    }, [springValue, value]);
    
    return <span ref={ref}>{Number.isInteger(value) ? value : value.toFixed(2)}</span>;
};


// --- (4) Loading / Error / Access Denied States (No changes) ---
const LoadingSpinner = () => ( <div className="flex min-h-screen w-full items-center justify-center bg-black"><Loader2 className="h-12 w-12 animate-spin text-cyan-400" /></div> );
const AccessDenied = () => ( <div className="flex min-h-screen w-full flex-col items-center justify-center bg-black p-4 text-center"><div className="flex h-20 w-20 items-center justify-center rounded-full bg-red-500/10"><Lock className="h-10 w-10 text-red-500" /></div><h1 className="mt-8 text-3xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Access Denied</h1><p className="mt-2 text-gray-400">You do not have permission to view this page.</p></div> );
const ErrorDisplay = ({ error }: { error: Error }) => ( <div className="flex w-full flex-col items-center justify-center rounded-lg bg-red-500/10 p-12 text-center"><AlertCircle className="h-12 w-12 text-red-500" /><h2 className="mt-4 text-xl font-bold text-white">Error Loading Dashboard</h2><p className="mt-2 text-sm text-red-300">{error.message}</p></div> );


// --- (5) Dashboard Sub-Components (UPDATED & NEW) ---

const StatCardSkeleton = () => ( <div className="h-[124px] w-full animate-pulse rounded-2xl bg-white/5 border border-white/10 p-6" /> );
const StatCard = ({ title, value, icon, isCurrency = false }: {
    title: string;
    value: number;
    icon: React.ReactNode;
    isCurrency?: boolean;
}) => (
    <motion.div
        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
        className="transform-gpu rounded-2xl bg-white/5 p-6 backdrop-blur-lg border border-white/10 transition-all duration-300 hover:bg-white/10 hover:shadow-2xl hover:shadow-cyan-500/10"
    >
        <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-400">{title}</span>
            <span className="text-cyan-400">{icon}</span>
        </div>
        <div 
            className="mt-2 text-5xl font-black text-white"
            style={{ fontFamily: "'Orbitron', sans-serif" }}
        >
            {isCurrency && <span className="text-3xl opacity-50">$</span>}
            <AnimatedCounter value={value} />
        </div>
    </motion.div>
);

const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
        case 'delivered': return 'bg-green-500/20 text-green-300';
        case 'in transit': return 'bg-blue-500/20 text-blue-300';
        case 'processing': return 'bg-yellow-500/20 text-yellow-300';
        case 'cancelled': return 'bg-red-500/20 text-red-300';
        default: return 'bg-gray-500/20 text-gray-300';
    }
};

const TableSkeleton = () => (
    <div className="space-y-4">
        <div className="h-8 w-full animate-pulse rounded bg-white/10"></div>
        <div className="h-8 w-full animate-pulse rounded bg-white/10 opacity-75"></div>
        <div className="h-8 w-full animate-pulse rounded bg-white/10 opacity-50"></div>
    </div>
);

const OrdersTable = ({ orders }: { orders: Order[] }) => {
    if (orders.length === 0) {
        return <p className="text-center text-gray-500 py-12">No recent orders found.</p>;
    }
    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10">
                <thead className="opacity-60">
                    <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-300">Order ID</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-300">Status</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-300">Date</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-300">Total</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                    {orders.map(order => (
                        <motion.tr key={order.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="transition-colors hover:bg-white/5">
                            <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-cyan-400">#{order.id}</td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusColor(order.status)}`}>{order.status}</span></td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-400">{new Date(order.created_at).toLocaleDateString()}</td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>${order.total_price.toFixed(2)}</td>
                        </motion.tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// --- NEW: Revenue Chart Component (UPDATED with Animation) ---
const RevenueChart = ({ data, isLoading }: { data: RevenueData[], isLoading: boolean }) => {
    if (isLoading) return <TableSkeleton />;
    
    return (
        // --- 3. GRAPH ANIMATION: Animate the width for a "draw" effect ---
        <motion.div
            className="h-[300px] w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
        >
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
                    <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `$${val}`} />
                    <Tooltip
                        contentStyle={{ 
                            backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                            borderRadius: '12px',
                        }}
                        labelStyle={{ color: '#fff' }}
                    />
                    <Area 
                        isAnimationActive={true} // <-- Default animation (fade-in)
                        animationDuration={1500} // <-- Slower, smoother animation
                        type="monotone" 
                        dataKey="revenue" 
                        stroke="#06b6d4" 
                        fillOpacity={1} 
                        fill="url(#colorRevenue)" 
                        strokeWidth={2}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </motion.div>
    );
};

// --- NEW: Activity Timeline Component (UPDATED with Readability) ---
const ActivityTimeline = ({ events, isLoading }: { events: ActivityEvent[], isLoading: boolean }) => {
    if (isLoading) return <TableSkeleton />;

    return (
        <div className="flow-root">
            <ul role="list" className="-mb-8">
                {events.map((event, eventIdx) => (
                    <li key={event.id}>
                        <div className="relative pb-8">
                            {eventIdx !== events.length - 1 ? (
                                <span className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-white/10" aria-hidden="true" />
                            ) : null}
                            <div className="relative flex space-x-3">
                                <div>
                                    <span className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center ring-8 ring-transparent text-cyan-400">
                                        {event.icon}
                                    </span>
                                </div>
                                <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                                    <div>
                                        <p className="text-sm text-gray-300">{event.description}</p>
                                    </div>
                                    {/* --- 2. READABILITY: Made time lighter --- */}
                                    <div className="whitespace-nowrap text-right text-sm text-gray-500 opacity-80">
                                        <time>{event.time}</time>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
};


// --- (6) Main Dashboard Component (UPDATED LAYOUT) ---
function DashboardContent() {
    const { data: statsData, error: statsError, isLoading: isLoadingStats } = useSWR<Stats>('/api/v1/admin/stats', fetcher);
    const { data: ordersData, error: ordersError, isLoading: isLoadingOrders } = useSWR<PaginatedOrdersResponse>('/api/v1/admin/orders?page=1&limit=5', fetcher);
    
    const isLoadingGraph = false;
    const isLoadingTimeline = false;

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    if (statsError || ordersError) {
        return <ErrorDisplay error={statsError || ordersError} />;
    }

    return (
        <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="w-full max-w-7xl mx-auto p-4 md:p-8 space-y-8 mt-16" 
        >
            <motion.h1 
                variants={{ hidden: { opacity: 0, y: -20 }, visible: { opacity: 1, y: 0 } }}
                className="text-3xl font-bold text-center text-cyan-400" 
                style={{ fontFamily: "'Orbitron', sans-serif" }}
            >
                Admin Dashboard
            </motion.h1>

            {/* --- Stats Grid (UPDATED to 6 columns) --- */}
            <motion.div 
                variants={containerVariants}
                // --- 1. METRICS: Changed to 6 columns ---
                className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-6"
            >
                {isLoadingStats ? (
                    <>
                        <StatCardSkeleton /><StatCardSkeleton /><StatCardSkeleton />
                        <StatCardSkeleton /><StatCardSkeleton /><StatCardSkeleton />
                    </>
                ) : statsData ? (
                    <>
                        <StatCard title="Total Revenue" value={statsData.total_revenue} icon={<DollarSign size={20} />} isCurrency />
                        <StatCard title="Total Orders" value={statsData.total_orders} icon={<Package size={20} />} />
                        <StatCard title="Total Products" value={statsData.total_products} icon={<HardDrive size={20} />} />
                        <StatCard title="Active Drones" value={statsData.active_drones} icon={<Wifi size={20} />} />
                        {/* --- 1. METRICS: New Cards Added --- */}
                        <StatCard title="Pending" value={statsData.pending_deliveries} icon={<Truck size={20} />} />
                        <StatCard title="Active Users" value={statsData.active_users_today} icon={<Users size={20} />} />
                    </>
                ) : null}
            </motion.div>

            {/* --- Two-Column Layout for Charts/Tables --- */}
            <motion.div 
                variants={containerVariants}
                className="grid grid-cols-1 lg:grid-cols-3 gap-6"
            >
                {/* Main Column (Graph + Orders) */}
                <div className="lg:col-span-2 space-y-6">
                    <motion.div
                        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                        className="rounded-2xl bg-white/5 p-6 backdrop-blur-lg border border-white/10"
                    >
                        <h2 className="flex items-center text-2xl font-bold text-white mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <BarChart2 className="mr-3 text-cyan-400" size={24} />
                            Revenue (Last 7 Days)
                        </h2>
                        <RevenueChart data={mockRevenueData} isLoading={isLoadingGraph} />
                    </motion.div>

                    <motion.div
                        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                        className="rounded-2xl bg-white/5 p-6 backdrop-blur-lg border border-white/10"
                    >
                        <h2 className="flex items-center text-2xl font-bold text-white mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <Package className="mr-3 text-cyan-400" size={24} />
                            Recent Orders
                        </h2>
                        {isLoadingOrders ? (
                            <TableSkeleton />
                        ) : ordersData ? (
                            <OrdersTable orders={ordersData.orders} />
                        ) : (
                            <p className="text-gray-500">No orders data available.</p>
                        )}
                    </motion.div>
                </div>

                {/* Side Column (Activity) */}
                <motion.div
                    variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                    className="lg:col-span-1 rounded-2xl bg-white/5 p-6 backdrop-blur-lg border border-white/10"
                >
                    <h2 className="flex items-center text-2xl font-bold text-white mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        <Clock className="mr-3 text-cyan-400" size={24} />
                        Activity Feed
                    </h2>
                    <ActivityTimeline events={mockActivityData} isLoading={isLoadingTimeline} />
                </motion.div>
            </motion.div>
        </motion.div>
    );
}

// --- (7) Main Page Export (No changes) ---
export default function AdminDashboardPage() {
    const { data: session, status } = useSession();

    if (status === 'loading') {
        return <LoadingSpinner />;
    }

    if (status === 'unauthenticated' || session?.user?.role !== 'admin') {
        return <AccessDenied />;
    }
    
    return (
        <div className="min-h-screen w-full bg-black text-gray-100 relative overflow-hidden" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            <div className="absolute inset-0 bg-grid-white/[0.05] -z-10" />
            <Suspense fallback={<LoadingSpinner />}>
                <DashboardContent />
            </Suspense>
        </div>
    );
}
